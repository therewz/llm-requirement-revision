"""Run and score the one approved supplementary turn extension."""

import base64
from decimal import Decimal
import json
from pathlib import Path
import time

from cleaned_continuation_v1 import runner as primary
from cleaned_opening_v1 import authorization as records, runner as opening

from . import engine, scope, transport
from .history import ReplayTools

prior = opening.prior


def _clock(prior_elapsed_seconds):
    # The frozen engine starts its timer at the first clock reading.
    offset = 0

    def now():
        nonlocal offset
        tick = time.monotonic() + offset
        offset = prior_elapsed_seconds
        return tick

    return now


def _attest(launch):
    if opening._host() != launch.config['host']:
        raise records.AuthorizationError('The current Mac differs from the approved grading host')


def _verify_replay(events, folder, history, mode):
    expected = {
        'dispatch_intent': history.requests,
        'response_saved': history.responses,
    }
    if mode == 'live_http':
        expected['http_attempt'] = history.http_evidence
    for name, values in expected.items():
        replay = [e for e in events if e['event'] == name and e['attempt'] <= scope.ORIGINAL_TURNS]
        if (len(replay) != len(values)
                or any((folder / event['files'][0]['path']).read_bytes() != records.encode(value)
                       for event, value in zip(replay, values))):
            raise records.AuthorizationError('Supplementary replay differs from the archived responses')
    tools = [e for e in events if e['event'] == 'tool_result' and e['tool_index'] <= len(history.tools)]
    if (len(tools) != len(history.tools)
            or any(event['workspace_files'] != saved.workspace_files
                   or (folder / event['files'][0]['path']).read_bytes() != records.encode(saved.result)
                   for event, saved in zip(tools, history.tools))):
        raise records.AuthorizationError('The original tool history was not reconstructed')


def _new_requests(launch, plan, events, grant):
    marker_dir = transport.dispatch_directory(launch)
    by_session = primary._markers(marker_dir, {plan['session_id']: plan}, {grant.claim_sha256})
    markers = by_session.get(plan['session_id'], {})
    intents = {e['attempt']: e['sha256'] for e in events if e['event'] == 'dispatch_intent'
               and e['attempt'] > scope.ORIGINAL_TURNS}
    receipts = {e['attempt']: e['outcome'] for e in events if e['event'] == 'http_attempt'
                and e['attempt'] > scope.ORIGINAL_TURNS}
    known = {n for n, status in receipts.items() if status in ('received', 'rejected')}
    if (not known <= markers.keys() <= intents.keys()
            or any(marker['dispatch_intent_sha256'] != intents[n] for n, marker in markers.items())):
        raise records.AuthorizationError('New dispatch markers disagree with supplementary requests')
    return {
        'markers': len(markers),
        'accepted': sum(receipts.get(n) == 'received' for n in markers),
        'rejected': sum(receipts.get(n) == 'rejected' for n in markers),
        'uncertain': sum(n not in known for n in markers),
    }


