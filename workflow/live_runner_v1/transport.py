"""Bind recorded HTTP responses to the session engine through a sealed transport."""
from dataclasses import dataclass, field
import base64
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
import hashlib
import http.client
import json
import math
import socket
import ssl
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlsplit

LIVE_LOCK = True
ENDPOINTS = {'openai': 'https://api.openai.com/v1/responses',
             'anthropic': 'https://api.anthropic.com/v1/messages'}
ANTHROPIC_VERSION = '2026-10-21'
REQUEST_CAP_SECONDS = 180
CONNECT_CAP_SECONDS = 30
RESPONSE_CAP_BYTES = 2 * 1024 * 1024
SAFE_RESPONSE_HEADERS = {'request-id', 'x-request-id', 'retry-after', 'content-type', 'date'}


class LiveDisabled(RuntimeError):
    pass


class BeforeDispatchLimit(ValueError):
    pass


class HTTPRejected(RuntimeError):
    def __init__(self, receipt):
        self.receipt = receipt
        self.status_code = receipt.status_code
        self.retry_after = retry_after_seconds(receipt.headers.get('retry-after'))
        super().__init__(f'Explicit HTTP {receipt.status_code} rejection; no automatic retry')


class DeliveryUncertain(RuntimeError):
    def __init__(self, reason, receipt=None):
        self.reason, self.receipt = reason, receipt
        super().__init__('Delivery requires reconciliation: ' + reason)


@dataclass(frozen=True)
class PreparedHTTPRequest:
    provider: str
    endpoint: str
    body: bytes = field(repr=False)
    headers: dict = field(repr=False)
    timeout_seconds: float
    connect_timeout_seconds: float

    def safe_record(self):
        return {'provider': self.provider, 'endpoint': self.endpoint, 'method': 'POST',
                'body_bytes': len(self.body), 'body_sha256': hashlib.sha256(self.body).hexdigest(),
                'timeout_seconds': self.timeout_seconds, 'connect_timeout_seconds': self.connect_timeout_seconds,
                'headers': {k:v for k,v in self.headers.items() if k.lower() not in ('authorization','x-api-key')}}


@dataclass(frozen=True)
class HTTPReceipt:
    status_code: int
    headers: dict
    body: bytes = field(repr=False)
    request_id: str | None

    def evidence_record(self):
        return {'status_code': self.status_code, 'headers': self.headers, 'request_id': self.request_id,
                'body_base64': base64.b64encode(self.body).decode('ascii'),
                'body_sha256': hashlib.sha256(self.body).hexdigest(), 'body_bytes': len(self.body)}


def timeout_budget(remaining_seconds):
    if type(remaining_seconds) not in (int, float) or not math.isfinite(remaining_seconds) or remaining_seconds <= 0:
        raise BeforeDispatchLimit('No positive finite session time remains')
    return min(float(remaining_seconds), REQUEST_CAP_SECONDS)


def build_http_request(provider, payload, credential, remaining_seconds, *, endpoint=None):
    """Pure preparation. The credential is explicitly supplied, never discovered."""
    expected = ENDPOINTS.get(provider)
    if expected is None or endpoint not in (None, expected):
        raise ValueError('Endpoint/provider is not allowlisted')
    if (not isinstance(credential, str) or not credential
            or any(not 33 <= ord(character) <= 126 for character in credential)):
        raise ValueError('A nonempty printable ASCII credential without whitespace is required')
    if not isinstance(payload, dict):
        raise ValueError('Provider payload must be an object')
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(body) > 131072:
        raise BeforeDispatchLimit('Request exceeds prepared byte limit; no truncation')
    timeout = timeout_budget(remaining_seconds)
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if provider == 'openai':
        headers['Authorization'] = 'Bearer ' + credential
    else:
        headers['x-api-key'] = credential
        headers['anthropic-version'] = ANTHROPIC_VERSION
    return PreparedHTTPRequest(provider, expected, body, headers, timeout, min(timeout, CONNECT_CAP_SECONDS))


