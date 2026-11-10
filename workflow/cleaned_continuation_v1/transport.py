"""One guarded HTTPS attempt at a time for an approved continuation."""

import base64
from copy import deepcopy
import http.client
import os
from pathlib import Path
import ssl
import subprocess
import sys
from threading import Lock
import time
from urllib.parse import urlsplit

# The parent invokes the wire worker by absolute path in isolated Python.
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cleaned_continuation_v1 import authority
from cleaned_opening_v1 import authorization as auth
from cleaned_opening_v1.transport import _check_dispatch as _check_frozen_dispatch
from live_runner_v1.transport import (
    BeforeDispatchLimit, DeliveryUncertain, ENDPOINTS, HTTPFixtureTransport,
    HTTPRejected, PreparedHTTPRequest, RESPONSE_CAP_BYTES, SAFE_RESPONSE_HEADERS,
    _HTTPTransport, build_http_request, timeout_budget,
)


def dispatch_directory(launch):
    """Keep one marker namespace across all controller leases for this run."""
    return launch.output_root / 'authorizations' / (launch.run_id + '.dispatches')


def _check_dispatch(launch, plan, session_dir, payload, attempt):
    opening_path = auth.ROOT / 'runs' / 'cleaned_opening_v1' / auth.RUN_ID / 'ledger.json'
    opening = auth.read_regular(opening_path)
    if auth.digest(opening) != launch.config['opening_ledger_sha256']:
        raise auth.AuthorizationError('The opening ledger no longer matches the continuation launch')
    ledger = auth.json_object(auth.read_regular(launch.run_directory / 'ledger.json'))
    if any(ledger.get(sid) != entry for sid, entry in auth.json_object(opening).items()):
        raise auth.AuthorizationError('The cumulative ledger changed the completed opening')
    return _check_frozen_dispatch(launch, plan, session_dir, payload, attempt)


class AuthorizedHTTPTransport(_HTTPTransport):
    """A session-specific transport backed by a live controller lease."""

    mode = 'live_http'

    def __init__(self, grant, plan, session_dir, credential_supplier):
        if type(grant) is not authority.RunGrant or not callable(credential_supplier):
            raise auth.AuthorizationError('An active continuation grant and credential supplier are required')
        plan = deepcopy(plan)
        session_dir = auth.canonical_path(session_dir)
        grant.assign(plan, session_dir)
        super().__init__(plan['provider'])
        self._grant = grant
        self._plan = plan
        self._session_dir = session_dir
        self._credential_supplier = credential_supplier
        self._attempt_count = 0
        self._mutex = Lock()

    def preflight(self, plan=None, output_dir=None):
        if plan is not None and auth.encode(plan) != auth.encode(self._plan):
            raise auth.AuthorizationError('The transport was assigned to a different plan')
        if output_dir is not None and auth.canonical_path(output_dir) != self._session_dir:
            raise auth.AuthorizationError('The transport was assigned to a different output path')
        self._grant.check(self._plan, self._session_dir)

    def send(self, payload, *, session_remaining_seconds):
        with self._mutex:
            self.last_http_evidence = None
            timeout_budget(session_remaining_seconds)
            started = time.monotonic()
            self.preflight()
            attempt = self._attempt_count + 1
            _check_dispatch(self._grant.launch, self._plan, self._session_dir, payload, attempt)
            remaining = session_remaining_seconds - (time.monotonic() - started)
            timeout_budget(remaining)
            self._attempt_count = attempt
            credential = self._credential_supplier(self.provider)
            remaining = session_remaining_seconds - (time.monotonic() - started)
            return self._attempt(
                payload, remaining, credential,
                lambda request: _wire_child(request, self._grant, self._plan['session_id'], attempt),
            )


def _wire_child(request, grant, session_id, attempt):
    # The credential travels only in memory and through this subprocess's stdin.
    data = auth.encode({
        'config_path': str(grant.launch.config_path),
        'config_sha256': grant.launch.sha256,
        'claim_path': str(grant.claim_path),
        'claim_sha256': grant.claim_sha256,
        'session_id': session_id,
        'attempt': attempt,
        'request': {
            'provider': request.provider,
            'endpoint': request.endpoint,
            'headers': request.headers,
            'body': base64.b64encode(request.body).decode('ascii'),
            'timeout_seconds': request.timeout_seconds,
            'connect_timeout_seconds': request.connect_timeout_seconds,
        },
    })
    completed = subprocess.run(
        [sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--wire-child'],
        input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'TZ': 'UTC'},
        timeout=request.timeout_seconds, check=True,
    )
    answer = auth.json_object(completed.stdout)
    return answer['status'], answer['headers'], base64.b64decode(answer['body'], validate=True)