def _execute(launch, output, history, connection, *, mode, grant=None):
    plan = launch.config['sessions'][0]
    original_plan = scope.original_plan()
    if output.parent != launch.output_root:
        raise records.AuthorizationError('Output is outside the supplementary run directory')
    records.canonical_path(output)
    if mode == 'live_http':
        if grant is None or grant.launch != launch or output != launch.run_directory:
            raise records.AuthorizationError('The extension needs its exact active grant')
    elif mode != 'http_fixture' or grant is not None or output == launch.run_directory:
        raise records.AuthorizationError('Fixture execution needs a separate output directory')

    output.mkdir(mode=0o700)
    header = {
        'run_id': launch.run_id, 'selection_sha256': launch.sha256, 'mode': mode,
        'evidence_class': 'POST_HOC_TURN_LIMIT_SENSITIVITY',
        'origin': launch.config['origin'], 'run_directory': str(output),
        'claim_sha256': grant.claim_sha256 if grant is not None else None,
    }
    prior._record_once(output / 'run.json', header)
    ledger_path = output / 'ledger.json'
    sid = plan['session_id']
    prior._save(ledger_path, {sid: primary._reservation(plan)})
    folder = output / 'sessions' / sid
    adapter = prior._adapter(plan)
    engine.run_session(plan, folder, connection(plan, folder), adapter,
                       lambda workspace, limits: ReplayTools(workspace, limits, history),
                       clock=_clock(history.elapsed_seconds))
    result = engine.verify_session(plan, folder, adapter)
    events = engine.Journal(folder).events
    _verify_replay(events, folder, history, mode)
    requests = _new_requests(launch, plan, events, grant) if grant is not None else None

    def verify_scoring_plan(scoring_plan, session_dir, session_adapter):
        if scoring_plan != original_plan:
            raise records.AuthorizationError('The original scientific plan changed')
        return engine.verify_session(plan, session_dir, session_adapter)

    envelope = None
    if result['status'] == 'completed':
        grader = primary._grader(launch.config, launch.sha256)
        envelope = grader.evaluate_completed(original_plan, folder, adapter, verify_session=verify_scoring_plan)
        if grader.verify_evaluation(original_plan, folder, adapter, verify_session=verify_scoring_plan) != envelope:
            raise records.AuthorizationError('The supplementary grade differs on verification')
    entry = prior._entry(plan, folder, result, envelope, mode)
    prior._save(ledger_path, {sid: entry})
    usage = result['reported_cost_usd']
    incremental = None
    if usage is not None:
        incremental = sum((Decimal(event['cost_usd']) for event in events if event['event'] == 'usage'
                           and event['attempt'] > scope.ORIGINAL_TURNS), Decimal(0))
        if Decimal(usage) != history.usage_usd + incremental:
            raise records.AuthorizationError('Archived and incremental charges did not reconcile')
    new_intents = [e for e in events if e['event'] == 'dispatch_intent' and e['attempt'] > scope.ORIGINAL_TURNS]
    if new_intents:
        first = new_intents[0]
        if (first['turn'] != scope.ORIGINAL_TURNS + 1
                or first['files'][0]['sha256'] != launch.config['origin']['first_new_request_sha256']):
            raise records.AuthorizationError('The extension did not begin at the exact ninth turn')
    if scope.load_launch() != launch:
        raise records.AuthorizationError('The extension scope changed during execution')
    summary = {
        **header, 'session_id': sid, 'session_status': result['status'], 'reason': result['reason'],
        'model_turns_including_replay': result['model_turns'],
        'tool_calls_including_replay': result['tool_calls'],
        'new_attempts': len(new_intents), 'new_wire_requests': requests,
        'recorded_session_usage_usd': usage,
        'new_usage_usd': None if incremental is None else str(incremental),
        'evaluation_status': None if envelope is None else envelope['status'],
        'evaluation_sha256': entry['evaluation_sha256'],
        'final_source_sha256': result['final_source_sha256'],
    }
    prior._record_once(output / 'summary.json', summary)
    return summary


def run_live(credential_supplier):
    launch = scope.load_launch()
    history = scope.verify_history(launch)
    _attest(launch)
    records.verify_available_approval(launch)
    value = credential_supplier('openai')
    transport.build_http_request('openai', {}, value, 1)
    grant = records.claim_approval(launch)
    return _execute(launch, launch.run_directory, history,
                    lambda p, f: transport.AuthorizedHTTPTransport(grant, p, f, lambda _: value, history),
                    mode='live_http', grant=grant)


def run_fixture(output):
    launch = scope.load_launch()
    history = scope.verify_history(launch)
    _attest(launch)
    attempt = 0

    def wire(request):
        nonlocal attempt
        attempt += 1
        payload = json.loads(request.body)
        if attempt <= scope.ORIGINAL_TURNS:
            if payload != history.requests[attempt - 1]:
                raise records.AuthorizationError('A fixture replay request differs')
            saved = history.http_evidence[attempt - 1]['receipt']
            return saved['status_code'], saved['headers'], base64.b64decode(saved['body_base64'], validate=True)
        if attempt != scope.ORIGINAL_TURNS + 1 or payload != history.next_request:
            raise records.AuthorizationError('Unexpected offline extension request')
        reply = {
            'id': 'offline_turn_extension_complete', 'model': 'gpt-6.1-sol', 'status': 'completed',
            'output': [{'type': 'message', 'status': 'completed', 'role': 'assistant',
                        'content': [{'type': 'output_text', 'text': 'Synthetic completion after archived tool check.'}]}],
            'usage': {'input_tokens': 100, 'output_tokens': 50},
        }
        return 200, {'x-request-id': 'offline_turn_extension_ninth_request'}, json.dumps(reply).encode()

    return _execute(launch, Path(output), history, lambda _p, _f: transport.HTTPFixtureTransport('openai', wire),
                    mode='http_fixture')
