"""Replay the eight bound turns and permit only guarded extension requests."""

import base64
from copy import deepcopy
from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys
from threading import Lock
import time

# The wire child is invoked by absolute path with Python isolation enabled.
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bounded_sessions_v1.adapters import OpenAIAdapter
from cleaned_continuation_v1.transport import _https_once
from cleaned_opening_v1 import authorization as auth
from cleaned_opening_v1 import engine as evidence
from cleaned_opening_v1.transport import _check_dispatch
from live_runner_v1.transport import (
    BeforeDispatchLimit, DeliveryUncertain, ENDPOINTS, HTTPFixtureTransport,
    HTTPRejected, PreparedHTTPRequest, _HTTPTransport, build_http_request, timeout_budget,
)

REPLAY_TURNS = 8
REPLAY_EVENT_NAMES = ('dispatch_intent', 'http_attempt', 'response_saved', 'response_parsed',
                      'usage', 'tool_intent', 'tool_result')


def dispatch_directory(launch):
    return launch.output_root / 'authorizations' / (launch.run_id + '.dispatches')


def _require(condition, message):
    if not condition:
        raise auth.AuthorizationError(message)


def _artifact_bytes(session_dir, event):
    refs = event['files']
    _require(len(refs) == 1, 'Expected one bound event artifact')
    path = session_dir / refs[0]['path']
    _require(path.is_relative_to(session_dir) and '..' not in path.parts, 'Invalid event artifact path')
    return auth.read_regular(path)


def _check_usage(event, attempt, normalized, plan, spent):
    expected = evidence.usage_cost(normalized['usage'], plan['pricing'])
    _require(event['attempt'] == attempt and event['usage'] == normalized['usage']
             and auth.amount(event['cost_usd']) == expected
             and auth.amount(event['cumulative_cost_usd']) == spent + expected,
             'Recorded request usage differs from its verified response')
    return spent + expected


def _check_replayed_prefix(session_dir, events, history, plan):
    _require(events[0]['event'] == 'initialized'
             and events[0]['workspace_files'] == history.initial_workspace,
             'The extension initialized a different workspace')
    adapter = OpenAIAdapter()
    spent = Decimal(0)
    width = len(REPLAY_EVENT_NAMES)
    for index in range(REPLAY_TURNS):
        attempt = index + 1
        start = 1 + index * width
        row = events[start:start + width]
        _require(tuple(event['event'] for event in row) == REPLAY_EVENT_NAMES,
                 'The extension journal does not contain all eight local replay turns')
        intent, http, response, parsed, usage, tool_call, tool_result = row
        _require(intent['attempt'] == intent['turn'] == http['attempt'] == response['attempt']
                 == parsed['attempt'] == attempt and http['outcome'] == 'received',
                 'The local replay attempt or receipt order changed')
        raw = history.responses[index]
        normalized = adapter.parse(raw)
        for event, expected in ((intent, history.requests[index]), (http, history.http_evidence[index]),
                                (response, raw), (parsed, normalized)):
            _require(_artifact_bytes(session_dir, event) == auth.encode(expected),
                     'A replayed request, response or receipt changed')
        tool = history.tools[index]
        _require(tool_call['turn'] == attempt and tool_call['tool_index'] == tool_result['tool_index'] == attempt
                 and auth.encode(tool_call['tool_call']) == auth.encode(tool.call)
                 and tool_result['workspace_files'] == tool.workspace_files
                 and _artifact_bytes(session_dir, tool_result) == auth.encode(tool.result),
                 'A replayed tool call, result or workspace changed')
        spent = _check_usage(usage, attempt, normalized, plan, spent)
    _require(spent == history.usage_usd, 'Replayed usage does not equal the original eight-turn cost')
    return 1 + REPLAY_TURNS * width


def _check_extension_context(session_dir, history, plan, payload, attempt):
    _require(type(attempt) is int and attempt > REPLAY_TURNS, 'An archived turn cannot dispatch live')
    events = evidence.Journal(session_dir).events
    start = _check_replayed_prefix(session_dir, events, history, plan)
    expected = deepcopy(history.next_request)
    spent = history.usage_usd
    adapter = OpenAIAdapter()
    pending = []
    active_tool = None
    response = normalized = None
    workspace_files = history.final_workspace
    for event in events[start:]:
        kind = event['event']
        if kind == 'dispatch_intent':
            _require(not pending and active_tool is None and response is None and normalized is None
                     and _artifact_bytes(session_dir, event) == auth.encode(expected),
                     'The extension request does not carry the verified conversation')
        elif kind == 'response_saved':
            _require(response is None and normalized is None, 'Unexpected unconsumed extension response')
            response = event['attempt'], auth.json_object(_artifact_bytes(session_dir, event))
        elif kind == 'response_parsed':
            _require(response is not None and response[0] == event['attempt'] and normalized is None,
                     'The extension parsed response has no matching raw reply')
            parsed = adapter.parse(response[1])
            _require(parsed['status'] == 'tool_calls' and parsed['model'] == plan['model']
                     and _artifact_bytes(session_dir, event) == auth.encode(parsed),
                     'An earlier extension reply does not authorize another turn')
            normalized = event['attempt'], parsed
            response = None
            expected['input'].extend(parsed['continuation'])
            pending = list(parsed['tool_calls'])
        elif kind == 'usage':
            _require(normalized is not None, 'Extension usage lacks a matching response')
            spent = _check_usage(event, normalized[0], normalized[1], plan, spent)
            normalized = None
        elif kind == 'tool_intent':
            _require(active_tool is None and normalized is None and pending
                     and auth.encode(event['tool_call']) == auth.encode(pending[0]),
                     'The extension tool call does not match its verified reply')
            active_tool = pending.pop(0)
        elif kind == 'tool_result':
            _require(active_tool is not None, 'An extension tool result has no verified call')
            result = _artifact_bytes(session_dir, event)
            expected['input'].append({'type': 'function_call_output', 'call_id': active_tool['id'],
                                      'output': result.decode('utf-8')})
            workspace_files = event['workspace_files']
            active_tool = None
        elif kind not in ('http_attempt', 'request_rejected'):
            raise auth.AuthorizationError('Unexpected event before extension dispatch')
    _require(auth.encode(payload) == auth.encode(expected)
             and evidence._snapshot(session_dir / 'workspace') == workspace_files,
             'The extension payload or workspace differs from its verified history')


