"""Labelled synthetic end-to-end exercises and authentic unchanged-source replay.

No generated model outputs and no fresh execution of participant source here.
"""
import copy
import json
from pathlib import Path
from adapters import OpenAIAdapter, ClaudeAdapter
from engine import MockTransport, run_session, verify_session, digest, encoded, _atomic
from runtime import WorkspaceTools
from evaluate import evaluate_session
from scoring import score_observations, score_saved_baseline_replay

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'runs/bounded_sessions_v1'
SYNTH = {
    'A': (b"def suggest_slots(events, meeting_duration, day):\n return ['09:00']\n",
          b"def suggest_slots(events, meeting_duration, day):\n return ['09:00','15:30','15:45','16:00','16:15']\n",
          "from solution import suggest_slots\nassert '16:00' in suggest_slots([],30,'Friday')\nprint('SELF_CHECK_OK')\n"),
    'B': (b"def is_allocation_feasible(resources,requests):\n return False\n",
          b"def is_allocation_feasible(resources,requests):\n return all(sum(r.get(k,0) for r in requests)<=v for k,v in resources.items())\n",
          "from solution import is_allocation_feasible\nassert is_allocation_feasible({'cpu':10},[{'cpu':10}]) is True\nprint('SELF_CHECK_OK')\n")}


def responses(p, revised, check):
    actions = [('read_file', {'path': 'src/solution.py'}),
               ('write_file', {'path': 'src/solution.py', 'content': revised.decode()}),
               ('write_file', {'path': 'checks/self_check.py', 'content': check}),
               ('run_python', {'path': 'checks/self_check.py'}), None]
    rows = []
    for i, action in enumerate(actions):
        rid = f"synthetic_{p['session_id']}_{i}"
        if p['provider'] == 'openai':
            content = [{'type': 'function_call', 'call_id': 'call_' + rid, 'name': action[0],
                        'arguments': json.dumps(action[1]), 'status': 'completed'}] if action else [
                       {'type': 'message', 'role': 'assistant', 'status': 'completed',
                        'content': [{'type': 'output_text', 'text': 'Synthetic fixture finished.'}]}]
            if action: content.insert(0, {'type': 'reasoning', 'id': 'rs_' + rid, 'summary': [], 'encrypted_content': 'opaque_fixture'})
            rows.append({'id': rid, 'model': p['model'], 'status': 'completed', 'output': content,
                         'usage': {'input_tokens': 100, 'output_tokens': 50, 'input_tokens_details': {'cached_tokens': 0}}})
        else:
            content = [{'type': 'tool_use', 'id': 'call_' + rid, 'name': action[0], 'input': action[1]}] if action else [
                       {'type': 'text', 'text': 'Synthetic fixture finished.'}]
            if action: content.insert(0, {'type': 'thinking', 'thinking': 'Synthetic fixture.', 'signature': 'opaque_fixture'})
            rows.append({'id': rid, 'model': p['model'], 'type': 'message', 'role': 'assistant', 'content': content,
                         'stop_reason': 'tool_use' if action else 'end_turn',
                         'usage': {'input_tokens': 100, 'output_tokens': 50,
                                   'cache_read_input_tokens': 0, 'cache_creation_input_tokens': 0}})
    return rows


def synthetic():
    plan = json.loads((RUN / 'plan.json').read_text())
    records = []
    for task in ('A', 'B'):
        for provider in ('openai', 'anthropic'):
            p = copy.deepcopy(next(p for p in plan['sessions'] if p['task'] == task and p['provider'] == provider and p['condition'] == 'EW'))
            p['session_id'] = 'synthetic_' + p['session_id']
            folder = RUN / 'synthetic_e2e' / p['session_id']
            packet = folder / 'packet'; (packet / 'workspace/src').mkdir(parents=True, exist_ok=True)
            source, revised, check = SYNTH[task]
            (packet / 'workspace/src/solution.py').write_bytes(source)
            (packet / 'prompt_draft.md').write_text('Labelled offline synthetic integration fixture; no study inference.\n')
            p.update({'packet_dir': str(packet), 'source_sha256': digest(source),
                      'prompt_sha256': digest((packet / 'prompt_draft.md').read_bytes()),
                      'evidence_class': 'SYNTHETIC_INTEGRATION_FIXTURE_NOT_EXPERIMENT'})
            adapter = OpenAIAdapter() if provider == 'openai' else ClaudeAdapter()
            session = folder / 'session'
            result = run_session(p, session, MockTransport(responses(p, revised, check)), adapter, WorkspaceTools)
            assert result['status'] == 'completed', result
            assert (session / 'final.py').read_bytes() == revised
            tool = json.loads((session / 'tools/0004.json').read_text())
            assert tool['status'] == 'ok' and 'SELF_CHECK_OK' in tool['stdout'], tool
            before = digest((session / 'events.jsonl').read_bytes())
            obs = evaluate_session(p, session, adapter)
            assert obs['evaluation_complete'], obs
            score = score_observations(p, result, obs)
            assert score['condition_success'] is True and score['withdrawal']['complete']
            assert digest((session / 'events.jsonl').read_bytes()) == before
            # Scores are implementation fixtures using fixed baseline dimensions, not model results.
            obs['evidence_class'] = score['evidence_class'] = 'SYNTHETIC_INTEGRATION_FIXTURE_NOT_EXPERIMENT'
            _atomic(folder / 'evaluation.json', encoded(obs)); _atomic(folder / 'score.json', encoded(score))
            records.append({'task': task, 'provider': provider, 'session_id': p['session_id'],
                            'status': 'PASS', 'actual_isolated_self_check': True,
                            'hidden_evaluation_complete': True, 'model_history_unchanged_by_evaluation': True})
    _atomic(RUN / 'synthetic_e2e/SUMMARY.json', encoded({'evidence_class': 'SYNTHETIC_ONLY', 'records': records}))
    print(json.dumps({'synthetic_e2e': len(records), 'status': 'PASS'}))


def score_replay():
    plan = json.loads((RUN / 'plan.json').read_text()); scores = []
    for p in plan['sessions']:
        adapter = OpenAIAdapter() if p['provider'] == 'openai' else ClaudeAdapter()
        session = RUN / 'mock_all_432/sessions' / p['session_id']
        result = verify_session(p, session, adapter)
        score = score_saved_baseline_replay(p, result)
        _atomic(RUN / 'unchanged_source_scores' / (p['session_id'] + '.json'), encoded(score))
        scores.append(score)
    summary = {'evidence_class': 'EXACT_HASH_BASELINE_REPLAY_NOT_NEW_MODEL_RESULTS', 'sessions': len(scores),
               'all_core_complete': all(s['core_preservation']['complete'] for s in scores),
               'core_loss_count': sum(s['core_preservation']['loss_count'] for s in scores),
               'source_evidence_reused': all(s['exact_hash_evidence_reused'] for s in scores),
               'by_condition': {c: {'sessions': sum(s['condition'] == c for s in scores),
                                    'eligible_targets': sum(s['withdrawal']['eligible_case_count'] for s in scores if s['condition'] == c),
                                    'met_condition_targets': sum(s['withdrawal']['success_count'] for s in scores if s['condition'] == c)}
                                for c in ('RR', 'SA', 'EW')}}
    assert summary['core_loss_count'] == 0 and summary['all_core_complete']
    _atomic(RUN / 'unchanged_source_scores/SUMMARY.json', encoded(summary)); print(json.dumps(summary))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['synthetic', 'replay'])
    {'synthetic': synthetic, 'replay': score_replay}[parser.parse_args().action]()
