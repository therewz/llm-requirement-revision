"""The frozen editing loop with admission for the one-session extension transport."""

from copy import deepcopy
from decimal import Decimal
import math
from pathlib import Path
import time

from cleaned_opening_v1.engine import (
    DEFAULT_LIMITS, IntegrityError, Journal, KnownRejection, MockTransport,
    ReplayTransport, _atomic, _decimal, _finish, _reservation, _save_http_evidence,
    _snapshot, _terminal_consistency, _validate_plan, digest, encoded, usage_cost,
    verify_session,
)
from .transport import (
    AuthorizedHTTPTransport, BeforeDispatchLimit, DeliveryUncertain,
    HTTPFixtureTransport, HTTPRejected,
)


def run_session(plan, output_dir, transport, adapter, runtime_factory, *, clock=time.monotonic, sleep=time.sleep):
    """Run or verify a bounded session. Never automatically resend inflight work.

    Terminal statuses distinguish model completion, refusal/truncation, limits,
    request rejection, delivery uncertainty, malformed data and runtime failure.
    The resulting final source is not scored here and is never repaired.
    """
    if type(transport) not in (MockTransport, ReplayTransport, HTTPFixtureTransport, AuthorizedHTTPTransport):
        raise ValueError('Only built-in transports are allowed')
    uses_http = type(transport) in (HTTPFixtureTransport, AuthorizedHTTPTransport)
    if uses_http:
        if transport.provider != plan['provider']:
            raise ValueError('Transport provider does not match the plan')
        if type(transport) is AuthorizedHTTPTransport:
            transport.preflight(plan, output_dir)
        else:
            transport.preflight()
    limits = _validate_plan(plan)
    output = Path(output_dir)
    if output.is_symlink():
        raise IntegrityError('Output root is a symlink')
    mode = transport.mode if uses_http else ('replay' if type(transport) is ReplayTransport else 'mock')
    frozen = {'plan': plan, 'effective_limits': limits, 'mode': mode}
    plan_bytes = encoded(frozen)
    workspace = output / 'workspace'
    if output.exists():
        if not (output / 'plan.json').is_file() or (output / 'plan.json').read_bytes() != plan_bytes:
            raise IntegrityError('Existing output has a different or missing plan')
        journal = Journal(output)
        if journal.events and journal.events[-1]['event'] == 'terminal':
            result = journal.events[-1]['result']
            if result['mode'] != mode:
                raise IntegrityError('Terminal transport mode differs')
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
                if uses_http:
                    remaining = limits['session_seconds'] - (dispatch_started - start)
                    raw = transport.send(request, session_remaining_seconds=remaining)
                else:
                    raw = transport.send(request)
            except BeforeDispatchLimit:
                if uses_http:
                    _save_http_evidence(journal, prefix, attempts, transport, 'not_sent')
                return finish('session_limit', 'deadline_before_transport')
            except (KnownRejection, HTTPRejected) as exc:
                if uses_http:
                    _save_http_evidence(journal, prefix, attempts, transport, 'rejected')
                retry_after = exc.retry_after
                journal.append('request_rejected', attempt=attempts, status_code=exc.status_code,
                               generation_usage='not_reported', retry_index=retries,
                               retry_after_seconds=retry_after if math.isfinite(retry_after) else None,
                               latency_seconds=max(0, clock() - dispatch_started))
                if exc.status_code == 429 and retries < limits['max_429_retries']:
                    retries += 1
                    delay = max(retry_after, 2 ** (retries - 1))
                    if delay > limits['max_retry_backoff_seconds']:
                        return finish('request_rejected', 'HTTP_429_retry_delay_out_of_bounds')
                    if clock() - start + delay >= limits['session_seconds']:
                        return finish('session_limit', 'retry_would_exceed_wall_time')
                    sleep(delay)
                    continue
                return finish('request_rejected', 'HTTP_' + str(exc.status_code))
            except Exception as exc:
                if uses_http:
                    _save_http_evidence(journal, prefix, attempts, transport, 'uncertain')
                reason = exc.reason if isinstance(exc, DeliveryUncertain) else 'transport_exception'
                journal.append('delivery_uncertain', attempt=attempts, exception_type=type(exc).__name__, reason=reason)
                return finish('delivery_uncertain', reason, None)
            if uses_http:
                _save_http_evidence(journal, prefix, attempts, transport, 'received')
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