def _run_authorized_child(data):
    """Recheck the production pin, actual controller and exact request before POST."""
    from cleaned_continuation_v1.launch_pin import LAUNCH_SHA256

    config_path = auth.canonical_path(data['config_path'])
    if config_path != authority.CONFIG_PATH or data['config_sha256'] != LAUNCH_SHA256:
        raise auth.AuthorizationError('The wire worker requires the pinned continuation launch')
    host = auth.json_object(auth.read_regular(config_path))['host']
    launch = authority.validate_launch(
        config_path, LAUNCH_SHA256, host=host, output_root=authority.RUN_ROOT,
    )
    controller_pid = os.getppid()
    authority.verify_claim(
        launch, auth.canonical_path(data['claim_path']), data['claim_sha256'],
        controller_pid=controller_pid,
    )
    plan = launch.session_plan(data['session_id'])
    session_dir = launch.session_directory(plan['session_id'])
    request = dict(data['request'])
    request['body'] = base64.b64decode(request['body'], validate=True)
    request = PreparedHTTPRequest(**request)
    payload = auth.json_object(request.body)
    intent = _check_dispatch(launch, plan, session_dir, payload, data['attempt'])
    if request.provider != plan['provider'] or request.endpoint != ENDPOINTS[plan['provider']]:
        raise auth.AuthorizationError('The request endpoint is outside the approved provider')
    if request.provider == 'openai':
        value = request.headers.get('Authorization', '')
        if not value.startswith('Bearer '):
            raise auth.AuthorizationError('Expected the approved provider authentication header')
        credential = value.removeprefix('Bearer ')
    else:
        credential = request.headers.get('x-api-key')
    expected = build_http_request(request.provider, payload, credential, request.timeout_seconds)
    if request != expected:
        raise auth.AuthorizationError('The prepared wire request changed')
    if os.getppid() != controller_pid:
        raise auth.AuthorizationError('The wire worker lost its approved controller')

    # The exclusive attempt marker must be durable before a connection begins.
    marker = dispatch_directory(launch) / f"{plan['session_id']}.{data['attempt']:04d}.json"
    auth._write_exclusive(marker, {
        'claim_sha256': data['claim_sha256'],
        'session_id': plan['session_id'],
        'attempt': data['attempt'],
        'dispatch_intent_sha256': intent['sha256'],
    })
    if os.getppid() != controller_pid:
        raise auth.AuthorizationError('The wire worker lost its approved controller')
    return _https_once(request)


def _https_once(request):
    """Use the opening's direct TLS, deadlines and bounded response capture."""
    endpoint = urlsplit(request.endpoint)
    deadline = time.monotonic() + request.timeout_seconds
    connection = http.client.HTTPSConnection(
        endpoint.hostname, 443, timeout=request.connect_timeout_seconds,
        context=ssl.create_default_context(),
    )

    def set_remaining():
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            raise TimeoutError('request deadline')
        if connection.sock is not None:
            connection.sock.settimeout(seconds)

    try:
        connection.connect()
        set_remaining()
        connection.request('POST', endpoint.path, body=request.body, headers=request.headers)
        set_remaining()
        response = connection.getresponse()
        body = bytearray()
        while len(body) <= RESPONSE_CAP_BYTES:
            set_remaining()
            block = response.read1(min(65536, RESPONSE_CAP_BYTES + 1 - len(body)))
            if not block:
                break
            body.extend(block)
        headers = {
            key: value for key, value in response.getheaders()
            if key.lower() in SAFE_RESPONSE_HEADERS
        }
        return {'status': response.status, 'headers': headers,
                'body': base64.b64encode(body).decode('ascii')}
    finally:
        connection.close()


if __name__ == '__main__' and sys.argv[1:] == ['--wire-child']:
    wire_input = sys.stdin.buffer.read(auth.RECORD_LIMIT + 1)
    if len(wire_input) > auth.RECORD_LIMIT:
        raise auth.AuthorizationError('Wire input exceeded its bound')
    response = _run_authorized_child(auth.json_object(wire_input))
    sys.stdout.buffer.write(auth.encode(response))
