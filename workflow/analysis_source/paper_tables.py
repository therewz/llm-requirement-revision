"""Extract current author review tables from verified saved outputs; no inference."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/results_readiness_v1/tables'
VIEWS = {'primary69__main', 'alternative62__main'}
INPUTS = {}

def read(rel):
    p = ROOT / rel
    INPUTS[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    with p.open(newline='') as stream:
        return list(csv.DictReader(stream))

def save(name, rows, cols):
    with (OUT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=cols)
        writer.writeheader()
        writer.writerows({k: r[k] for k in cols} for r in rows)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    arm = [r for r in read('reports/full_analysis_v2_prelim/tables/arm_summary.csv') if r['view'] in VIEWS]
    assert len(arm) == 24
    for r in arm:
        assert int(r['missing']) == 0
        assert sum(int(r[c + '_count']) for c in ['RESTORED', 'RETAINED', 'PARTIAL', 'OTHER_FAILURE', 'INDETERMINATE']) == int(r['target_cases_observed'])
        assert sum(int(r[c + '_count']) for c in ['PP', 'PF', 'FP', 'FF']) == 28 * int(r['evaluated'])
    common = ['view', 'task', 'provider', 'condition', 'programs', 'evaluated', 'missing']
    save('RQ1_targets_and_controls.csv', arm, common + ['target_cases_planned', 'target_cases_observed',
         'RESTORED_count', 'RETAINED_count', 'PARTIAL_count', 'OTHER_FAILURE_count', 'INDETERMINATE_count',
         'all_target_success_count', 'strict_target_success_count', 'linked_controls_bad', 'linked_controls_unknown',
         'restoration_rate_mean', 'residue_rate_mean', 'persistence_rate_mean', 'combined_success_count'])
    save('RQ2_core_preservation.csv', arm, common + ['core_opportunities', 'core_losses', 'core_gains',
         'core_loss_rate_mean', 'core_loss_rate_median', 'core_loss_count_mean', 'any_core_loss_count',
         'core_absolute_passes_mean', 'PP_count', 'PF_count', 'FP_count', 'FF_count', 'pooled_core_loss_rate'])
    for name in ['paired_all_views', 'mean_permutation_all_views', 'friedman_all_views', 'groups_all_views']:
        rows = [r for r in read('reports/statistical_analysis_v3/reporting/' + name + '.csv') if r['view'] in VIEWS]
        cols = list(rows[0])
        save(name.replace('_all_views', '_main_and_alternative') + '.csv', rows, cols)
    base = [r for r in read('reports/full_analysis_v2_prelim/tables/baseline_groups.csv') if r['view'] in VIEWS]
    save('RQ4_group_baselines.csv', base, list(base[0]))
    groups = [r for r in read('reports/full_analysis_v2_prelim/tables/group_summary.csv') if r['view'] in VIEWS]
    save('RQ4_group_descriptives.csv', groups, common + ['group', 'target_cases_observed', 'all_target_success_count',
         'strict_target_success_count', 'residue_rate_mean', 'core_loss_rate_mean', 'core_loss_rate_median',
         'core_opportunities', 'core_losses', 'core_gains', 'any_core_loss_count'])
    cohorts = [r for r in read('reports/full_analysis_v2_prelim/tables/cohorts.csv') if r['view'] in VIEWS]
    save('cohorts.csv', cohorts, list(cohorts[0]))
    # Supplementary angles stay available without treating cases as independent observations.
    for name in ['original_five_diagnostics', 'residue_attribution_bounds', 'missingness_bounds']:
        rows = [r for r in read('reports/full_analysis_v2_prelim/tables/' + name + '.csv') if r['view'] in VIEWS]
        save(name + '.csv', rows, list(rows[0]))
    counts = {}
    for path in sorted(OUT.glob('*.csv')):
        rows = list(csv.DictReader(path.open()))
        counts[path.name] = {'rows': len(rows), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    result = {'method': 'Exact row/column selection from verified source outputs; no new tests or transformations.',
              'views': sorted(VIEWS), 'input_sha256': INPUTS, 'outputs': counts,
              'units': 'Programs are inferential units. Category totals are case-runs. Mean core loss rates weight programs equally.',
              'calibration': 'Both planned and exact p-values retained. Exact is the recommended consistent reporting choice.',
              'scope': 'New expanded-conflict sensitivities are separate; these extracts preserve original main69 and alternative62.'}
    (OUT.parent / 'TABLES_MANIFEST.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v['rows'] for k, v in counts.items()}, indent=2))

if __name__ == '__main__':
    main()
