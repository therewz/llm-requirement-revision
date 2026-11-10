"""Build a deterministic offline plan from the accepted matched input package."""
import hashlib
import itertools
import json
from pathlib import Path
from adapters import OpenAIAdapter, ClaudeAdapter
from runtime import TOOL_SCHEMAS

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'runs/bounded_sessions_v1'
WRAPPER = ('Work on src/solution.py using the provided tools. Read it before editing. '
           'Keep its public function names and call signatures. You may create and run Python checks '
           'under checks/; no tests are supplied. Python runs are read-only; use write_file for edits. '
           'Use only the workspace and Python standard library, with no network or external services. '
           'Finish with a brief summary. The final src/solution.py is your submitted implementation.')
LIMITS = {'max_model_turns': 8, 'max_tool_calls': 12, 'session_seconds': 600,
          'max_output_tokens': 8192, 'max_request_bytes': 131072,
          'max_429_retries': 1, 'session_cost_cap_usd': '1.00',
          'python_timeout_seconds': 10, 'file_bytes': 131072,
          'workspace_bytes': 1048576, 'workspace_files': 32, 'output_bytes': 16384, 'memory_mb': 256}
MODELS = {
    'openai': {'model': 'gpt-6.1-sol', 'settings': {'reasoning': {'effort': 'high'}, 'service_tier': 'default'},
               'api_version': OpenAIAdapter.api_version},
    'anthropic': {'model': 'claude-sonnet-5-5', 'settings': {'thinking': {'type': 'adaptive'}, 'output_config': {'effort': 'high'}},
                  'api_version': ClaudeAdapter.api_version}}
PRICES = {'input_per_million': '2', 'output_per_million': '10',
          'cache_read_per_million': '0.10', 'cache_write_per_million': '2.50'}


def sha(data): return hashlib.sha256(data).hexdigest()


def save(path, obj):
    data = (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data: raise ValueError('Refusing changed plan: ' + str(path))
    path.write_bytes(data)


def build():
    source = ROOT / 'runs/matched_inputs_v2/build_manifest.json'
    m = json.loads(source.read_text())
    permutations = list(itertools.permutations(['RR', 'SA', 'EW']))
    sessions = []
    for i, row in enumerate(sorted(m['records'], key=lambda r: (r['task'], r['group'], r['participant_id']))):
        for ci, condition in enumerate(permutations[i % 6]):
            # Use the condition's fixed identity, not its permuted position: the
            # latter accidentally correlates model order with arm permutations.
            providers = ['openai', 'anthropic'] if (i + ['RR', 'SA', 'EW'].index(condition)) % 2 == 0 else ['anthropic', 'openai']
            rec = row['conditions'][condition]
            folder = ROOT / 'runs/matched_inputs_v2' / rec['path']
            for name, f in rec['files'].items(): assert sha((folder / name).read_bytes()) == f['sha256']
            for provider in providers:
                sessions.append({'session_id': f"{row['participant_id']}_{condition}_{provider}_r1",
                    'participant_id': row['participant_id'], 'task': row['task'], 'group': row['group'],
                    'condition': condition, 'provider': provider, 'repeat': 1, **MODELS[provider],
                    'packet_dir': str(folder), 'prompt_sha256': rec['files']['prompt_draft.md']['sha256'],
                    'source_sha256': rec['files']['workspace/src/solution.py']['sha256'],
                    'operational_instruction': WRAPPER, 'tools': TOOL_SCHEMAS,
                    'limits': LIMITS, 'pricing': PRICES,
                    'order': len(sessions), 'batch': len(sessions) // 12 + 1,
                    'settings_status': 'PROPOSED_OFFLINE_ONLY_NOT_LIVE_APPROVED'})
    assert len(sessions) == len({s['session_id'] for s in sessions}) == 432
    obj = {'status': 'OFFLINE_ONLY', 'live_enabled': False, 'approval_reference': None,
           'execution_mode': 'bounded_editing_session', 'mode_authorized_by_user': True,
           'repeat_count': 1, 'repeat_count_status': 'PLANNING_SCENARIO_NOT_FINAL_DESIGN',
           'provider_settings_status': 'CANDIDATE_CONFIG_NOT_ACCOUNT_TESTED',
           'pricing_source_date': '2026-11-05', 'parent_manifest_sha256': sha(source.read_bytes()),
           'scheduler': {'concurrency': 4, 'per_provider_concurrency': 2,
                         'run_cost_cap_usd': '100', 'provider_cost_caps_usd': {'openai': '50', 'anthropic': '50'},
                         'budget_status': 'SIMULATION_ONLY_NOT_SPENDING_AUTHORIZATION'},
           'sessions': sessions}
    save(RUN / 'plan.json', obj)
    print(json.dumps({'sessions': len(sessions), 'live_enabled': False}))
    return obj


if __name__ == '__main__': build()
