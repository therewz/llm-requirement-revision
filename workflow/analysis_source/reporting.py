"""Join preserved planned calibration and uniform exact checks for author use.

This script performs no new inference. It verifies the source manifests and
joins already computed results by their full analysis identities.
"""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'reports/statistical_analysis_v3'
EXACT = BASE / 'verification/all_views_exact_v1'
OUT = BASE / 'reporting'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def same_number(a, b):
    return (a == b == '') or (a != '' and b != '' and abs(float(a) - float(b)) < 1e-12)


def main():
    summary = json.loads((EXACT / 'SUMMARY.json').read_text())
    for name, expected in summary['outputs'].items():
        assert digest(EXACT / name) == expected, name
    manifests = [('paired/manifest.json', 'outputs'), ('groups/analysis_manifest.json', None)]
    inputs = {}
    for name, field in manifests:
        path = BASE / name
        data = json.loads(path.read_text())
        inputs[str(path.relative_to(ROOT))] = digest(path)
        if field:
            for filename, expected in data[field].items():
                assert digest(path.parent / filename) == expected, filename
        else:
            assert digest(path.parent / 'group_tests.csv') == data['output_sha256']
    specs = [
        ('paired', 'paired/paired_wilcoxon.csv', 'paired_all_views_exact.csv', 'p',
         ('view', 'task', 'provider', 'family', 'metric', 'contrast')),
        ('mean_permutation', 'paired/paired_mean_permutation.csv', 'meanflip_all_views_exact.csv', 'p',
         ('view', 'task', 'provider', 'family', 'metric', 'contrast')),
        ('friedman', 'paired/friedman.csv', 'friedman_all_views_exact.csv', 'p',
         ('view', 'task', 'provider', 'family', 'metric')),
        ('groups', 'groups/group_tests.csv', 'group_all_views_exact.csv', 'p_raw',
         ('view', 'task', 'provider', 'context', 'metric', 'group_left', 'group_right')),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for name, original_name, exact_name, pfield, keys in specs:
        source_path, exact_path = BASE / original_name, EXACT / exact_name
        original, exact = read(source_path), read(exact_path)
        identity = lambda row: tuple(row[k] for k in keys)
        index = {identity(row): row for row in exact}
        assert len(index) == len(exact) == len(original), name
        assert {identity(row) for row in original} == set(index), name
        records = []
        for row in original:
            precise = index[identity(row)]
            assert row['status'] == precise['status'], identity(row)
            assert same_number(row[pfield], precise['primary_raw_p'])
            assert same_number(row['p_holm'], precise['primary_holm_p'])
            item = {('planned_raw_p' if k == pfield else 'planned_holm_p' if k == 'p_holm' else k): v
                    for k, v in row.items()}
            for key in ('exact_raw_p', 'exact_holm_p', 'exact_method', 'exact_extreme', 'exact_assignments',
                        'primary_threshold', 'exact_threshold'):
                item[key] = precise[key]
            item['planned_source'] = str(source_path.relative_to(ROOT))
            item['exact_source'] = str(exact_path.relative_to(ROOT))
            records.append(item)
        path = OUT / (name + '_all_views.csv')
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
        inputs[str(source_path.relative_to(ROOT))] = digest(source_path)
        inputs[str(exact_path.relative_to(ROOT))] = digest(exact_path)
        outputs[path.name] = {'rows': len(records), 'sha256': digest(path),
                              'views': dict(sorted(Counter(r['view'] for r in records).items()))}
    inputs[str((EXACT / 'SUMMARY.json').relative_to(ROOT))] = digest(EXACT / 'SUMMARY.json')
    result = {'status': 'PASS', 'purpose': 'Full-key join for reporting; no new tests or outcome changes',
              'code_sha256': digest(Path(__file__)), 'inputs': inputs, 'outputs': outputs,
              'exact_calibration_for_author_discussion': True,
              'planned_outputs_preserved': True}
    (OUT / 'MANIFEST.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v['rows'] for k, v in outputs.items()}, indent=2))


if __name__ == '__main__':
    main()
