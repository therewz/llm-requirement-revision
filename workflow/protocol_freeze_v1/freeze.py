"""Build/verify a prospective protocol freeze; never dispatch or access credentials.

This artifact does not unlock the separately frozen bounded-session engine.
The current batch runner also lacks the required opening-batch pause, so this
configuration deliberately is not a runnable approval record.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = 'planning/BOUNDED_SESSION_PROTOCOL_2026-11-05_v2.md'
PLAN = 'runs/bounded_sessions_v1/plan.json'
CONFIG = 'runs/protocol_freeze_v1/selected_config.json'
LIMITS = {
    'file_bytes': 131072, 'max_429_retries': 1, 'max_model_turns': 8,
    'max_output_tokens': 8192, 'max_request_bytes': 131072,
    'max_tool_calls': 12, 'memory_mb': 256, 'output_bytes': 16384,
    'python_timeout_seconds': 10, 'session_cost_cap_usd': '1.00',
    'session_seconds': 600, 'workspace_bytes': 1048576, 'workspace_files': 32,
}
MODELS = {
    'openai': {'model': 'gpt-6.1-sol', 'settings': {
        'reasoning': {'effort': 'high'}, 'service_tier': 'default'}},
    'anthropic': {'model': 'claude-sonnet-5-5', 'settings': {
        'thinking': {'type': 'adaptive'}, 'output_config': {'effort': 'high'}}},
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(obj):
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode()


def check_plan(plan):
    """Reject a changed study design rather than inherit arbitrary plan values."""
    if plan.get('live_enabled') is not False or plan.get('approval_reference') is not None:
        raise ValueError('Parent plan is not offline')
    if plan.get('repeat_count') != 1:
        raise ValueError('Repeat count changed')
    sessions = plan.get('sessions', [])
    if len(sessions) != 432 or len({s['session_id'] for s in sessions}) != 432:
        raise ValueError('Expected exactly 432 unique sessions')
    cells = Counter()
    pairs = {}
    for i, s in enumerate(sessions):
        if s['order'] != i or s['batch'] != i // 12 + 1 or s['repeat'] != 1:
            raise ValueError('Order, batch or repetition changed')
        if s['condition'] not in ('RR', 'SA', 'EW') or s['task'] not in ('A', 'B') or s['group'] not in ('G1', 'G2', 'G3'):
            raise ValueError('Unrecognized design cell')
        if s['provider'] not in MODELS or any(s[k] != v for k, v in MODELS[s['provider']].items()):
            raise ValueError('Model or settings changed')
        if s['limits'] != LIMITS:
            raise ValueError('Session limits changed')
        cells[(s['task'], s['group'], s['condition'], s['provider'])] += 1
        pairs.setdefault((s['participant_id'], s['condition']), []).append(s)
    if len(cells) != 36 or set(cells.values()) != {12} or len(pairs) != 216:
        raise ValueError('Incomplete task/group/condition/model crossing')
    first = Counter()
    for pair in pairs.values():
        if len(pair) != 2 or {s['provider'] for s in pair} != set(MODELS):
            raise ValueError('Missing model pair')
        a, b = pair
        if (a['task'], a['group'], a['source_sha256'], a['prompt_sha256']) != (b['task'], b['group'], b['source_sha256'], b['prompt_sha256']):
            raise ValueError('Unmatched model inputs')
        first[(a['task'], a['group'], a['condition'], a['provider'])] += 1
    if len(first) != 36 or set(first.values()) != {6}:
        raise ValueError('First-provider order is not balanced')
    scheduler = plan['scheduler']
    if (scheduler['concurrency'], scheduler['per_provider_concurrency'], scheduler['run_cost_cap_usd'], scheduler['provider_cost_caps_usd']) != (4, 2, '100', {'openai': '50', 'anthropic': '50'}):
        raise ValueError('Scheduler or budget changed')


def bound_files(root):
    """Directly bind all inputs and saved baseline evidence, not only manifests."""
    singles = [POLICY, PLAN, 'runs/matched_inputs_v2/build_manifest.json',
               'runs/withdrawal_keys_v1/inventory.json',
               'runs/withdrawal_keys_v1/freeze.json',
               'runs/withdrawal_keys_v1/answer_key_A.json',
               'runs/withdrawal_keys_v1/answer_key_B.json',
               'runs/withdrawal_keys_v1/source_hashes.json',
               'runs/withdrawal_keys_v1/suite_case_ids.json',
               'reports/matched_inputs_v1/specification_audit/flags.json',
               'reports/matched_inputs_v1/specification_audit/coverage.json',
               'reports/matched_inputs_v1/specification_audit/target_comparisons.json',
               'reports/withdrawal_keys_v1/ARTIFACT_HASHES.json',
               'reports/matched_inputs_v1/ARTIFACT_HASHES.json',
               'reports/matched_inputs_v2/ARTIFACT_HASHES.json',
               'reports/bounded_sessions_v1/PROVIDER_SOURCES.md']
    paths = {root / rel for rel in singles}
    for rel in ['code/bounded_sessions_v1', 'code/withdrawal_keys_v1', 'code/protocol_freeze_v1',
                'runs/matched_inputs_v2/packets',
                'runs/withdrawal_keys_v1/input_snapshot',
                'runs/withdrawal_keys_v1/raw', 'runs/withdrawal_keys_v1/derived']:
        base = root / rel
        if not base.is_dir():
            raise ValueError('Missing bound directory: ' + rel)
        paths.update(p for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    result = []
    for p in sorted(paths):
        if p.is_symlink() or not p.is_file():
            raise ValueError('Missing/nonregular bound file: ' + str(p))
        data = p.read_bytes()
        result.append({'path': str(p.relative_to(root)), 'bytes': len(data), 'sha256': digest(data)})
    return result


def expected_config(root=ROOT):
    plan = json.loads((root / PLAN).read_text())
    check_plan(plan)
    manifest = root / 'runs/matched_inputs_v2/build_manifest.json'
    if digest(manifest.read_bytes()) != plan['parent_manifest_sha256']:
        raise ValueError('Matched-input manifest differs from parent plan')
    for session in plan['sessions']:
        folder = Path(session['packet_dir'])
        if not folder.is_relative_to(root / 'runs/matched_inputs_v2/packets'):
            raise ValueError('Packet outside the frozen input tree')
        for rel, field in [('prompt_draft.md', 'prompt_sha256'),
                           ('workspace/src/solution.py', 'source_sha256')]:
            if digest((folder / rel).read_bytes()) != session[field]:
                raise ValueError('Packet content differs from parent session')
    bindings = bound_files(root)
    selected = deepcopy(plan['sessions'])
    for session in selected:
        session['settings_status'] = 'SELECTED_PROTOCOL_OFFLINE_NO_LIVE_AUTHORIZATION'
    return {
        'schema_version': 1,
        'status': 'PROTOCOL_SELECTED_OFFLINE_NOT_EXECUTABLE',
        'live_enabled': False,
        'approval_reference': None,
        'spending_authorized': False,
        'scientific_repeat_count': 1,
        'study_design': {'participants': 72, 'conditions': ['RR', 'SA', 'EW'],
                         'providers': ['openai', 'anthropic'], 'sessions': 432},
        'model_identity_policy': 'EXACT_REQUESTED_ID_ONLY_NO_SILENT_SUBSTITUTION',
        'models': MODELS,
        'scheduler': {'concurrency': 4, 'per_provider_concurrency': 2,
                      'run_cost_cap_usd': '100',
                      'provider_cost_caps_usd': {'openai': '50', 'anthropic': '50'},
                      'budget_status': 'SELECTED_CEILING_NOT_PERMISSION_TO_SPEND'},
        'opening_batch': {
            'session_ids': [s['session_id'] for s in selected[:12]],
            'mandatory_pause_after': 12,
            'resume_requires': 'Recorded coordinator operational check and existing explicit run authorization',
            'pool_with_main_run_only_if': 'No protocol, prompt, model, settings, limits or scoring change',
            'current_runner_enforces_pause': False,
            'coverage': 'First 12 deterministic sessions are Task A only; technical acceptance, not a representative scientific sample',
        },
        'retry_policy': {'known_429_retries': 1, 'ambiguous_delivery_automatic_retries': 0,
                         'outcome_dependent_reruns': False},
        'live_readiness_requirements': [
            'Select and validate execution host',
            'Bind locked HTTP transport to engine with saved evidence and remaining deadline',
            'Enforce opening-batch pause before dispatch beyond first 12',
            'Record evaluation start/end UTC and effective timezone in the live evidence envelope',
            'Obtain explicit run-specific authorization and provide owner credentials',
            'Verify real provider acceptance and reconcile usage/identity in authorized opening batch',
        ],
        'binding_policy': 'Every bound byte must match; changes require a new version before outputs',
        'bindings': bindings,
        'bindings_sha256': digest(encode(bindings)),
        'parent_plan_sha256': digest((root / PLAN).read_bytes()),
        'protocol': {'path': POLICY, 'sha256': digest((root / POLICY).read_bytes())},
        'sessions': selected,
    }


def validate(config, root=ROOT):
    """Exact reconstruction catches changed controls, reordered sessions and inputs."""
    expected = expected_config(root)
    if config != expected:
        raise ValueError('Selected configuration or a bound artifact changed; create a new reviewed version')
    return {'status': 'PASS_OFFLINE_FREEZE_ONLY', 'bound_files': len(config['bindings']),
            'sessions': len(config['sessions']), 'live_enabled': False,
            'opening_pause_implemented': False, 'provider_access_tested': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['build', 'validate'])
    args = parser.parse_args()
    path = ROOT / CONFIG
    if args.mode == 'build':
        obj = expected_config()
        data = encode(obj)
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Refusing to overwrite changed frozen configuration')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    result = validate(json.loads(path.read_text()))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
