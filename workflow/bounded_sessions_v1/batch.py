"""Offline scheduler with durable, conservative whole-session budget reservations."""
import concurrent.futures
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import threading
from adapters import OpenAIAdapter, ClaudeAdapter
from engine import MockTransport, ReplayTransport, run_session, verify_session, encoded, digest, _atomic, IntegrityError
from runtime import WorkspaceTools

HALT = {'delivery_uncertain', 'infrastructure_failure', 'response_identity_failure',
        'usage_or_parse_unassessable', 'malformed_response', 'malformed', 'artifact_missing'}


def fixture_responses(plan):
    """Three simulated turns: read source, write identical source, finish. No code execution."""
    source = (Path(plan['packet_dir']) / 'workspace/src/solution.py').read_text()
    out = []
    for i, call in enumerate([('read_file', {'path': 'src/solution.py'}),
                             ('write_file', {'path': 'src/solution.py', 'content': source}), None], 1):
        rid = f"mock_{plan['session_id']}_{i}"
        if plan['provider'] == 'openai':
            items = [{'type': 'function_call', 'id': 'fc_' + rid, 'status': 'completed',
                      'call_id': 'call_' + rid, 'name': call[0], 'arguments': json.dumps(call[1])}] if call else [
                      {'type': 'message', 'role': 'assistant', 'status': 'completed',
                       'content': [{'type': 'output_text', 'text': 'Offline fixture: unchanged source.'}]}]
            out.append({'id': rid, 'model': plan['model'], 'status': 'completed', 'output': items,
                        'usage': {'input_tokens': 100, 'output_tokens': 50, 'input_tokens_details': {'cached_tokens': 0}}})
        else:
            items = [{'type': 'tool_use', 'id': 'call_' + rid, 'name': call[0], 'input': call[1]}] if call else [
                {'type': 'text', 'text': 'Offline fixture: unchanged source.'}]
            out.append({'id': rid, 'model': plan['model'], 'type': 'message', 'role': 'assistant',
                        'stop_reason': 'tool_use' if call else 'end_turn', 'content': items,
                        'usage': {'input_tokens': 100, 'output_tokens': 50,
                                  'cache_read_input_tokens': 0, 'cache_creation_input_tokens': 0}})
    return out


def run_batch(plan, output, response_factory=fixture_responses, runtime_factory=WorkspaceTools):
    if plan.get('live_enabled') is not False:
        raise ValueError('Live execution is unavailable')
    output = Path(output)
    if output.is_symlink(): raise IntegrityError('Symlink batch root')
    output.mkdir(parents=True, exist_ok=True)
    lockfile = output / 'running.lock'
    try: fd = lockfile.open('x')
    except FileExistsError: raise IntegrityError('Active or interrupted scheduler lock; reconcile before restarting')
    try:
        fd.write('offline scheduler\n'); fd.close()
        return _run_locked(plan, output, response_factory, runtime_factory)
    finally:
        lockfile.unlink()


