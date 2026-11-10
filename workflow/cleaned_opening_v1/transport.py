"""HTTPS transport scoped to an explicitly approved cleaned opening."""

import base64
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import http.client
import os
from pathlib import Path
import ssl
import subprocess
import sys
import time
from threading import Lock
from urllib.parse import urlsplit

# The isolated HTTPS subprocess executes this trusted file by absolute path.
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bounded_sessions_v1.adapters import ClaudeAdapter, OpenAIAdapter
from live_runner_v1 import engine as evidence
from live_runner_v1.transport import (
    BeforeDispatchLimit, DeliveryUncertain, ENDPOINTS, HTTPFixtureTransport,
    HTTPRejected, LiveDisabled, PreparedHTTPRequest, RESPONSE_CAP_BYTES,
    SAFE_RESPONSE_HEADERS, _HTTPTransport, build_http_request, timeout_budget,
)
from cleaned_opening_v1 import authorization as auth


def _check_budget(launch, plan):
    ledger = auth.json_object(auth.read_regular(launch.run_directory / 'ledger.json'))
    sid, provider = plan['session_id'], plan['provider']
    expected = {'status': 'reserved', 'provider': provider,
                'charged_or_reserved_usd': plan['limits']['session_cost_cap_usd']}
    if ledger.get(sid) != expected:
        raise auth.AuthorizationError('The authorized session has no exact durable cost reservation')
    ordered = launch.config['sessions']
    scopes = {p['session_id']: p for p in ordered[:len(ledger)]}
    if ledger.keys() != scopes.keys():
        raise auth.AuthorizationError('The cost ledger is not a prefix of the authorized opening')
    totals = {name: Decimal(0) for name in auth.PROVIDERS}
    active = Counter()
    for session_id, record in ledger.items():
        scoped = scopes[session_id]
        if (not isinstance(record, dict) or record.get('provider') != scoped['provider']
                or record.get('status') not in ('reserved', 'terminal')):
            raise auth.AuthorizationError('Malformed opening cost ledger')
        charge = auth.amount(record.get('charged_or_reserved_usd'))
        ceiling = auth.amount(scoped['limits']['session_cost_cap_usd'])
        if charge > ceiling or (record['status'] == 'reserved' and charge != ceiling):
            raise auth.AuthorizationError('A session reservation exceeds its authorized scope')
        if record.get('cost_uncertain'):
            raise auth.AuthorizationError('An unknown delivery or cost needs reconciliation')
        totals[scoped['provider']] += charge
        if record['status'] == 'reserved':
            active[scoped['provider']] += 1
    scheduler = launch.config['scheduler']
    if (sum(active.values()) > scheduler['concurrency']
            or any(count > scheduler['per_provider_concurrency'] for count in active.values())):
        raise auth.AuthorizationError('The opening has more active reservations than authorized')
    if (sum(totals.values()) > auth.amount(scheduler['run_cost_cap_usd'])
            or any(value > auth.amount(scheduler['provider_cost_caps_usd'][name])
                   for name, value in totals.items())):
        raise auth.AuthorizationError('The opening cost reservation exceeds its authorized scope')


def _check_payload(plan, payload, turn):
    packet = auth.canonical_path(plan['packet_dir'])
    prompt = auth.read_regular(packet / 'prompt_draft.md')
    source = auth.read_regular(packet / 'workspace/src/solution.py', limit=plan['limits']['file_bytes'])
    if auth.digest(prompt) != plan['prompt_sha256'] or auth.digest(source) != plan['source_sha256']:
        raise auth.AuthorizationError('The cleaned source or matched prompt no longer matches the plan')
    adapter, history_key = ((OpenAIAdapter(), 'input') if plan['provider'] == 'openai'
                            else (ClaudeAdapter(), 'messages'))
    template = adapter.encode(
        plan['model'],
        [{'role': 'system', 'content': plan['operational_instruction']},
         {'role': 'user', 'content': prompt.decode('utf-8')}],
        plan['tools'], plan['limits']['max_output_tokens'], plan['settings'],
    )
    expected_history = template.pop(history_key)
    if not isinstance(payload, dict):
        raise auth.AuthorizationError('The provider payload is not an object')
    history = payload.get(history_key)
    if (auth.encode({k: v for k, v in payload.items() if k != history_key}) != auth.encode(template)
            or not isinstance(history, list)
            or auth.encode(history[:len(expected_history)]) != auth.encode(expected_history)
            or (turn == 1 and len(history) != len(expected_history))):
        raise auth.AuthorizationError('The request differs from the authorized model, settings, tools or prompt')