class AuthorizedHTTPTransport(_HTTPTransport):
    """An assigned extension that can replay the first eight turns without credentials."""

    mode = 'live_http'

    def __init__(self, grant, plan, folder, credential_supplier, history):
        _require(type(grant) is auth.RunGrant and callable(credential_supplier) and plan['provider'] == 'openai',
                 'An active single-session extension grant and credential supplier are required')
        plan = deepcopy(plan)
        folder = auth.canonical_path(folder)
        grant.assign(plan, folder)
        _require(all(len(value) == REPLAY_TURNS for value in (
            history.requests, history.responses, history.http_evidence, history.tools)),
            'The authorized extension needs exactly eight verified local replay turns')
        super().__init__('openai')
        self._grant = grant
        self._plan = plan
        self._session_dir = folder
        self._credential_supplier = credential_supplier
        self._history = history
        self._attempt_count = 0
        self._mutex = Lock()

    def preflight(self, plan=None, output_dir=None):
        if plan is not None:
            _require(auth.encode(plan) == auth.encode(self._plan), 'Extension transport plan changed')
        if output_dir is not None:
            _require(auth.canonical_path(output_dir) == self._session_dir, 'Extension output path changed')
        self._grant.check(self._plan, self._session_dir)

    def send(self, payload, *, session_remaining_seconds):
        with self._mutex:
            self.last_http_evidence = None
            timeout_budget(session_remaining_seconds)
            started = time.monotonic()
            self.preflight()
            attempt = self._attempt_count + 1
            _check_dispatch(self._grant.launch, self._plan, self._session_dir, payload, attempt)
            if attempt <= REPLAY_TURNS:
                index = attempt - 1
                _require(auth.encode(payload) == auth.encode(self._history.requests[index]),
                         'Local replay does not reproduce the original request bytes')
                self._attempt_count = attempt
                self.last_http_evidence = deepcopy(self._history.http_evidence[index])
                return deepcopy(self._history.responses[index])
            _check_extension_context(self._session_dir, self._history, self._plan, payload, attempt)
            timeout_budget(session_remaining_seconds - (time.monotonic() - started))
            self._attempt_count = attempt
            credential = self._credential_supplier(self.provider)
            remaining = session_remaining_seconds - (time.monotonic() - started)
            return self._attempt(payload, remaining, credential,
                                 lambda request: _wire_child(request, self._grant, self._plan['session_id'], attempt))


def _wire_child(request, grant, session_id, attempt):
    data = auth.encode({
        'config_path': str(grant.launch.config_path),
        'config_sha256': grant.launch.sha256,
        'claim_sha256': grant.claim_sha256,
        'session_id': session_id,
        'attempt': attempt,
        'request': {**vars(request), 'body': base64.b64encode(request.body).decode('ascii')},
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
    attempt = data['attempt']
    _require(type(attempt) is int and attempt > REPLAY_TURNS, 'An archived turn cannot dispatch live')
    from turn_extension_v1 import scope
    from turn_extension_v1.history import load_history

    launch = scope.load_launch()
    _require(auth.canonical_path(data['config_path']) == launch.config_path
             and data['config_sha256'] == launch.sha256, 'The wire worker requires the pinned extension scope')
    controller_pid = os.getppid()
    auth.verify_claim(launch, data['claim_sha256'], controller_pid=controller_pid)
    plan = launch.session_plan(data['session_id'])
    session_dir = launch.session_directory(plan['session_id'])
    request = dict(data['request'])
    request['body'] = base64.b64decode(request['body'], validate=True)
    request = PreparedHTTPRequest(**request)
    payload = auth.json_object(request.body)
    intent = _check_dispatch(launch, plan, session_dir, payload, attempt)
    history = load_history(scope.ORIGIN, scope.original_plan())
    _check_extension_context(session_dir, history, plan, payload, attempt)
    _require(request.provider == plan['provider'] == 'openai' and request.endpoint == ENDPOINTS['openai'],
             'The extension request endpoint differs from the approved provider')
    value = request.headers.get('Authorization', '')
    _require(value.startswith('Bearer '), 'The approved OpenAI authorization header is required')
    expected = build_http_request('openai', payload, value.removeprefix('Bearer '), request.timeout_seconds)
    _require(request == expected and os.getppid() == controller_pid, 'The approved wire request or controller changed')

    marker = dispatch_directory(launch) / f"{plan['session_id']}.{attempt:04d}.json"
    auth._write_exclusive(marker, {
        'claim_sha256': data['claim_sha256'],
        'session_id': plan['session_id'],
        'attempt': attempt,
        'dispatch_intent_sha256': intent['sha256'],
    })
    _require(os.getppid() == controller_pid, 'The wire worker lost its approved controller')
    return _https_once(request)


if __name__ == '__main__' and sys.argv[1:] == ['--wire-child']:
    wire_input = sys.stdin.buffer.read(auth.RECORD_LIMIT + 1)
    _require(len(wire_input) <= auth.RECORD_LIMIT, 'Wire input exceeded its bound')
    response = _run_authorized_child(auth.json_object(wire_input))
    sys.stdout.buffer.write(auth.encode(response))