def parse_http_result(status_code, headers, body):
    """Classify HTTP only. Model output interpretation belongs to the adapter."""
    if type(status_code) is not int or not 100 <= status_code <= 599 or not isinstance(headers, dict) or not isinstance(body, bytes):
        raise DeliveryUncertain('malformed_http_evidence')
    normalized = {str(k).lower():str(v) for k,v in headers.items()}
    allowed = {k:v for k,v in normalized.items() if k in SAFE_RESPONSE_HEADERS}
    request_id = allowed.get('x-request-id') or allowed.get('request-id')
    receipt = HTTPReceipt(status_code, allowed, body, request_id)
    if len(body) > RESPONSE_CAP_BYTES:
        raise DeliveryUncertain('response_size_limit', receipt)
    if 200 <= status_code < 300:
        return receipt
    if 400 <= status_code < 500:
        raise HTTPRejected(receipt)
    # Never follow redirects; a 5xx/other response does not prove no model work.
    raise DeliveryUncertain('HTTP_' + str(status_code), receipt)


def classify_wire_exception(exc):
    """Transport failures have unknown delivery, even when a retry looks tempting."""
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return DeliveryUncertain('timeout')
    return DeliveryUncertain(type(exc).__name__)


def _stdlib_https_one_attempt(request):
    """Locked HTTPS implementation; no redirects, proxies or automatic retries.

    Socket operations use the remaining deadline. DNS/OS scheduling still need
    validation on the eventual live host; this is not a measured latency bound.
    """
    if LIVE_LOCK:
        raise LiveDisabled('HTTPS is code-locked; no network operation was attempted')
    if request.endpoint != ENDPOINTS.get(request.provider):
        raise ValueError('Endpoint changed after preparation')
    endpoint = urlsplit(request.endpoint)
    started = time.monotonic()
    deadline = started + request.timeout_seconds
    connection = http.client.HTTPSConnection(endpoint.hostname, 443, timeout=request.connect_timeout_seconds,
                                             context=ssl.create_default_context())

    def set_remaining():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('request deadline')
        if connection.sock is not None:
            connection.sock.settimeout(remaining)

    try:
        connection.connect()
        set_remaining()
        connection.request('POST', endpoint.path, body=request.body, headers=request.headers)
        set_remaining()
        response = connection.getresponse()
        body = bytearray()
        while True:
            set_remaining()
            block = response.read1(min(65536, RESPONSE_CAP_BYTES + 1 - len(body)))
            if not block:
                break
            body.extend(block)
            if len(body) > RESPONSE_CAP_BYTES:
                break
        return response.status, dict(response.getheaders()), bytes(body)
    finally:
        connection.close()


def retry_after_seconds(value):
    """Preserve a provider's retry delay when it is a number or HTTP date."""
    if value is None:
        return 0.0
    try:
        seconds = float(value)
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            seconds = (date - datetime.now(timezone.utc)).total_seconds()
        except (ValueError, OverflowError, TypeError, AttributeError):
            return math.inf
    return max(0.0, seconds) if math.isfinite(seconds) else math.inf


def _wire_child(request):
    """Put the actual HTTPS attempt under a parent process timeout, including DNS."""
    if LIVE_LOCK:
        raise LiveDisabled('HTTPS is code-locked before starting a connection')
    data = json.dumps({'provider': request.provider, 'endpoint': request.endpoint,
                       'headers': request.headers, 'body': base64.b64encode(request.body).decode('ascii'),
                       'timeout_seconds': request.timeout_seconds,
                       'connect_timeout_seconds': request.connect_timeout_seconds}).encode()
    completed = subprocess.run(
        [sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--wire-child'],
        input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'TZ': 'UTC'},
        timeout=request.timeout_seconds, check=True,
    )
    answer = json.loads(completed.stdout)
    return answer['status'], answer['headers'], base64.b64decode(answer['body'], validate=True)


def _run_child():
    if LIVE_LOCK:
        raise LiveDisabled('HTTPS is code-locked in the connection worker')
    data = json.load(sys.stdin.buffer)
    data['body'] = base64.b64decode(data['body'], validate=True)
    status, headers, body = _stdlib_https_one_attempt(PreparedHTTPRequest(**data))
    json.dump({'status': status, 'headers': headers,
               'body': base64.b64encode(body).decode('ascii')}, sys.stdout)


