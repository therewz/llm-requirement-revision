"""Join frozen baseline evidence and prospective input flags; never select a cohort."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
run = ROOT / 'runs/matched_inputs_v1'
audit = ROOT / 'reports/matched_inputs_v1/specification_audit'
manifest = json.loads((run / 'build_manifest.json').read_text())
coverage = {r['participant_id']: r for r in json.loads((audit / 'coverage.json').read_text())}
summary = json.loads((audit / 'summary.json').read_text())
baseline = list(csv.DictReader((ROOT / 'runs/withdrawal_keys_v1/derived/programs.csv').open()))
assert len(baseline) == len(coverage) == len(manifest['records']) == 72
assert {r['participant_id'] for r in baseline} == set(coverage) == {r['participant_id'] for r in manifest['records']}
rows = []
for base in sorted(baseline, key=lambda r: r['participant_id']):
    sid = base['participant_id']
    c = coverage[sid]
    assert (base['task'], base['group']) == (c['task'], c['group'])
    rows.append({**base, 'prepared_conditions': 'RR;SA;EW',
                 'specification_flag_ids': ';'.join(c['flag_ids']),
                 'direct_key_compatibility_issue': sid in summary['direct_fixed_target_key_incompatibility_ids'],
                 'conditional_date_issue': sid in summary['conditional_fixed_date_conflict_ids'],
                 'broader_packet_decision_flag': sid in summary['packet_decision_ids'],
                 'exclusion_applied_by_this_preparation': False,
                 'execution_mode': 'undecided', 'live_enabled': False})
with (run / 'PACKET_STATUS.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print('72 records joined; no exclusions or live enablement')
