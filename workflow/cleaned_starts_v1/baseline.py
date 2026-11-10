"""Run the existing isolated evaluator on the versioned cleaned starting files."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import csv
import importlib.util
import json
from pathlib import Path
import sys

from .prepare import ROOT, RUN, ORIGINAL, build, digest, encode, read_checked, write_same

FROZEN_EVALUATOR = ROOT / 'code/bounded_sessions_v1/evaluate.py'
spec = importlib.util.spec_from_file_location('cleaned_baseline_evaluator', FROZEN_EVALUATOR)
evaluator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluator)
sys.path.insert(0, str(ROOT / 'code/withdrawal_keys_v1'))
from task_a import classify as classify_a
from summarize import score_b

KEYS = {t: json.loads((ORIGINAL / f'answer_key_{t}.json').read_bytes()) for t in 'AB'}
BY_ID = {t: {row['case_id']: row for row in key['cases']} for t, key in KEYS.items()}


def linked(case):
    return case.get('control_ids', case.get('linked_controls', []))


def classify(task, case, observations):
    if task == 'A':
        return classify_a(case, observations)
    return score_b(case, observations, BY_ID['B'])


def canonical_cases(task):
    return [case for case in KEYS[task]['cases'] if (
        (case['role'], case.get('profile')) == ('target', 'iso_primary') if task == 'A'
        else case['role'] == 'primary_target'
    )]


def check_parity(program, old, fresh):
    sid, task = program['participant_id'], program['task']
    prior, current = old['targets']['cases'], fresh['targets']['cases']
    if set(prior) != set(current):
        raise ValueError(f'Missing probe records for {sid}')
    if not program['changed']:
        if prior != current:
            raise ValueError(f'Unchanged source produced different target/control observations: {sid}')
        return {'unchanged_probes': len(prior)}
    if task == 'A':
        native = program['original_profile']
        unchanged = [case for case in KEYS['A']['cases'] if case['profile'].startswith('weekday_')]
        for case in unchanged:
            cid = case['case_id']
            if current[cid] != prior[cid]:
                raise ValueError(f'Native behavior changed: {sid}/{cid}')
        canonical = [case for case in KEYS['A']['cases'] if case['profile'] == 'iso_primary']
        for case in canonical:
            cid = case['case_id']
            original_id = f"{native}:{cid.replace('A-F4', 'A-F1')}"
            if current[cid] != prior[original_id]:
                raise ValueError(f'ISO probe differs from its original native equivalent: {sid}/{cid}')
        return {'unchanged_native_probes': len(unchanged), 'iso_to_native_comparisons': len(canonical)}
    for cid, original in prior.items():
        items = original['items']
        if (original['kind'], original['type'], original['length'], len(items), items[1]['type']) != (
            'ret', 'tuple', 2, 2, 'dict'
        ) or items[0]['type'] != 'bool' or type(items[0]['value']) is not bool:
            raise ValueError(f'Original Boolean field missing: {sid}/{cid}')
        if current[cid] != {'kind': 'ret', **items[0]}:
            raise ValueError(f'Allocation decision changed: {sid}/{cid}')
    return {'boolean_decision_comparisons': len(prior)}


def original_case_ids(program, eligible):
    profile = program['original_profile']
    return {
        cid: f"{profile}:{cid.replace('A-F4', 'A-F1')}" if profile.startswith('weekday_') else cid
        for cid in eligible
    }


def summarize(prepared):
    with (ORIGINAL / 'derived/target_cases.csv').open() as stream:
        p1_rows = {(r['participant_id'], r['case_id']): r for r in csv.DictReader(stream)}
    results = []
    for p in prepared['programs']:
        sid, task = p['participant_id'], p['task']
        path = RUN / 'baseline' / f'{sid}.json'
        data = path.read_bytes()
        record = json.loads(data)
        if (record['source_sha256'] != p['cleaned_source']['sha256']
                or record['participant_id'] != sid or record['task'] != task or record['group'] != p['group']
                or record['freeze_sha256'] != evaluator.FREEZE_SHA256
                or not record['evaluation_complete']):
            raise ValueError(f'Incomplete or mismatched cleaned baseline: {sid}')
        old = json.loads((ORIGINAL / 'raw' / f'{sid}_P2.json').read_bytes())
        parity = check_parity(p, old, record)
        cases = record['targets']['cases']
        eligible = [case['case_id'] for case in canonical_cases(task)
                    if classify(task, case, cases)['status'] == 'RETAINED']
        controls = sorted({c for cid in eligible for c in linked(BY_ID[task][cid])})
        original_ids = original_case_ids(p, eligible)
        phase_one = {}
        for cid, original_id in original_ids.items():
            row = p1_rows[sid, original_id]
            if sid == 'S0027':
                observation = json.loads((ORIGINAL / 'raw/S0027_P1.json').read_bytes())['targets']['cases'][original_id]
                phase_one[cid] = {'restored': row['p1_match_for_tuple_diagnostic'] == 'True',
                                  'original_return_format': observation.get('type'),
                                  'original_return_format_valid': observation.get('type') == 'bool'}
            else:
                phase_one[cid] = {'restored': row['p1_target_predicate_match'] == 'True',
                                  'original_return_format_valid': row['p1_return_format_valid'] == 'True'}
        passed = lambda suite: {k for k, v in suite['results'].items() if v[0] == 'passed'}
        before = passed(old['core28'])
        after = passed(record['core28'])
        results.append({
            'participant_id': sid, 'task': task, 'group': p['group'], 'source_changed': p['changed'],
            'starting_source_sha256': record['source_sha256'],
            'baseline_sha256': digest(data), 'baseline_path': str(path.relative_to(ROOT)),
            'fixed_profile': p['target_profile'], 'eligible_case_ids': eligible,
            'required_linked_controls_after_edit': controls,
            'original_phase_i_case_mapping': original_ids, 'original_phase_i_predicates': phase_one,
            'core_baseline_pass_ids': sorted(after),
            'old_core_pass_count': len(before), 'cleaned_core_pass_count': len(after),
            'core_pass_gains': sorted(after - before), 'core_pass_losses': sorted(before - after),
            'parity_checks': parity,
        })
    qualifies = [row for row in results if row['eligible_case_ids']]
    unavailable = sorted(row['participant_id'] for row in results if not row['eligible_case_ids'])
    if unavailable != ['S0041', 'S0050', 'S0052']:
        raise ValueError('Unexpected change in the rule-bearing starting cohort')
    if any(len(r['eligible_case_ids']) != (7 if r['task'] == 'A' else 4) for r in qualifies):
        raise ValueError('Incomplete canonical target and control coverage')
    summary = {
        'evidence_class': 'OFFLINE_CLEANED_START_BASELINE_NOT_MODEL_OUTPUT',
        'live_enabled': False, 'model_calls': 0, 'programs': len(results),
        'normalized_sources': sum(row['source_changed'] for row in results),
        'eligible_programs': len(qualifies),
        'eligible_programs_by_task': dict(Counter(r['task'] for r in qualifies)),
        'eligible_dated_or_boolean_targets_by_task': {
            t: sum(len(r['eligible_case_ids']) for r in qualifies if r['task'] == t) for t in 'AB'
        },
        'eligible_programs_by_group': dict(Counter(r['task'] + '_' + r['group'] for r in qualifies)),
        'no_demonstrated_restriction': unavailable,
        'original_core_passes': sum(r['old_core_pass_count'] for r in results),
        'cleaned_core_passes': sum(r['cleaned_core_pass_count'] for r in results),
        'core_pass_gains': sum(len(r['core_pass_gains']) for r in results),
        'core_pass_losses': sum(len(r['core_pass_losses']) for r in results),
        'phase_i_predicate_programs': sum(bool(r['original_phase_i_predicates']) and
                                         all(x['restored'] for x in r['original_phase_i_predicates'].values()) for r in results),
        'records': results,
    }
    write_same(RUN / 'baseline_manifest.json', encode(summary))
    return summary


def baseline():
    prepared = build()
    evaluator.runtime.isolation_preflight(RUN)

    def one(p):
        sid = p['participant_id']
        destination = RUN / 'baseline' / f'{sid}.json'
        if destination.exists():
            return
        source = p['cleaned_source']
        data = read_checked(ROOT / source['path'], source['sha256'])
        identity = {key: p[key] for key in ('participant_id', 'task', 'group')}
        started = datetime.now(timezone.utc).isoformat()
        record = evaluator.evaluate_source_bytes(data, p['task'], metadata=identity)
        record.update(evidence_class='FRESH_ISOLATED_CLEANED_START_NOT_MODEL_OUTPUT',
                      started_at_utc=started, finished_at_utc=datetime.now(timezone.utc).isoformat(),
                      effective_timezone=evaluator.runtime.ENV['TZ'])
        write_same(destination, encode(record))
    with ThreadPoolExecutor(max_workers=4) as pool:
        for count, _ in enumerate(pool.map(one, prepared['programs']), 1):
            if count % 12 == 0:
                print(f'{count}/72 baseline records available', flush=True)
    summary = summarize(prepared)
    print(json.dumps({k: v for k, v in summary.items() if k != 'records'}, indent=2), flush=True)


if __name__ == '__main__':
    baseline()
