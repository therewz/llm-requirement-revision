"""Score captured revision evidence against the cleaned baseline and fixed controls."""

from copy import deepcopy
import importlib.util
import json

from .baseline import BY_ID, classify, evaluator, linked
from .prepare import ROOT, RUN, digest, encode, parent, read_checked, write_same

spec = importlib.util.spec_from_file_location('preserved_core_scoring', ROOT / 'code/bounded_sessions_v1/scoring.py')
original_scorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original_scorer)

IDENTITY = ('session_id', 'participant_id', 'task', 'group', 'condition', 'provider', 'model', 'repeat')


class CleanedScorer:
    def __init__(self, preparation_sha256, baseline_manifest_sha256):
        parent()
        prepared = json.loads(read_checked(RUN / 'preparation.json', preparation_sha256))
        manifest = json.loads(read_checked(RUN / 'baseline_manifest.json', baseline_manifest_sha256))
        self.plans = {plan['session_id']: plan for plan in prepared['sessions']}
        self.rows = {row['participant_id']: row for row in manifest['records']}
        self.suite_ids = json.loads((ROOT / 'runs/withdrawal_keys_v1/suite_case_ids.json').read_bytes())

    def score(self, plan, result, observations):
        """Score a verified terminal session and its bound evaluation envelope."""
        if self.plans.get(plan.get('session_id')) != plan:
            raise ValueError('Session does not use the cleaned input preparation')
        row = self.rows[plan['participant_id']]
        if (plan['source_sha256'] != row['starting_source_sha256']
                or any(result.get(key) != plan[key] for key in IDENTITY)):
            raise ValueError('Cleaned starting source or session identity differs')
        base = {**{key: plan[key] for key in IDENTITY}, 'session_status': result['status'],
                'baseline_source_sha256': row['starting_source_sha256'],
                'fixed_profile': row['fixed_profile'], 'weighted_overall_score': None}
        if result['status'] != 'completed' or observations is None:
            return {**base, 'withdrawal': None, 'core_preservation': None, 'supplied_five': None}
        if (any(observations.get(key) != plan[key] for key in IDENTITY)
                or observations.get('freeze_sha256') != evaluator.FREEZE_SHA256
                or not result.get('final_source_sha256')
                or observations.get('source_sha256') != result['final_source_sha256']):
            raise ValueError('Evaluation evidence does not match the cleaned session and final file')

        task = row['task']
        archived = json.loads(read_checked(ROOT / row['baseline_path'], row['baseline_sha256']))
        if archived.get('source_sha256') != row['starting_source_sha256']:
            raise ValueError('Baseline source hash differs')
        core = original_scorer._suite(observations.get('core28'), self.suite_ids[task]['core28'], archived['core28'])
        supplied = original_scorer._suite(observations.get('supplied5'), self.suite_ids[task]['supplied5'], archived['supplied5'])
        baseline_passes = set(row['core_baseline_pass_ids'])
        lost = sorted(k for k in baseline_passes if core['outcomes'].get(k) in ('failed', 'error'))
        preservation = {
            'complete': core['complete'], 'opportunity_count': len(baseline_passes),
            'loss_count': len(lost) if core['complete'] and baseline_passes else None,
            'known_observed_loss_ids': lost, 'revision_suite': core,
        }
        target_record = observations.get('targets') or {}
        cases = target_record.get('cases', {})
        key = BY_ID[task]
        if not isinstance(cases, dict) or set(cases) - set(key):
            raise ValueError('Unknown or malformed target evidence')
        for evidence in cases.values():
            original_scorer._validate_observation(evidence)
        eligible = row['eligible_case_ids']
        controls = {control for cid in eligible for control in linked(key[cid])}
        if controls != set(row['required_linked_controls_after_edit']):
            raise ValueError('Fixed linked controls changed')
        missing = sorted((set(eligible) | controls) - set(cases))
        meta = target_record.get('execution_metadata') or {}
        complete = (bool(eligible) and not missing and type(meta.get('returncode')) is int
                    and meta['returncode'] == 0 and not target_record.get('import_error')
                    and not target_record.get('execution_failure') and not meta.get('timed_out_file')
                    and not meta.get('timed_out', False) and meta.get('complete', True) is True
                    and target_record.get('complete', True) is True)
        expected = 'RETAINED' if plan['condition'] == 'RR' else 'RESTORED'
        by_case = [dict(classify(task, key[cid], cases), case_id=cid) for cid in eligible]
        matched = sum(case['status'] == expected for case in by_case)
        withdrawal = {
            'eligible_case_count': len(eligible), 'complete': complete,
            'expected_status': expected, 'met_count': matched,
            'all_targets_met': matched == len(eligible) if complete else None,
            'missing_required_ids': missing, 'case_results': by_case,
            'failed_control_case_ids': [c['case_id'] for c in by_case if c.get('controls_ok') is False],
        }
        return {**base, 'withdrawal': withdrawal, 'core_preservation': preservation, 'supplied_five': supplied}


