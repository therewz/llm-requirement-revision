"""Prepared one-attempt HTTPS connection, permanently locked for offline work.

Pure request/response helpers are testable with placeholders. Neither lock can
be enabled by a CLI flag, environment variable or an approval-shaped argument.
The session engine independently rejects this transport class.
"""
from dataclasses import dataclass, field
import hashlib
import http.client
import json
import math
import socket
import ssl
import time
from urllib.parse import urlsplit

LIVE_LOCK = True
ENDPOINTS = {'openai': 'https://api.openai.com/v1/responses',
             'anthropic': 'https://api.anthropic.com/v1/messages'}
ANTHROPIC_VERSION = '2026-10-21'
REQUEST_CAP_SECONDS = 180
CONNECT_CAP_SECONDS = 30
RESPONSE_CAP_BYTES = 2 * 1024 * 1024


class LiveDisabled(RuntimeError):
    pass


class BeforeDispatchLimit(ValueError):
    pass


class HTTPRejected(RuntimeError):
    def __init__(self, receipt):
        self.receipt = receipt
        self.status_code = receipt.status_code
        self.retry_after = receipt.headers.get('retry-after')
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
                'body_utf8': self.body.decode('utf-8', errors='replace'),
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
    if not isinstance(credential, str) or not credential or any(ch.isspace() for ch in credential):
        raise ValueError('A nonempty credential without whitespace is required')
    if not isinstance(payload, dict):
        raise ValueError('Provider payload must be an object')
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
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
    allowed = {k:v for k,v in normalized.items() if k in ('request-id','x-request-id','retry-after','content-type','date')}
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


class LockedHTTPTransport:
    """Prepared connection path; intentionally cannot be used by the engine."""
    def __init__(self, provider, credential_supplier, *, wire=None):
        if provider not in ENDPOINTS or not callable(credential_supplier):
            raise ValueError('Known provider and explicit credential supplier required')
        self.provider, self._credential_supplier = provider, credential_supplier
        self._wire = wire if wire is not None else _stdlib_https_one_attempt
        self.last_http_evidence = None

    def send(self, payload, *, session_remaining_seconds=180, live=False, approved=False):
        if LIVE_LOCK:
            raise LiveDisabled('Transport is code-locked before credential access or dispatch')
        # Reaching this path requires a reviewed source change, not flags.
        timeout_budget(session_remaining_seconds)
        credential = self._credential_supplier()
        request = build_http_request(self.provider, payload, credential, session_remaining_seconds)
        try:
            status, headers, body = self._wire(request)
        except Exception as exc:
            raise classify_wire_exception(exc) from None
        # Do not allow a provider error echo to persist an explicit credential.
        clean_body = body.replace(credential.encode(), b'[REDACTED_CREDENTIAL]') if isinstance(body, bytes) else body
        try:
            receipt = parse_http_result(status, headers, clean_body)
        except (HTTPRejected, DeliveryUncertain) as exc:
            if exc.receipt is not None:
                self.last_http_evidence = exc.receipt.evidence_record()
            raise
        self.last_http_evidence = receipt.evidence_record()
        try:
            raw = json.loads(receipt.body)
        except (UnicodeDecodeError, ValueError):
            raise DeliveryUncertain('invalid_json_response', receipt) from None
        if not isinstance(raw, dict):
            raise DeliveryUncertain('nonobject_json_response', receipt)
        return raw