def _redact_receipt(body, headers, credential):
    """Strip credential echoes, including strings decoded from JSON escapes."""
    if not isinstance(body, bytes) or not isinstance(headers, dict):
        return body, headers, False
    token = credential.encode()
    replacement = '[REDACTED_CREDENTIAL]'
    allowed = {str(k).lower(): str(v) for k, v in headers.items()
               if str(k).lower() in SAFE_RESPONSE_HEADERS}
    clean_headers = {k: v.replace(credential, replacement) for k, v in allowed.items()}
    clean_body = body.replace(token, replacement.encode())

    def contains_credential(value):
        if isinstance(value, str):
            return credential in value
        if isinstance(value, (list, tuple)):
            return any(contains_credential(item) for item in value)
        return False

    try:
        # Keeping object pairs avoids missing an echo hidden by a duplicate key.
        decoded = json.loads(clean_body, object_pairs_hook=list)
        if contains_credential(decoded):
            clean_body = b'[REDACTED_JSON_CREDENTIAL_ECHO]'
    except (UnicodeDecodeError, ValueError):
        pass
    except RecursionError:
        clean_body = b'[REDACTED_UNCHECKABLE_JSON]'
    return clean_body, clean_headers, clean_body != body or clean_headers != allowed


class _HTTPTransport:
    def __init__(self, provider):
        if provider not in ENDPOINTS:
            raise ValueError('Unknown provider')
        self.provider = provider
        self.last_http_evidence = None

    def _attempt(self, payload, remaining_seconds, credential, wire):
        request = build_http_request(self.provider, payload, credential, remaining_seconds)
        self.last_http_evidence = {'request': request.safe_record(), 'receipt': None}
        try:
            status, headers, body = wire(request)
        except subprocess.TimeoutExpired:
            raise DeliveryUncertain('timeout') from None
        except Exception as exc:
            raise classify_wire_exception(exc) from None

        clean_body, clean_headers, redacted = _redact_receipt(body, headers, credential)
        self.last_http_evidence['redacted_credential_echo'] = redacted
        try:
            receipt = parse_http_result(status, clean_headers, clean_body)
        except (HTTPRejected, DeliveryUncertain) as exc:
            if exc.receipt is not None:
                self.last_http_evidence['receipt'] = exc.receipt.evidence_record()
            if redacted:
                raise DeliveryUncertain('credential_echo_redacted') from None
            raise
        self.last_http_evidence['receipt'] = receipt.evidence_record()
        if redacted:
            raise DeliveryUncertain('credential_echo_redacted') from None
        try:
            raw = json.loads(receipt.body, parse_constant=_reject_json_constant,
                             object_pairs_hook=_unique_json_object)
            json.dumps(raw, ensure_ascii=False, allow_nan=False).encode('utf-8')
        except (UnicodeError, ValueError, RecursionError):
            raise DeliveryUncertain('invalid_json_response', receipt) from None
        if not isinstance(raw, dict):
            raise DeliveryUncertain('nonobject_json_response', receipt)
        return raw


def _unique_json_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError('Duplicate JSON property')
    return result


def _reject_json_constant(value):
    raise ValueError('Nonfinite JSON number')


class HTTPFixtureTransport(_HTTPTransport):
    """Run the HTTP binding with an injected wire and a fixed dummy credential."""
    mode = 'http_fixture'
    credential = 'offline-fixture-secret'

    def __init__(self, provider, wire):
        super().__init__(provider)
        if not callable(wire):
            raise ValueError('An explicit offline fixture wire is required')
        self._wire = wire

    def preflight(self):
        return None

    def send(self, payload, *, session_remaining_seconds):
        self.last_http_evidence = None
        return self._attempt(payload, session_remaining_seconds, self.credential, self._wire)


class LockedHTTPTransport(_HTTPTransport):
    """Real request path, sealed before any credential access or connection."""
    mode = 'live_http'

    def __init__(self, provider, credential_supplier):
        super().__init__(provider)
        if not callable(credential_supplier):
            raise ValueError('An explicit credential supplier is required')
        self._credential_supplier = credential_supplier

    def preflight(self):
        if LIVE_LOCK:
            raise LiveDisabled('Transport is code-locked before credential access or dispatch')

    def send(self, payload, *, session_remaining_seconds):
        self.preflight()
        self.last_http_evidence = None
        timeout_budget(session_remaining_seconds)
        started = time.monotonic()
        credential = self._credential_supplier()
        remaining = session_remaining_seconds - (time.monotonic() - started)
        return self._attempt(payload, remaining, credential, _wire_child)


if __name__ == '__main__' and sys.argv[1:] == ['--wire-child']:
    _run_child()
