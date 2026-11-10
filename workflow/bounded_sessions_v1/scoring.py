"""Post-session measurement from captured observations, never participant execution.

Fixed baseline profiles and eligible cases are selected before model outcomes.
Core preservation and target behavior remain separate; old five-test results
are reported without treating their retained-rule assertions as withdrawal truth.
"""
import csv
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
RUN = 'runs/withdrawal_keys_v1/'
MANIFESTS = {
    'reports/withdrawal_keys_v1/ARTIFACT_HASHES.json': '60efa485cf3852b1097b427252b8e8e79dbb05c7068ba632156c50c39bceeaa1',
    'reports/matched_inputs_v1/ARTIFACT_HASHES.json': '24ff5da6f4e27562d66a1d2c8e165e70c680381596d42ecfcc0c0a7f9c83fb04',
}


class ScoringIntegrityError(ValueError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _hashes():
    hashes = {}
    for path, expected in MANIFESTS.items():
        data = (ROOT / path).read_bytes()
        if sha(data) != expected:
            raise ScoringIntegrityError('Frozen artifact manifest changed')
        for rec in json.loads(data)['files']:
            if rec['path'] in hashes and hashes[rec['path']] != rec['sha256']:
                raise ScoringIntegrityError('Manifest disagreement')
            hashes[rec['path']] = rec['sha256']
    return hashes


def _checked(path, hashes):
    data = (ROOT / path).read_bytes()
    if path not in hashes or sha(data) != hashes[path]:
        raise ScoringIntegrityError('Frozen artifact changed: ' + path)
    return data


def _context(sid):
    hashes = _hashes()
    inventory = json.loads(_checked(RUN + 'inventory.json', hashes))
    candidates = [r for r in inventory if r['participant_id'] == sid]
    if len(candidates) != 1:
        raise ScoringIntegrityError('Unknown participant')
    row = candidates[0]
    raw_path = RUN + f'raw/{sid}_P2.json'
    raw_bytes = _checked(raw_path, hashes)
    raw = json.loads(raw_bytes)
    freeze = _checked(RUN + 'freeze.json', hashes)
    if raw['source_sha256'] != row['P2']['sha256'] or raw['freeze_sha256'] != sha(freeze):
        raise ScoringIntegrityError('Baseline lineage mismatch')
    key = json.loads(_checked(RUN + f"answer_key_{row['task']}.json", hashes))
    programs = list(csv.DictReader(io.StringIO(_checked(RUN + 'derived/programs.csv', hashes).decode())))
    program = next(p for p in programs if p['participant_id'] == sid)
    cases = [r for r in csv.DictReader(io.StringIO(_checked(RUN + 'derived/target_cases.csv', hashes).decode())) if r['participant_id'] == sid]
    eligible = [r for r in cases if r['selected_profile'] == 'True' and r['p2_eligible'] == 'True']
    for relative in ['code/withdrawal_keys_v1/task_a.py', 'code/withdrawal_keys_v1/summarize.py', 'code/withdrawal_keys_v1/task_b.py', 'code/withdrawal_keys_v1/assess.py']:
        _checked(relative, hashes)
    # Trusted, hash-pinned evaluator modules only. Neither main() is invoked.
    directory = str(ROOT / 'code/withdrawal_keys_v1')
    if directory not in sys.path:
        sys.path.insert(0, directory)
    import task_a
    import summarize
    coverage = json.loads(_checked('reports/matched_inputs_v1/specification_audit/coverage.json', hashes))
    flags = next(r['flag_ids'] for r in coverage if r['participant_id'] == sid)
    ids = json.loads(_checked(RUN + 'suite_case_ids.json', hashes))[row['task']]
    return {'inventory': row, 'baseline': raw, 'raw_path': raw_path, 'raw_sha256': sha(raw_bytes), 'freeze_sha256': sha(freeze),
            'key': key, 'program': program, 'eligible': eligible, 'flags': flags, 'suite_ids': ids,
            'classify_a': task_a.classify, 'classify_b': summarize.score_b}


def _suite(obj, expected_ids, baseline_obj):
    if obj is None:
        return {'complete': False, 'expected': len(expected_ids), 'observed': 0, 'passed_ids': [],
                'passed_count': 0, 'missing_ids': sorted(expected_ids), 'extra_ids': [], 'outcomes': {}}
    if not isinstance(obj, dict):
        raise ScoringIntegrityError('Malformed evaluation suite')
    if obj.get('suite_sha256') != baseline_obj['suite_sha256']:
        raise ScoringIntegrityError('Evaluation suite hash differs')
    results, metadata = obj.get('results', {}), obj.get('metadata', {})
    if not isinstance(results, dict) or not isinstance(metadata, dict):
        raise ScoringIntegrityError('Malformed suite observation')
    for result in results.values():
        if not isinstance(result, list) or len(result) != 2 or result[0] not in ('passed', 'failed', 'error', 'skipped') or not isinstance(result[1], str):
            raise ScoringIntegrityError('Malformed test outcome')
    required = {'returncode', 'timed_out_file', 'collection_error'}
    complete = (set(results) == set(expected_ids) and required <= set(metadata)
                and metadata['timed_out_file'] is False and metadata['collection_error'] is None
                and type(metadata['returncode']) is int and metadata['returncode'] in (0, 1)
                and obj.get('expected_case_count') == len(expected_ids)
                and not any(v[0] == 'skipped' for v in results.values()))
    complete = complete and obj.get('complete', True) is True and metadata.get('complete', True) is True
    if 'pytest_exitcode' in metadata:
        complete = complete and type(metadata['pytest_exitcode']) is int and metadata['pytest_exitcode'] in (0, 1)
    complete = complete and metadata.get('timed_out', False) is False
    passed = sorted(k for k,v in results.items() if v[0] == 'passed')
    return {'complete': complete, 'expected': len(expected_ids), 'observed': len(results),
            'passed_ids': passed, 'passed_count': len(passed), 'missing_ids': sorted(set(expected_ids) - set(results)),
            'extra_ids': sorted(set(results) - set(expected_ids)), 'outcomes': {k:v[0] for k,v in results.items()}}


def _validate_observation(obs):
    if not isinstance(obs, dict):
        raise ScoringIntegrityError('Malformed target observation')
    kind = obs.get('kind')
    if kind == 'timeout':
        return
    if kind == 'exc' and isinstance(obs.get('exc'), str) and isinstance(obs.get('msg'), str):
        return
    if kind != 'ret' or not isinstance(obs.get('type'), str):
        raise ScoringIntegrityError('Malformed target observation kind/type')
    typ = obs['type']
    if typ == 'bool' and type(obs.get('value')) is bool:
        return
    if typ == 'list_str' and isinstance(obs.get('value'), list) and all(type(v) is str for v in obs['value']):
        return
    if typ == 'tuple' and isinstance(obs.get('items'), list) and type(obs.get('length')) is int and obs['length'] >= len(obs['items']):
        return
    if typ not in ('bool', 'list_str', 'tuple') and isinstance(obs.get('repr'), str):
        return
    raise ScoringIntegrityError('Malformed normalized return value')


def score_observations(plan, result, observations, baseline=None):
    """Score normalized evaluator output; caller verifies engine terminal evidence first.

    `observations` uses the original captured record schema with participant/task/
    group/source_sha256/freeze_sha256, targets.cases and core28/supplied5 objects.
    A supplied baseline must equal the pinned original, never a caller's new oracle.
    """
    context = _context(plan['participant_id'])
    original = context['baseline']
    if baseline is not None and baseline != original:
        raise ScoringIntegrityError('Supplied baseline differs from pinned original')
    for key in ('participant_id', 'task', 'group'):
        if plan[key] != original[key] or result[key] != plan[key]:
            raise ScoringIntegrityError('Session dimensions differ from baseline')
    for key in ('session_id', 'condition', 'provider', 'model', 'repeat'):
        if result[key] != plan[key]:
            raise ScoringIntegrityError('Session identity mismatch')
    if plan['condition'] not in ('RR', 'SA', 'EW'):
        raise ScoringIntegrityError('Unknown condition')
    identity = {k:plan[k] for k in ('session_id','participant_id','task','group','condition','provider','model','repeat')}
    base = {**identity, 'session_status': result['status'], 'selected_profile': context['program']['selected_profile'],
            'baseline_program_flags': context['program'], 'specification_flag_ids': context['flags'],
            'interpretation': 'fixed benchmark behavior, not universal instruction compliance',
            'baseline_source_sha256': original['source_sha256'], 'freeze_sha256': context['freeze_sha256'],
            'exact_hash_evidence_reused': False, 'new_participant_execution_by_scorer': False,
            'weighted_overall_score': None}
    if result['status'] != 'completed':
        return {**base, 'assessable': False, 'reason': 'session_not_completed', 'condition_success': False,
                'withdrawal': None, 'core_preservation': None, 'supplied_five': None}
    if not isinstance(observations, dict):
        return {**base, 'assessable': False, 'reason': 'observations_missing', 'condition_success': None,
                'withdrawal': None, 'core_preservation': None, 'supplied_five': None}
    for key in ('participant_id', 'task', 'group'):
        if observations.get(key) != plan[key]:
            raise ScoringIntegrityError('Observation identity mismatch')
    if not result.get('final_source_sha256') or observations.get('source_sha256') != result['final_source_sha256']:
        raise ScoringIntegrityError('Observations do not match final source')
    if observations.get('freeze_sha256') != context['freeze_sha256']:
        raise ScoringIntegrityError('Observation key freeze differs')
    core = _suite(observations.get('core28'), context['suite_ids']['core28'], original['core28'])
    prior_core = _suite(original['core28'], context['suite_ids']['core28'], original['core28'])
    opportunities = prior_core['passed_ids']
    known_losses = [k for k in opportunities if k in core['outcomes'] and core['outcomes'][k] in ('failed', 'error')]
    assessable_core = prior_core['complete'] and core['complete'] and bool(opportunities)
    preservation = {'assessable': assessable_core, 'complete': core['complete'], 'opportunity_count': len(opportunities),
                    'opportunity_ids': opportunities, 'loss_count': len(known_losses) if assessable_core else None,
                    'known_observed_loss_ids': known_losses, 'no_losses': not known_losses if assessable_core else None,
                    'revision_suite': core}
    supplied = _suite(observations.get('supplied5'), context['suite_ids']['supplied5'], original['supplied5'])
    supplied['interpretation'] = 'unchanged supplied assertions; not pooled with withdrawal targets'
    targets_obj = observations.get('targets')
    target_observations = targets_obj.get('cases') if isinstance(targets_obj, dict) else None
    if not isinstance(target_observations, dict):
        target_observations = {}
    by_id = {c['case_id']:c for c in context['key']['cases']}
    if set(target_observations) - set(by_id):
        raise ScoringIntegrityError('Unknown target observation IDs')
    for observation in target_observations.values():
        _validate_observation(observation)
    scores, required = [], set()
    for fixed in context['eligible']:
        case = by_id[fixed['case_id']]
        required.add(case['case_id'])
        required.update(case.get('control_ids', case.get('linked_controls', [])))
        if plan['task'] == 'A':
            scored = context['classify_a'](case, target_observations)
        else:
            scored = context['classify_b'](case, target_observations, by_id)
        scores.append({'case_id':case['case_id'], **scored, 'fixed_baseline_flags': fixed})
    meta = targets_obj.get('execution_metadata', {}) if isinstance(targets_obj, dict) else {}
    complete = bool(required) and required <= set(target_observations) and type(meta.get('returncode')) is int and meta['returncode'] == 0
    complete = complete and targets_obj.get('import_error') is None
    complete = complete and targets_obj.get('complete', True) is True
    complete = complete and meta.get('complete', True) is True and meta.get('timed_out', False) is False
    complete = complete and meta.get('timed_out_file', False) is False and targets_obj.get('execution_failure', False) is False
    expected = 'RETAINED' if plan['condition'] == 'RR' else 'RESTORED'
    success_count = sum(s['status'] == expected for s in scores)
    success = (success_count == len(scores)) if complete else None
    withdrawal = {'expected_status': expected, 'eligible_case_count': len(scores), 'complete': complete,
                  'success_count': success_count, 'all_eligible_targets_met': success,
                  'missing_required_observation_ids': sorted(required - set(target_observations)),
                  'case_results': scores, 'no_eligible_targets_is_unassessable': not bool(scores)}
    return {**base, 'assessable': complete and assessable_core, 'condition_success': success,
            'reason': 'scored' if complete else 'withdrawal_evidence_incomplete_or_no_eligible_targets',
            'withdrawal': withdrawal, 'core_preservation': preservation, 'supplied_five': supplied,
            'source_sha256': result['final_source_sha256']}


def score_saved_baseline_replay(plan, result):
    """Reuse authentic captured P2 observations only for byte-identical final code."""
    context = _context(plan['participant_id'])
    if result.get('final_source_sha256') != context['baseline']['source_sha256']:
        raise ScoringIntegrityError('Changed code cannot reuse baseline execution evidence')
    scored = score_observations(plan, result, deepcopy(context['baseline']))
    scored.update({'exact_hash_evidence_reused': True, 'evidence_source_path': context['raw_path'],
                   'evidence_source_sha256': context['raw_sha256'],
                   'evidence_class': 'unchanged_source_replay_of_previously_captured_baseline_not_new_model_output'})
    return scored