def _check_dispatch(launch, plan, session_dir, payload, attempt):
    session_dir = auth.canonical_path(session_dir)
    if session_dir != launch.session_directory(plan['session_id']):
        raise auth.AuthorizationError('The request targets the wrong session directory')
    _check_budget(launch, plan)
    limits = {**evidence.DEFAULT_LIMITS, **plan['limits']}
    saved_plan = {'plan': plan, 'effective_limits': limits, 'mode': 'live_http'}
    if auth.read_regular(session_dir / 'plan.json') != auth.encode(saved_plan):
        raise auth.AuthorizationError('The session did not bind the approved plan and limits')
    # The engine owns this journal. Reuse its verified hash chain and file refs.
    auth.read_regular(session_dir / 'events.jsonl')
    events = evidence.Journal(session_dir).events
    intents = [event for event in events if event['event'] == 'dispatch_intent']
    if (not events or events[-1]['event'] != 'dispatch_intent'
            or type(attempt) is not int or attempt < 1
            or [e['attempt'] for e in intents] != list(range(1, attempt + 1))):
        raise auth.AuthorizationError('The request lacks a new durable dispatch intent')
    intent = intents[-1]
    turn = intent['turn']
    if (type(turn) is not int or not 1 <= turn <= limits['max_model_turns']
            or turn != 1 + sum(event['event'] == 'response_saved' for event in events)):
        raise auth.AuthorizationError('The request exceeds or differs from the authorized model turns')
    same_turn = [e for e in intents if e['turn'] == turn]
    prior_attempts = {e['attempt'] for e in same_turn[:-1]}
    rejected_429 = {e['attempt'] for e in events if e['event'] == 'request_rejected' and e['status_code'] == 429}
    if len(prior_attempts) > limits['max_429_retries'] or not prior_attempts <= rejected_429:
        raise auth.AuthorizationError('Only an explicit 429 permits a bounded retry')

    request_data = auth.encode(payload)
    relative = f'attempts/{attempt:04d}_request.json'
    refs = [{'path': relative, 'sha256': auth.digest(request_data), 'bytes': len(request_data)}]
    if (intent['files'] != refs
            or auth.read_regular(session_dir / relative, limit=limits['max_request_bytes']) != request_data):
        raise auth.AuthorizationError('The request bytes do not match the recorded dispatch intent')
    reservation = evidence._reservation(len(request_data), limits, plan['pricing'])
    charged = sum((auth.amount(e['cost_usd']) for e in events if e['event'] == 'usage'), Decimal(0))
    if (auth.amount(intent['reservation_usd']) != reservation
            or charged + reservation > auth.amount(limits['session_cost_cap_usd'])):
        raise auth.AuthorizationError('The request does not fit the session cost reservation')
    _check_payload(plan, payload, turn)
    return intent


class AuthorizedHTTPTransport(_HTTPTransport):
    """A single assigned session, with approval and accounting checks before secrets."""

    mode = 'live_http'

    def __init__(self, grant, plan, session_dir, credential_supplier):
        if type(grant) is not auth.RunGrant or not callable(credential_supplier):
            raise auth.AuthorizationError('An active opening grant and credential supplier are required')
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
            launch = self._grant.launch
            _check_dispatch(launch, self._plan, self._session_dir, payload, attempt)
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
    # The provider credential travels only through the subprocess stdin pipe.
    data = auth.encode({
        'config_path': str(grant.launch.config_path),
        'config_sha256': grant.launch.sha256,
        'claim_sha256': grant.claim_sha256,
        'session_id': session_id, 'attempt': attempt,
        'request': {'provider': request.provider, 'endpoint': request.endpoint,
                    'headers': request.headers, 'body': base64.b64encode(request.body).decode('ascii'),
                    'timeout_seconds': request.timeout_seconds,
                    'connect_timeout_seconds': request.connect_timeout_seconds},
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
    """Verify the one-use claim again in the process that performs the HTTPS POST."""
    config_path = auth.canonical_path(data['config_path'])
    host = auth.json_object(auth.read_regular(config_path))['host']
    launch = auth.validate_launch(config_path, data['config_sha256'], host=host, output_root=config_path.parent)
    auth.verify_claim(launch, data['claim_sha256'], controller_pid=os.getppid())
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

    # Even this lower-level worker cannot re-send a consumed dispatch attempt.
    claimed = launch.claim_path.parent / (launch.run_id + '.dispatches')
    marker = claimed / f"{plan['session_id']}.{data['attempt']:04d}.json"
    auth._write_exclusive(marker, {'claim_sha256': data['claim_sha256'], 'session_id': plan['session_id'],
                                   'attempt': data['attempt'], 'dispatch_intent_sha256': intent['sha256']})
    endpoint = urlsplit(request.endpoint)
    deadline = time.monotonic() + request.timeout_seconds
    connection = http.client.HTTPSConnection(endpoint.hostname, 443, timeout=request.connect_timeout_seconds,
                                             context=ssl.create_default_context())

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
        headers = {key: value for key, value in response.getheaders() if key.lower() in SAFE_RESPONSE_HEADERS}
        return {'status': response.status, 'headers': headers, 'body': base64.b64encode(body).decode('ascii')}
    finally:
        connection.close()


if __name__ == '__main__' and sys.argv[1:] == ['--wire-child']:
    response = _run_authorized_child(auth.json_object(sys.stdin.buffer.read(auth.RECORD_LIMIT + 1)))
    sys.stdout.buffer.write(auth.encode(response))
