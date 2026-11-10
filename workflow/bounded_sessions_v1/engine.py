"""Offline bounded editing sessions. There is deliberately no live transport.

All provider responses are fixtures or replay data. Participant execution is
delegated to a separately reviewed workspace runtime, never performed here.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time


class IntegrityError(ValueError):
    pass


class KnownRejection(Exception):
    """A saved/fixture explicit rejection, not a timeout with unknown delivery."""
    def __init__(self, status_code, retry_after=0):
        if type(status_code) is not int or not 400 <= status_code < 500:
            raise ValueError('Only explicit 4xx rejections qualify')
        self.status_code, self.retry_after = status_code, max(0, float(retry_after))


class MockTransport:
    def __init__(self, responses):
        self.responses, self.requests = list(responses), []

    def send(self, request):
        self.requests.append(deepcopy(request))
        if not self.responses:
            raise RuntimeError('Fixture exhausted')
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return deepcopy(value)


class ReplayTransport(MockTransport):
    """Explicitly labelled raw-response replay; never sends a network request."""


DEFAULT_LIMITS = {
    'max_model_turns': 8, 'max_tool_calls': 12, 'session_seconds': 600,
    'max_output_tokens': 4096, 'max_request_bytes': 131072,
    'max_response_bytes': 2097152, 'max_tool_result_bytes': 32768,
    'max_429_retries': 1, 'max_retry_backoff_seconds': 5,
    'input_token_margin': 2048, 'session_cost_cap_usd': '1.00',
}


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def _atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    if tmp.is_symlink() or path.is_symlink():
        raise IntegrityError('Symlink in orchestration output')
    with tmp.open('wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _snapshot(workspace):
    files = {}
    for p in sorted(workspace.rglob('*')):
        if p.is_symlink():
            raise IntegrityError('Workspace contains a symlink')
        if p.is_file():
            data = p.read_bytes()
            files[p.relative_to(workspace).as_posix()] = {'sha256': digest(data), 'bytes': len(data)}
    return files


class Journal:
    """Hash-chained append-only events; this detects corruption, not forgery by an owner."""
    def __init__(self, root):
        self.root, self.events = root, []
        path = root / 'events.jsonl'
        if path.exists():
            previous = None
            for line in path.read_bytes().splitlines(keepends=True):
                try:
                    item = json.loads(line)
                    payload = {k: v for k, v in item.items() if k != 'sha256'}
                    assert item['seq'] == len(self.events)
                    assert item['previous_sha256'] == previous
                    assert item['sha256'] == digest(encoded(payload))
                    assert line == encoded(item)
                    for ref in item.get('files', []):
                        file = root / ref['path']
                        assert file.resolve().is_relative_to(root.resolve()) and not file.is_symlink()
                        assert digest(file.read_bytes()) == ref['sha256']
                except (ValueError, KeyError, AssertionError, OSError) as exc:
                    raise IntegrityError('Event or artifact verification failed') from exc
                self.events.append(item)
                previous = item['sha256']

    def write_json(self, relative, value):
        path = self.root / relative
        if path.exists():
            raise IntegrityError('Refusing to replace recorded artifact')
        data = encoded(value)
        _atomic(path, data)
        return {'path': relative, 'sha256': digest(data), 'bytes': len(data)}

    def append(self, event, **values):
        payload = {'seq': len(self.events), 'previous_sha256': self.events[-1]['sha256'] if self.events else None,
                   'event': event, 'timestamp_utc': datetime.now(timezone.utc).isoformat(), **values}
        item = {**payload, 'sha256': digest(encoded(payload))}
        with (self.root / 'events.jsonl').open('ab') as f:
            f.write(encoded(item)); f.flush(); os.fsync(f.fileno())
        directory = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        self.events.append(item)
        return item


def _decimal(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('Invalid rate/cap') from exc
    if not result.is_finite() or result < 0:
        raise ValueError('Rate/cap must be finite and nonnegative')
    return result


def usage_cost(usage, pricing):
    """Normalized input total includes cached subsets; no missing usage becomes zero."""
    if not isinstance(usage, dict):
        raise ValueError('Missing usage')
    counts = {}
    for key in ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_write_input_tokens'):
        value = usage.get(key, 0 if key.startswith('cache_') else None)
        if type(value) is not int or value < 0:
            raise ValueError('Incomplete or invalid usage')
        counts[key] = value
    read, write = counts['cache_read_input_tokens'], counts['cache_write_input_tokens']
    ordinary = counts['input_tokens'] - read - write
    if ordinary < 0:
        raise ValueError('Cached input exceeds total input')
    cost = Decimal(ordinary) * _decimal(pricing['input_per_million'])
    cost += Decimal(counts['output_tokens']) * _decimal(pricing['output_per_million'])
    if read:
        cost += Decimal(read) * _decimal(pricing['cache_read_per_million'])
    if write:
        cost += Decimal(write) * _decimal(pricing['cache_write_per_million'])
    return cost / Decimal(1000000)


def _reservation(request_bytes, limits, pricing):
    input_rate = max(_decimal(pricing[k]) for k in pricing if k in
                     ('input_per_million', 'cache_read_per_million', 'cache_write_per_million'))
    return ((Decimal(request_bytes + limits['input_token_margin']) * input_rate
             + Decimal(limits['max_output_tokens']) * _decimal(pricing['output_per_million'])) / Decimal(1000000))


def _validate_plan(plan):
    required = ('session_id', 'participant_id', 'task', 'group', 'condition', 'provider', 'model', 'repeat',
                'packet_dir', 'prompt_sha256', 'source_sha256', 'operational_instruction', 'tools', 'settings', 'pricing')
    if any(k not in plan for k in required):
        raise ValueError('Incomplete plan')
    if plan.get('live_enabled', False) is not False:
        raise ValueError('Live execution is code-locked')
    if plan['condition'] not in ('RR', 'SA', 'EW') or plan['task'] not in ('A', 'B'):
        raise ValueError('Invalid study dimensions')
    if type(plan['repeat']) is not int or plan['repeat'] < 1:
        raise ValueError('Invalid repeat')
    limits = {**DEFAULT_LIMITS, **plan.get('limits', {})}
    for key in DEFAULT_LIMITS:
        if key == 'session_cost_cap_usd':
            continue
        if type(limits[key]) is not int or limits[key] < (0 if key in ('max_429_retries', 'input_token_margin') else 1):
            raise ValueError('Invalid limit: ' + key)
    _decimal(limits['session_cost_cap_usd'])
    for key in ('input_per_million', 'output_per_million'):
        _decimal(plan['pricing'][key])
    if not isinstance(plan['operational_instruction'], str) or not plan['operational_instruction'].strip():
        raise ValueError('Operational instruction required')
    if not isinstance(plan['tools'], list):
        raise ValueError('Tools must be a list')
    tool_names = [t.get('name') if isinstance(t, dict) else None for t in plan['tools']]
    if len(set(tool_names)) != len(tool_names) or any(n not in ('read_file', 'write_file', 'run_python') for n in tool_names):
        raise ValueError('Invalid or repeated tool schema name')
    encoded(plan)
    return limits


def _terminal_consistency(journal, result, plan, adapter):
    """Derive terminal claims from saved responses; a checkpoint is not evidence."""
    try:
        for key in ('session_id', 'participant_id', 'task', 'group', 'condition', 'provider', 'model', 'repeat'):
            assert result[key] == plan[key]
        assert result['live_execution'] is False and result['scientific_score'] is None
        assert result['transport_attempts'] == sum(e['event'] == 'dispatch_intent' for e in journal.events)
        assert result['model_turns'] == sum(e['event'] in ('response_saved', 'malformed_response') for e in journal.events)
        assert result['tool_calls'] == sum(e['event'] == 'tool_intent' for e in journal.events)
        raw_by_attempt, parsed_by_attempt, costs = {}, {}, []
        for event in journal.events:
            if event['event'] == 'response_saved':
                raw_by_attempt[event['attempt']] = json.loads((journal.root / event['files'][0]['path']).read_bytes())
            elif event['event'] == 'response_parsed':
                saved = json.loads((journal.root / event['files'][0]['path']).read_bytes())
                rebuilt = adapter.parse(deepcopy(raw_by_attempt[event['attempt']]))
                assert encoded(rebuilt) == encoded(saved)
                parsed_by_attempt[event['attempt']] = rebuilt
            elif event['event'] == 'usage':
                parsed = parsed_by_attempt[event['attempt']]
                assert event['usage'] == parsed['usage']
                cost = usage_cost(parsed['usage'], plan['pricing'])
                assert _decimal(event['cost_usd']) == cost
                costs.append(cost)
                assert _decimal(event['cumulative_cost_usd']) == sum(costs, Decimal(0))
        assert result['usage_complete'] == (result['reported_cost_usd'] is not None)
        if result['usage_complete']:
            assert _decimal(result['reported_cost_usd']) == sum(costs, Decimal(0))
        if result['status'] == 'completed':
            assert parsed_by_attempt and not result['resumed_uncertain']
            last = parsed_by_attempt[max(parsed_by_attempt)]
            assert last['status'] == 'completed' and last['model'] == plan['model']
            assert result['usage_complete']
            assert len(costs) == len(parsed_by_attempt) == len(raw_by_attempt)
            ids = [p['response_id'] for p in parsed_by_attempt.values()]
            assert all(isinstance(x, str) and x for x in ids) and len(set(ids)) == len(ids)
            assert all(p['model'] == plan['model'] for p in parsed_by_attempt.values())
            assert result['final_source_sha256'] is not None
    except (AssertionError, ValueError, KeyError, TypeError, OSError) as exc:
        raise IntegrityError('Terminal summary disagrees with recorded response evidence') from exc


def verify_session(plan, output_dir, adapter):
    """Read-only verification for schedulers/evaluators; never repairs or dispatches."""
    output = Path(output_dir)
    frozen = json.loads((output / 'plan.json').read_bytes())
    if frozen['plan'] != plan or frozen['effective_limits'] != _validate_plan(plan) or frozen['mode'] not in ('mock', 'replay'):
        raise IntegrityError('Recorded session plan differs')
    journal = Journal(output)
    if not journal.events or journal.events[-1]['event'] != 'terminal':
        raise IntegrityError('Session has no terminal evidence')
    result = journal.events[-1]['result']
    _terminal_consistency(journal, result, plan, adapter)
    if (output / 'result.json').read_bytes() != encoded(result):
        raise IntegrityError('Result differs from terminal evidence')
    if _snapshot(output / 'workspace') != result['workspace_files']:
        raise IntegrityError('Terminal workspace differs from recorded files')
    if result['final_source_sha256'] is not None:
        if digest((output / 'final.py').read_bytes()) != result['final_source_sha256']:
            raise IntegrityError('Final source changed')
        if result['workspace_files']['src/solution.py']['sha256'] != result['final_source_sha256']:
            raise IntegrityError('Final and workspace source differ')
    return result


def run_session(plan, output_dir, transport, adapter, runtime_factory, *, clock=time.monotonic, sleep=time.sleep):
    """Run or verify a terminal mock/replay session. Never automatically resend inflight work.

    Terminal statuses distinguish model completion, refusal/truncation, limits,
    request rejection, delivery uncertainty, malformed data and runtime failure.
    The resulting final source is not scored here and is never repaired.
    """
    if type(transport) not in (MockTransport, ReplayTransport):
        raise ValueError('Only built-in offline mock/replay transports are allowed')
    limits = _validate_plan(plan)
    output = Path(output_dir)
    if output.is_symlink():
        raise IntegrityError('Output root is a symlink')
    mode = 'replay' if type(transport) is ReplayTransport else 'mock'
    frozen = {'plan': plan, 'effective_limits': limits, 'mode': mode}
    plan_bytes = encoded(frozen)
    workspace = output / 'workspace'
    if output.exists():
        if not (output / 'plan.json').is_file() or (output / 'plan.json').read_bytes() != plan_bytes:
            raise IntegrityError('Existing output has a different or missing plan')
        journal = Journal(output)
        if journal.events and journal.events[-1]['event'] == 'terminal':
            result = journal.events[-1]['result']
            _terminal_consistency(journal, result, plan, adapter)
            if (output / 'result.json').exists() and (output / 'result.json').read_bytes() != encoded(result):
                raise IntegrityError('Result differs from terminal evidence')
            if _snapshot(workspace) != result['workspace_files']:
                raise IntegrityError('Terminal workspace differs from recorded files')
            final = output / 'final.py'
            if result['final_source_sha256'] is not None and digest(final.read_bytes()) != result['final_source_sha256']:
                raise IntegrityError('Final source changed')
            if not (output / 'result.json').exists():
                _atomic(output / 'result.json', encoded(result))
            return result
        # A crash anywhere in a nonterminal session may have dispatched a call or
        # partially applied a tool. Preserve it; do not infer a safe resend.
        return _finish(journal, plan, mode, 'delivery_uncertain', 'nonterminal_session_requires_reconciliation',
                       workspace, sum(e['event'] in ('response_saved', 'malformed_response') for e in journal.events),
                       sum(e['event'] == 'tool_intent' for e in journal.events), None,
                       sum(e['event'] == 'dispatch_intent' for e in journal.events), resumed_uncertain=True)
    output.mkdir(parents=True)
    _atomic(output / 'plan.json', plan_bytes)
    journal = Journal(output)
    packet = Path(plan['packet_dir'])
    prompt_file, source_file = packet / 'prompt_draft.md', packet / 'workspace/src/solution.py'
    prompt, source = prompt_file.read_bytes(), source_file.read_bytes()
    if digest(prompt) != plan['prompt_sha256'] or digest(source) != plan['source_sha256']:
        raise IntegrityError('Frozen packet bytes mismatch')
    text = prompt.decode('utf-8')
    if not text.strip():
        raise IntegrityError('Empty prompt')
    workspace.mkdir(); (workspace / 'src').mkdir()
    _atomic(workspace / 'src/solution.py', source)
    initial = _snapshot(workspace)
    journal.append('initialized', plan_sha256=digest(plan_bytes), workspace_files=initial,
                   files=[{'path': 'plan.json', 'sha256': digest(plan_bytes), 'bytes': len(plan_bytes)}])
    messages = [{'role': 'system', 'content': plan['operational_instruction']}, {'role': 'user', 'content': text}]
    try:
        runtime = runtime_factory(workspace, limits)
    except Exception as exc:
        return _finish(journal, plan, mode, 'infrastructure_failure', type(exc).__name__, workspace, 0, 0, Decimal(0), 0)
    start, turns, calls, attempts, total = clock(), 0, 0, 0, Decimal(0)
    response_ids, tool_ids = set(), set()

    def finish(status, reason, cost=...):
        return _finish(journal, plan, mode, status, reason, workspace, turns, calls,
                       total if cost is ... else cost, attempts)

    while turns < limits['max_model_turns']:
        if clock() - start >= limits['session_seconds']:
            return finish('session_limit', 'wall_time_limit')
        try:
            request = adapter.encode(plan['model'], deepcopy(messages), deepcopy(plan['tools']),
                                     limits['max_output_tokens'], deepcopy(plan['settings']))
            request_data = encoded(request)
        except Exception as exc:
            return finish('infrastructure_failure', 'encode_' + type(exc).__name__)
        if len(request_data) > limits['max_request_bytes']:
            return finish('context_limit', 'request_bytes_exceed_limit_no_truncation')
        reservation = _reservation(len(request_data), limits, plan['pricing'])
        if total + reservation > _decimal(limits['session_cost_cap_usd']):
            return finish('budget_limit', 'estimated_pre_send_reservation')
        retries = 0
        while True:
            attempts += 1
            prefix = f'attempts/{attempts:04d}'
            ref = journal.write_json(prefix + '_request.json', request)
            journal.append('dispatch_intent', turn=turns + 1, attempt=attempts, files=[ref],
                           reservation_usd=str(reservation), reservation_method='serialized_utf8_bytes_plus_margin_not_provider_bound')
            dispatch_started = clock()
            try:
                raw = transport.send(request)
            except KnownRejection as exc:
                journal.append('request_rejected', attempt=attempts, status_code=exc.status_code,
                               generation_usage='not_reported', retry_index=retries,
                               retry_after_seconds=exc.retry_after, latency_seconds=max(0, clock() - dispatch_started))
                if exc.status_code == 429 and retries < limits['max_429_retries']:
                    retries += 1
                    delay = min(max(exc.retry_after, 2 ** (retries - 1)), limits['max_retry_backoff_seconds'])
                    if clock() - start + delay >= limits['session_seconds']:
                        return finish('session_limit', 'retry_would_exceed_wall_time')
                    sleep(delay)
                    continue
                return finish('request_rejected', 'HTTP_' + str(exc.status_code))
            except Exception as exc:
                journal.append('delivery_uncertain', attempt=attempts, exception_type=type(exc).__name__)
                return finish('delivery_uncertain', 'transport_exception', None)
            break
        turns += 1
        try:
            response_data = encoded(raw)
        except Exception:
            journal.append('malformed_response', attempt=attempts, reason='not_json_serializable')
            return finish('malformed_response', 'not_json_serializable', None)
        ref = journal.write_json(prefix + '_response.json', raw)
        journal.append('response_saved', attempt=attempts, files=[ref], latency_seconds=max(0, clock() - dispatch_started))
        if len(response_data) > limits['max_response_bytes']:
            return finish('malformed_response', 'response_bytes_exceed_limit', None)
        try:
            parsed = adapter.parse(deepcopy(raw))
            ref = journal.write_json(prefix + '_parsed.json', parsed)
            journal.append('response_parsed', attempt=attempts, files=[ref])
            call_cost = usage_cost(parsed.get('usage'), plan['pricing'])
        except Exception as exc:
            return finish('usage_or_parse_unassessable', type(exc).__name__, None)
        total += call_cost
        journal.append('usage', attempt=attempts, usage=parsed['usage'], cost_usd=str(call_cost), cumulative_cost_usd=str(total))
        rid = parsed.get('response_id')
        if not isinstance(rid, str) or not rid or rid in response_ids:
            return finish('response_identity_failure', 'missing_or_duplicate_response_id', None)
        response_ids.add(rid)
        if parsed.get('model') != plan['model']:
            return finish('response_identity_failure', 'returned_model_not_exact_match')
        if total > _decimal(limits['session_cost_cap_usd']):
            return finish('budget_limit', 'reported_usage_exceeded_estimate_or_cap')
        if clock() - start >= limits['session_seconds']:
            return finish('session_limit', 'wall_time_limit_after_response')
        status = parsed.get('status')
        if status in ('completed', 'refusal', 'truncated', 'malformed'):
            return finish(status, 'provider_' + status)
        if status != 'tool_calls':
            return finish('malformed_response', 'unknown_normalized_status')
        tc = parsed.get('tool_calls')
        if not isinstance(tc, list) or not tc or any(not isinstance(x, dict) for x in tc):
            return finish('malformed_response', 'missing_tool_calls')
        ids = [x.get('id') for x in tc]
        if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids) or tool_ids.intersection(ids):
            return finish('malformed_response', 'invalid_tool_call_ids')
        tool_ids.update(ids)
        if calls + len(tc) > limits['max_tool_calls']:
            return finish('tool_limit', 'requested_batch_exceeds_remaining_tools')
        allowed_tools = {t['name'] for t in plan['tools']}
        if any(x.get('name') not in allowed_tools or not isinstance(x.get('arguments'), dict) for x in tc):
            return finish('malformed_response', 'invalid_or_unoffered_tool_call')
        messages.append({'role': 'assistant', 'content': parsed.get('text', ''),
                         'continuation': parsed.get('continuation'), 'tool_calls': deepcopy(tc)})
        for item in tc:
            if clock() - start >= limits['session_seconds']:
                return finish('session_limit', 'wall_time_limit_before_tool')
            name, args = item.get('name'), item.get('arguments')
            if name not in ('read_file', 'write_file', 'run_python') or not isinstance(args, dict):
                return finish('malformed_response', 'invalid_tool_call')
            calls += 1
            journal.append('tool_intent', turn=turns, tool_index=calls, tool_call=deepcopy(item))
            try:
                result = runtime.execute(name, deepcopy(args))
                if not isinstance(result, dict):
                    raise ValueError('Tool result must be an object')
                data = encoded(result)
            except Exception as exc:
                journal.append('tool_failure', tool_index=calls, exception_type=type(exc).__name__)
                return finish('infrastructure_failure', 'runtime_exception')
            if len(data) > limits['max_tool_result_bytes']:
                result = {'status': 'output_limit', 'truncated': True,
                          'original_bytes': len(data), 'original_sha256': digest(data),
                          'content': data[:limits['max_tool_result_bytes'] // 2].decode('utf-8', errors='replace')}
            ref = journal.write_json(f'tools/{calls:04d}.json', result)
            journal.append('tool_result', tool_index=calls, files=[ref], workspace_files=_snapshot(workspace))
            if result.get('status') == 'isolation_unavailable':
                return finish('infrastructure_failure', 'isolation_unavailable')
            messages.append({'role': 'tool', 'tool_call_id': item['id'], 'name': name,
                             'content': encoded(result).decode('utf-8')})
    return finish('session_limit', 'model_turn_limit')


def _finish(journal, plan, mode, status, reason, workspace, turns, calls, total, attempts, resumed_uncertain=False):
    snapshot = _snapshot(workspace) if workspace.exists() else {}
    source = workspace / 'src/solution.py'
    final_hash = None
    if source.is_file() and not source.is_symlink():
        data = source.read_bytes()
        final_hash = digest(data)
        _atomic(journal.root / 'final.py', data)
    elif status == 'completed':
        status, reason = 'artifact_missing', 'completed_without_final_source'
    result = {k: plan[k] for k in ('session_id', 'participant_id', 'task', 'group', 'condition', 'provider', 'model', 'repeat')}
    result.update({'mode': mode, 'status': status, 'reason': reason, 'model_turns': turns,
                   'transport_attempts': attempts, 'tool_calls': calls,
                   'reported_cost_usd': None if total is None else str(total),
                   'usage_complete': total is not None, 'workspace_files': snapshot,
                   'final_source_sha256': final_hash, 'resumed_uncertain': resumed_uncertain,
                   'scientific_score': None, 'live_execution': False,
                   'started_at_utc': journal.events[0]['timestamp_utc'] if journal.events else None,
                   'finished_at_utc': datetime.now(timezone.utc).isoformat()})
    journal.append('terminal', result=result)
    _atomic(journal.root / 'result.json', encoded(result))
    return result