def _run_locked(plan, output, response_factory, runtime_factory):
    pbytes = encoded(plan); psha = digest(pbytes)
    ledgerpath = output / 'ledger.json'
    if ledgerpath.exists():
        ledger = json.loads(ledgerpath.read_text())
        if ledger.get('plan_sha256') != psha: raise IntegrityError('Batch plan changed')
        if (output / 'plan.json').read_bytes() != pbytes: raise IntegrityError('Saved batch plan changed')
        if any(r['status'] == 'reserved' for r in ledger['sessions'].values()):
            raise IntegrityError('Interrupted batch reservations require reconciliation; no resubmission')
        byid = {p['session_id']: p for p in plan['sessions']}
        identities = {}
        for sid, stored in ledger['sessions'].items():
            if sid not in byid: raise IntegrityError('Unplanned recorded session')
            p = byid[sid]
            adapter = OpenAIAdapter() if p['provider'] == 'openai' else ClaudeAdapter()
            result = verify_session(p, output / 'sessions' / sid, adapter)
            charge = p['limits']['session_cost_cap_usd'] if result['reported_cost_usd'] is None else result['reported_cost_usd']
            expected = {'provider': p['provider'], 'status': 'terminal',
                        'result_sha256': digest(encoded(result)), 'session_status': result['status'],
                        'charged_or_reserved_usd': str(Decimal(charge)),
                        'cost_uncertain': result['reported_cost_usd'] is None}
            if stored != expected: raise IntegrityError('Cached batch accounting differs from session evidence')
            for raw in parsed_records(output / 'sessions' / sid):
                key = p['provider'] + ':' + raw['response_id']
                if key in identities: ledger['halt_reason'] = 'duplicate_response_id_across_sessions'
                identities[key] = sid
            if result['status'] in HALT or result['reported_cost_usd'] is None:
                ledger['halt_reason'] = result['status']
        if identities != ledger['response_ids']: raise IntegrityError('Cached provider identities differ from evidence')
    else:
        if (output / 'sessions').exists(): raise IntegrityError('Sessions exist without ledger')
        ledger = {'plan_sha256': psha, 'mode': 'mock', 'sessions': {}, 'halt_reason': None,
                  'response_ids': {}, 'real_spend_usd': '0', 'fixture_cost_is_not_real_spend': True}
        _atomic(output / 'plan.json', pbytes)
        _atomic(ledgerpath, encoded(ledger))
    limits = plan['scheduler']; mutex = threading.Lock()
    count = limits['concurrency']; per = limits['per_provider_concurrency']
    if type(count) is not int or type(per) is not int or not 1 <= per <= count <= 32:
        raise ValueError('Invalid concurrency')
    ids = [p['session_id'] for p in plan['sessions']]
    if len(ids) != len(set(ids)): raise ValueError('Duplicate session IDs')
    sem = {p: threading.Semaphore(per) for p in ('openai', 'anthropic')}

    def total(provider=None):
        return sum((Decimal(r['charged_or_reserved_usd']) for r in ledger['sessions'].values()
                    if provider is None or r['provider'] == provider), Decimal(0))

    def one(p):
        sid, provider = p['session_id'], p['provider']
        if '/' in sid or '..' in sid or not sid: raise ValueError('Invalid session ID')
        adapter = OpenAIAdapter() if provider == 'openai' else ClaudeAdapter()
        with sem[provider]:
            with mutex:
                prior = ledger['sessions'].get(sid)
                if prior:
                    if prior['status'] != 'terminal': raise IntegrityError('Unreconciled session')
                    # Verify terminal session evidence rather than trusting this ledger.
                    result = run_session(p, output / 'sessions' / sid, MockTransport([]), adapter, runtime_factory)
                    if digest(encoded(result)) != prior['result_sha256']:
                        raise IntegrityError('Terminal result differs from batch ledger')
                    return result
                if ledger['halt_reason']: return None
                reserve = Decimal(p['limits']['session_cost_cap_usd'])
                if reserve <= 0 or not reserve.is_finite(): raise ValueError('Invalid session reservation')
                if total() + reserve > Decimal(limits['run_cost_cap_usd']) or total(provider) + reserve > Decimal(limits['provider_cost_caps_usd'][provider]):
                    ledger['halt_reason'] = 'budget_reservation_limit'
                    _atomic(ledgerpath, encoded(ledger)); return None
                ledger['sessions'][sid] = {'provider': provider, 'status': 'reserved', 'charged_or_reserved_usd': str(reserve)}
                _atomic(ledgerpath, encoded(ledger))
            try:
                result = run_session(p, output / 'sessions' / sid, MockTransport(response_factory(p)), adapter, runtime_factory)
                parsed = parsed_records(output / 'sessions' / sid)
            except Exception:
                with mutex:
                    ledger['halt_reason'] = 'infrastructure_exception_requires_reconciliation'
                    _atomic(ledgerpath, encoded(ledger))
                raise
            with mutex:
                for raw in parsed:
                    key = provider + ':' + raw['response_id']
                    if key in ledger['response_ids']:
                        ledger['halt_reason'] = 'duplicate_response_id_across_sessions'
                    ledger['response_ids'][key] = sid
                actual = result['reported_cost_usd']
                charged = reserve if actual is None else Decimal(actual)
                ledger['sessions'][sid] = {'provider': provider, 'status': 'terminal',
                    'result_sha256': digest(encoded(result)), 'session_status': result['status'],
                    'charged_or_reserved_usd': str(charged), 'cost_uncertain': actual is None}
                if result['status'] in HALT or actual is None:
                    ledger['halt_reason'] = result['status']
                if total() > Decimal(limits['run_cost_cap_usd']) or total(provider) > Decimal(limits['provider_cost_caps_usd'][provider]):
                    ledger['halt_reason'] = 'reported_cost_exceeds_budget'
                _atomic(ledgerpath, encoded(ledger))
            return result

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
        # Checkpoint every twelve scheduled sessions. Already terminal records are verified.
        for start in range(0, len(plan['sessions']), 12):
            results.extend(pool.map(one, plan['sessions'][start:start + 12]))
            checkpoint = {'scheduled_through': min(start + 12, len(ids)),
                          'terminal': sum(r is not None for r in results),
                          'halt_reason': ledger['halt_reason'],
                          'ledger_sha256': digest(ledgerpath.read_bytes()),
                          'simulated_charged_or_reserved_usd': str(total()), 'live_execution': False}
            _atomic(output / 'checkpoints' / f'{start // 12 + 1:03d}.json', encoded(checkpoint))
    summary = {'planned': len(ids), 'terminal': sum(r is not None for r in results),
               'not_started': sum(r is None for r in results), 'halt_reason': ledger['halt_reason'],
               'simulated_charged_or_reserved_usd': str(total()), 'real_spend_usd': '0',
               'states': {s: sum(r is not None and r['status'] == s for r in results)
                          for s in sorted({r['status'] for r in results if r is not None})}}
    _atomic(output / 'summary.json', encoded(summary))
    return summary


def parsed_records(session):
    parsed = []
    for line in (session / 'events.jsonl').read_text().splitlines():
        event = json.loads(line)
        if event['event'] == 'response_parsed':
            parsed.extend(json.loads((session / ref['path']).read_text()) for ref in event['files'])
    return parsed


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    p = json.loads((root / 'runs/bounded_sessions_v1/plan.json').read_text())
    print(json.dumps(run_batch(p, root / 'runs/bounded_sessions_v1/mock_all_432')))