def verify_saved_replay():
    prep_hash = digest((RUN / 'preparation.json').read_bytes())
    baseline_hash = digest((RUN / 'baseline_manifest.json').read_bytes())
    scorer = CleanedScorer(prep_hash, baseline_hash)
    arms = {arm: {'sessions': 0, 'eligible_targets': 0, 'met_targets': 0} for arm in ('RR', 'SA', 'EW')}
    checks = set()
    for plan in scorer.plans.values():
        row = scorer.rows[plan['participant_id']]
        observed = json.loads(read_checked(ROOT / row['baseline_path'], row['baseline_sha256']))
        observed.update({key: plan[key] for key in IDENTITY})
        result = {**{key: plan[key] for key in IDENTITY},
                  'status': 'completed', 'final_source_sha256': plan['source_sha256']}
        score = scorer.score(plan, result, observed)
        w = score['withdrawal']
        if score['core_preservation']['loss_count'] != 0 or not score['core_preservation']['complete']:
            raise ValueError('Cleaned-source replay did not reproduce core preservation')
        if w['failed_control_case_ids'] or (w['eligible_case_count'] > 0 and not w['complete']):
            raise ValueError('Cleaned-source replay did not reproduce control evidence')
        arm = arms[plan['condition']]
        arm['sessions'] += 1
        arm['eligible_targets'] += w['eligible_case_count']
        arm['met_targets'] += w['met_count']
        if plan['condition'] == 'EW' and row['eligible_case_ids'] and plan['task'] not in checks:
            # Illustrate why post-edit controls are still needed. These altered
            # records are synthetic counterexamples, not participant outcomes.
            task = plan['task']
            example = deepcopy(observed)
            cases = example['targets']['cases']
            cid = row['eligible_case_ids'][0]
            target = BY_ID[task][cid]
            if task == 'A':
                cases[cid]['value'] = sorted(set(cases[cid]['value'] + target['target_slots']))
                cases[linked(target)[0]]['value'] = ['09:00']
            else:
                cases[cid]['value'] = True
                overloaded = next(c for c in linked(target) if BY_ID['B'][c]['retained_expectation'] is False)
                cases[overloaded]['value'] = True
            bad = scorer.score(plan, result, example)['withdrawal']
            if bad['met_count'] != 1 or cid not in bad['failed_control_case_ids']:
                raise ValueError('Counterexample did not detect a passed target with a failed control')
            example['targets']['execution_metadata']['complete'] = False
            if scorer.score(plan, result, example)['withdrawal']['complete']:
                raise ValueError('Contradictory metadata incorrectly became complete evidence')
            del example['targets']['execution_metadata']['complete']
            del cases[linked(target)[0]]
            missing = scorer.score(plan, result, example)['withdrawal']
            if missing['complete'] or missing['all_targets_met'] is not None:
                raise ValueError('Missing control incorrectly became complete evidence')
            checks.add(task)
    if (checks != {'A', 'B'} or arms['RR']['met_targets'] != arms['RR']['eligible_targets']
            or any(arms[a]['met_targets'] for a in ('SA', 'EW'))):
        raise ValueError('Unexpected replay totals')
    report = {
        'evidence_class': 'SAVED_CLEANED_BASELINE_REPLAY_AND_SYNTHETIC_CONTROL_CHECKS',
        'model_calls': 0, 'sessions': len(scorer.plans), 'by_condition': arms,
        'synthetic_control_and_missingness_counterexamples_checked': sorted(checks),
        'preparation_sha256': prep_hash, 'baseline_manifest_sha256': baseline_hash,
    }
    write_same(RUN / 'scorer_verification.json', encode(report))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    verify_saved_replay()
