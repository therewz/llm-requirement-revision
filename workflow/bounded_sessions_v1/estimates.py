"""Planning arithmetic, never measured model latency or token estimates."""
import json
from pathlib import Path
from decimal import Decimal
from adapters import OpenAIAdapter, ClaudeAdapter

ROOT = Path(__file__).resolve().parents[2]
plan = json.loads((ROOT / 'runs/bounded_sessions_v1/plan.json').read_text())
sizes = []
for p in plan['sessions']:
    adapter = OpenAIAdapter() if p['provider'] == 'openai' else ClaudeAdapter()
    prompt = (Path(p['packet_dir']) / 'prompt_draft.md').read_text()
    request = adapter.encode(p['model'], [{'role': 'system', 'content': p['operational_instruction']},
                                         {'role': 'user', 'content': prompt}], p['tools'], p['limits']['max_output_tokens'], p['settings'])
    size = len(json.dumps(request, ensure_ascii=False, separators=(',', ':')).encode())
    assert size <= p['limits']['max_request_bytes']
    sizes.append(size)
rows = []
for name, inp, out in [('short_session', 8000, 2000), ('moderate_session', 24000, 6000), ('long_session', 80000, 12000)]:
    per = (Decimal(inp) * 2 + Decimal(out) * 10) / 1000000
    rows.append({'scenario': name, 'cumulative_billed_input_tokens_per_session': inp,
                 'cumulative_output_tokens_per_session_including_thinking': out,
                 'session_cost_usd': str(per), 'all_432_cost_usd': str(per * 432),
                 'each_216_model_cost_usd': str(per * 216)})
obj = {'evidence_class': 'ILLUSTRATIVE_PLANNING_ARITHMETIC_NOT_MEASURED_MODEL_USAGE',
       'sessions': len(plan['sessions']), 'models': 2, 'repeat_count': 1,
       'initial_request_bytes': {'min': min(sizes), 'max': max(sizes), 'mean': sum(sizes)/len(sizes)},
       'cost_scenarios': rows, 'pricing': {'input_per_million_usd': 2, 'output_per_million_usd': 10,
                                        'discounts': 'None assumed; no cache or batch discount'},
       'timing_scenarios': [{'average_session_minutes': m, 'concurrency': 4, 'hours_before_overhead': 432*m/4/60}
                            for m in (3, 5, 8, 10)],
       'limits': ['Input totals count resubmitted history across all turns, not just initial context.',
                  'No measured model latency, billed token counts, account access or rate limits available.',
                  'Retries, provider queues, evaluation and review checkpoints add time/cost.',
                  'Proposed USD100 run/USD50 per-provider ceilings may stop the longer scenario before completion.',
                  'Mock token fields and simulated USD0.9072 are fixture values, not a forecast or real spend.',
                  'Software reservations are estimates; future provider-side spending controls remain separate.']}
path = ROOT / 'reports/bounded_sessions_v1/ESTIMATES.json'
path.parent.mkdir(exist_ok=True, parents=True)
path.write_text(json.dumps(obj, indent=2)+'\n')
print(json.dumps(obj, indent=2))
