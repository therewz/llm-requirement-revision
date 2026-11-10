"""Compare fresh separate-grader results with the frozen cleaned baseline."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from . import evaluate
from cleaned_starts_v1.prepare import RUN, ROOT, digest, encode, parent, read_checked, write_same

OUT = ROOT / 'runs/separated_grader_v1'


def pass_status(layer):
    return {key: value[0] for key, value in layer['results'].items()}


def parity(participants=None):
    parent()
    manifest_bytes = (RUN / 'baseline_manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    prep = json.loads((RUN / 'preparation.json').read_bytes())
    starts = {r['participant_id']: r['cleaned_source'] for r in prep['programs']}
    records = [r for r in manifest['records'] if participants is None or r['participant_id'] in participants]
    if not records or participants is not None and {r['participant_id'] for r in records} != participants:
        raise ValueError('Requested an unknown cleaned program')

    def one(row):
        sid = row['participant_id']
        source = starts[sid]
        data = read_checked(ROOT / source['path'], row['starting_source_sha256'])
        old = json.loads(read_checked(ROOT / row['baseline_path'], row['baseline_sha256']))
        fresh = evaluate.evaluate_source_bytes(
            data, row['task'], metadata={k: row[k] for k in ('participant_id', 'group')})
        if (not fresh['evaluation_complete'] or fresh['source_sha256'] != row['starting_source_sha256']
                or fresh['freeze_sha256'] != old['freeze_sha256']):
            raise ValueError(f'Incomplete or misbound separate evaluation for {sid}')
        changed_targets = sorted(k for k in old['targets']['cases']
                                 if fresh['targets']['cases'][k] != old['targets']['cases'][k])
        changed_suites = {}
        for layer in ('core28', 'supplied5'):
            if old[layer]['suite_sha256'] != fresh[layer]['suite_sha256']:
                raise ValueError(f'Suite bytes changed: {sid}/{layer}')
            before = pass_status(old[layer])
            after = pass_status(fresh[layer])
            if set(before) != set(after):
                raise ValueError(f'Suite collection changed: {sid}/{layer}')
            changed_suites[layer] = sorted(k for k in before if before[k] != after[k])
        return fresh, {
            'participant_id': sid,
            'source_sha256': fresh['source_sha256'],
            'target_and_control_observations': len(old['targets']['cases']),
            'core_cases': len(old['core28']['results']),
            'supplied_five_cases': len(old['supplied5']['results']),
            'core_passes': sum(v == 'passed' for v in pass_status(fresh['core28']).values()),
            'changed_targets': changed_targets, 'changed_suites': changed_suites,
        }

    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for fresh, summary in pool.map(one, records):
            results.append((fresh, summary))
            if len(results) % 12 == 0 or len(results) == len(records):
                print(f'{len(results)}/{len(records)} isolated parity programs checked', flush=True)
    rows = [row for _, row in results]
    report = {
        'evidence_class': 'FRESH_CLEANED_SOURCE_SEPARATED_GRADER_PARITY_NOT_MODEL_OUTPUT',
        'model_calls': 0,
        'cleaned_baseline_manifest_sha256': digest(manifest_bytes),
        'program_count': len(rows),
        **{field: sum(r[field] for r in rows) for field in (
            'target_and_control_observations', 'core_cases', 'supplied_five_cases', 'core_passes')},
        'exact_target_and_status_parity': all(not r['changed_targets'] and
                                              not any(r['changed_suites'].values()) for r in rows),
        'records': rows,
    }
    print(json.dumps({k: v for k, v in report.items() if k != 'records'}, indent=2), flush=True)
    if participants is None:
        # Only the full validation run populates the durable evidence.
        for fresh, summary in results:
            write_same(OUT / 'observations' / f"{summary['participant_id']}.json", encode(fresh))
        write_same(OUT / 'parity.json', encode(report))
    if not report['exact_target_and_status_parity']:
        for row in rows:
            if row['changed_targets'] or any(row['changed_suites'].values()):
                print(row, flush=True)
        raise ValueError('Separate grader differs on the cleaned reference set')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--participants', nargs='+')
    args = parser.parse_args()
    parity(set(args.participants) if args.participants else None)
