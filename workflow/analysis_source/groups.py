"""Exploratory independent-group analysis of immutable saved v2 results.

Run only after the coordinator writes a passing preflight record. This module
does not execute participant code, access model providers or modify v2 data.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import itertools
import json
import math
import platform
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/statistical_analysis_v3/groups'
PLAN = 'planning/ANALYSIS_PLAN_v2_PRESTAT.md'
PLAN_SHA = 'abf7fa160883376f0b74a35f85433522e7474a3b76142bb2ac33a6fb01afa416'
LOCK = 'planning/STATISTICAL_ANALYSIS_V3_OPERATIONAL_LOCK.md'
LOCK_JSON = 'planning/STATISTICAL_ANALYSIS_V3_OPERATIONAL_LOCK.json'
PREFLIGHT = 'reports/statistical_analysis_v3/PREFLIGHT.json'
V2_ROOT = 'reports/full_analysis_v2_prelim/'
V2_MANIFEST = V2_ROOT + 'analysis_manifest.json'
GROUPS = ('G1', 'G2', 'G3')
TASKS = ('A', 'B')
PROVIDERS = ('anthropic', 'openai')
CONTEXTS = ('SA', 'EW', 'EW_minus_SA')
METRICS = ('residue_rate', 'all_target_success', 'core_loss_rate')
ARMS = ('RR', 'SA', 'EW')
BASE_SEED = 20261106
N_PERM = 9999
N_BOOT = 10000
FAMILY_SIZE = 108
TOL = 1e-12


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_bytes(rel, inputs, expected=None):
    data = (ROOT / rel).read_bytes()
    sha = digest(data)
    if expected is not None and expected != sha:
        raise ValueError(f'Input hash mismatch: {rel}')
    inputs[rel] = sha
    return data


def rng_for(key):
    """Independent deterministic PCG64 stream keyed by analysis identity."""
    raw = json.dumps([BASE_SEED, *key], ensure_ascii=True,
                     separators=(',', ':')).encode('utf-8')
    seed_hex = digest(raw)
    seed = int(seed_hex[:32], 16)
    return np.random.default_rng(seed), seed_hex


def mean_fraction(values):
    return sum(values, Fraction()) / len(values) if values else None


def to_float(value):
    return float(value) if value is not None else None


def metric_value(row, metric, strict=False):
    """Derive fractions from integer score counts; check stored v2 values."""
    if row['evaluated'] != 'True':
        return None
    if metric == 'core_loss_rate':
        den = int(row['core_opportunities'])
        value = Fraction(int(row['PF']), den) if den else None
        stored = row['core_loss_rate']
    elif metric == 'residue_rate':
        den = int(row['target_n'])
        value = Fraction(int(row['RETAINED_count']) + int(row['PARTIAL_count']), den) if den else None
        stored = row['residue_rate']
    elif metric == 'all_target_success':
        column = 'strict_target_success' if strict else 'all_target_success'
        stored = row[column]
        value = Fraction(int(stored), 1) if stored else None
    else:
        raise ValueError(f'Unknown metric {metric}')
    if (value is None) != (stored == ''):
        raise ValueError(f'Unexpected missing value: {row["session_id"]} {metric}')
    if value is not None and (not 0 <= value <= 1 or abs(float(value) - float(stored)) > TOL):
        raise ValueError(f'Rate mismatch: {row["session_id"]} {metric}')
    return value


def load_data():
    inputs = {}
    read_bytes(PLAN, inputs, PLAN_SHA)
    lock_json = json.loads(read_bytes(LOCK_JSON, inputs))
    lock_sha = lock_json['operational_lock_sha256']
    read_bytes(LOCK, inputs, lock_sha)
    if lock_json['plan_sha256'] != PLAN_SHA or lock_json['holm_family_sizes']['group'] != FAMILY_SIZE:
        raise ValueError('Statistical policy lock mismatch')
    preflight = json.loads(read_bytes(PREFLIGHT, inputs))
    if preflight.get('status') != 'PASS' or preflight.get('plan_sha256') != PLAN_SHA:
        raise ValueError('Passing preflight and matching frozen plan are required')
    if preflight.get('operational_lock_sha256') != lock_sha:
        raise ValueError('Preflight does not bind the operational lock')
    if preflight.get('implementation_sha256', {}).get('groups') != digest(Path(__file__).read_bytes()):
        raise ValueError('Preflight does not bind the current group-analysis implementation')
    manifest_data = read_bytes(V2_MANIFEST, inputs, lock_json['v2_manifest_sha256'])
    manifest = json.loads(manifest_data)
    if manifest['plan_sha256'] != PLAN_SHA or manifest['new_hypothesis_tests'] != 0:
        raise ValueError('Unexpected v2 provenance')
    rel = V2_ROOT + 'tables/session_metrics.csv'
    data = read_bytes(rel, inputs, manifest['outputs']['session_metrics.csv'])
    lines = data.decode('utf-8').splitlines()
    records = list(csv.DictReader(lines))
    if len(records) != manifest['table_rows']['session_metrics.csv']:
        raise ValueError('v2 row count mismatch')
    rows = defaultdict(dict)
    patient_group = {}
    for r in records:
        if r['view'] not in manifest['views'] or r['task'] not in TASKS or r['provider'] not in PROVIDERS:
            raise ValueError(f'Bad stratum: {r}')
        if r['condition'] not in ARMS or r['group'] not in GROUPS:
            raise ValueError(f'Bad arm/group: {r}')
        pid = r['participant_id']
        if pid in patient_group and patient_group[pid] != r['group']:
            raise ValueError(f'Participant group changed across observations: {pid}')
        patient_group[pid] = r['group']
        key = (r['task'], r['provider'], pid, r['condition'])
        if key in rows[r['view']]:
            raise ValueError(f'Duplicate session in view: {r["view"]} {key}')
        rows[r['view']][key] = r
    if set(rows) != set(manifest['views']) or len(rows) != 24:
        raise ValueError('Unexpected view inventory')
    for view, view_data in rows.items():
        subjects = {(task, prov, pid) for task, prov, pid, _ in view_data}
        for task, prov, pid in subjects:
            obs = [view_data.get((task, prov, pid, arm)) for arm in ARMS]
            if any(r is None for r in obs):
                raise ValueError(f'Missing condition in planned participant slot: {view} {pid}')
            if len({r['group'] for r in obs}) != 1:
                raise ValueError(f'Group changed across conditions: {view} {pid}')
            if len({r['selected_case_ids'] for r in obs}) != 1:
                raise ValueError(f'Case selection changed across conditions: {view} {pid}')
    return rows, inputs


def sample_groups(view_data, task, provider, context, metric, strict):
    """Keep missing outcomes out of analysis while retaining planned counts."""
    lookup = {(pid, arm): r for (t, p, pid, arm), r in view_data.items()
              if t == task and p == provider}
    result = {g: [] for g in GROUPS}
    planned = Counter()
    subject_ids = {pid for pid, _ in lookup}
    for pid in sorted(subject_ids):
        group = lookup[pid, 'RR']['group']
        planned[group] += 1
        if context == 'EW_minus_SA':
            sa = metric_value(lookup[pid, 'SA'], metric, strict)
            ew = metric_value(lookup[pid, 'EW'], metric, strict)
            value = ew - sa if sa is not None and ew is not None else None
        else:
            value = metric_value(lookup[pid, context], metric, strict)
        if value is not None:
            result[group].append((pid, value))
    return result, planned


def permutation_test(left, right, key):
    """Two-sided conditional group-label permutation test, fixed budget."""
    n_left, n_right = len(left), len(right)
    if n_left < 2 or n_right < 2:
        raise ValueError('At least two observations per group are required')
    pooled = list(left) + list(right)
    if len(set(pooled)) == 1:
        raise ValueError('Constant pooled outcome does not yield an informative test')
    n = n_left + n_right
    # Integer weights preserve all rational distinctions in the observed
    # rates. For fixed n_left/n_right, comparing absolute differences in
    # means is equivalent to comparing |n_left * total - n * left_sum|.
    scale = math.lcm(*(x.denominator for x in pooled))
    weights = [x.numerator * (scale // x.denominator) for x in pooled]
    total = sum(weights)
    observed_stat = abs(n_left * total - n * sum(weights[:n_left]))
    # Each intermediate term is bounded by this sum. If values are too large
    # for int64, fall back to arbitrary-precision Python integers.
    int64_max = int(np.iinfo(np.int64).max)
    safe_int64 = (n_left + n) * sum(abs(x) for x in weights) <= int64_max
    pool = np.array(weights, dtype=np.int64) if safe_int64 else None
    allocations = math.comb(n, n_left)
    if allocations <= N_PERM:
        ids = np.fromiter((i for indices in itertools.combinations(range(n), n_left)
                           for i in indices), dtype=np.int64, count=allocations * n_left)
        ids = ids.reshape(allocations, n_left)
        if safe_int64:
            left_sum = np.sum(pool[ids], axis=1, dtype=np.int64)
            stat = np.abs(n_left * total - n * left_sum)
            extreme = int(np.count_nonzero(stat >= observed_stat))
        else:
            extreme = sum(abs(n_left * total - n * sum(weights[int(i)] for i in indices)) >= observed_stat
                          for indices in ids)
        return dict(p=extreme / allocations, method='exact_group_label_allocations',
                    draws=allocations, extreme=extreme, seed_hex='',
                    integer_scale=str(scale), integer_backend='int64' if safe_int64 else 'python_int',
                    comparison='exact_integer')
    rng, seed_hex = rng_for((*key, 'group_permutation'))
    extreme = 0
    for start in range(0, N_PERM, 2000):
        count = min(2000, N_PERM - start)
        # Each row is an independent random permutation of participant indices.
        ids = rng.permuted(np.broadcast_to(np.arange(n), (count, n)), axis=1)[:, :n_left]
        if safe_int64:
            left_sum = np.sum(pool[ids], axis=1, dtype=np.int64)
            stat = np.abs(n_left * total - n * left_sum)
            extreme += int(np.count_nonzero(stat >= observed_stat))
        else:
            extreme += sum(abs(n_left * total - n * sum(weights[int(i)] for i in indices)) >= observed_stat
                           for indices in ids)
    return dict(p=(extreme + 1) / (N_PERM + 1), method='monte_carlo_group_label_plus_one',
                draws=N_PERM, extreme=extreme, seed_hex=seed_hex, integer_scale=str(scale),
                integer_backend='int64' if safe_int64 else 'python_int', comparison='exact_integer')


def bootstrap_ci(left, right, key):
    if len(left) < 2 or len(right) < 2:
        raise ValueError('At least two observations per group are required')
    rng, seed_hex = rng_for((*key, 'group_bootstrap'))
    a = np.array([float(x) for x in left], dtype=np.float64)
    b = np.array([float(x) for x in right], dtype=np.float64)
    a_draws = rng.integers(0, len(a), size=(N_BOOT, len(a)))
    b_draws = rng.integers(0, len(b), size=(N_BOOT, len(b)))
    values = np.mean(b[b_draws], axis=1) - np.mean(a[a_draws], axis=1)
    low, high = np.quantile(values, [.025, .975], method='linear')
    return dict(low=float(low), high=float(high), draws=N_BOOT,
                empirical_degenerate=bool(np.all(values == values[0])), seed_hex=seed_hex)


def holm_reserved(rows, family_size=FAMILY_SIZE):
    """Reserve all prespecified slots by padding untestable hypotheses with 1."""
    if len(rows) != family_size:
        raise ValueError(f'Expected {family_size} slots, got {len(rows)}')
    sortable = sorted(enumerate(rows), key=lambda z: (z[1]['p_raw'] if z[1]['p_raw'] is not None else 1.0, z[0]))
    running = 0.0
    for position, (_, row) in enumerate(sortable):
        internal_p = row['p_raw'] if row['p_raw'] is not None else 1.0
        running = max(running, min(1.0, (family_size - position) * internal_p))
        row['p_holm'] = running if row['p_raw'] is not None else None
        row['holm_family_size'] = family_size
    return rows


def make_result(view, task, provider, context, metric, left_name, right_name,
                samples, planned):
    left = samples[left_name]
    right = samples[right_name]
    lv, rv = [x[1] for x in left], [x[1] for x in right]
    lm, rm = mean_fraction(lv), mean_fraction(rv)
    difference = rm - lm if lm is not None and rm is not None else None
    strict = view.endswith('__strict_controls') and metric == 'all_target_success'
    field = 'strict_target_success' if strict else metric
    key = (view, task, provider, context, metric, left_name, right_name)
    row = dict(view=view, task=task, provider=provider, context=context, metric=metric,
               source_metric=field,
               endpoint_label=('complete_target_and_linked_controls' if strict else metric),
               group_left=left_name, group_right=right_name,
               contrast=f'{right_name} minus {left_name}',
               planned_left=planned[left_name], planned_right=planned[right_name],
               n_left=len(lv), n_right=len(rv),
               missing_left=planned[left_name] - len(lv), missing_right=planned[right_name] - len(rv),
               left_ids=[x[0] for x in left], right_ids=[x[0] for x in right],
               left_mean=to_float(lm), right_mean=to_float(rm), difference=to_float(difference),
               difference_pp=100 * float(difference) if difference is not None else None,
               p_raw=None, p_holm=None, permutation_method='', permutation_draws=0,
               permutation_extreme=None, permutation_seed_sha256='', permutation_integer_scale='',
               permutation_integer_backend='', permutation_comparison='',
               ci_low=None, ci_high=None, ci_low_pp=None, ci_high_pp=None,
               bootstrap_draws=0, bootstrap_seed_sha256='', interval_empirically_degenerate=None,
               status='')
    if view.startswith('all72_preservation__') and metric != 'core_loss_rate':
        row['status'] = 'not_applicable_all72_preservation_only'
    elif not lv or not rv:
        row['status'] = 'unassessable_empty_group'
    elif len(lv) < 2 or len(rv) < 2:
        row['status'] = 'descriptive_only_fewer_than_two_per_group'
    elif len(set(lv + rv)) == 1:
        row['status'] = 'no_informative_variation_in_pooled_values'
    else:
        p = permutation_test(lv, rv, key)
        ci = bootstrap_ci(lv, rv, key)
        row.update(p_raw=p['p'], permutation_method=p['method'], permutation_draws=p['draws'],
                   permutation_extreme=p['extreme'], permutation_seed_sha256=p['seed_hex'],
                   permutation_integer_scale=p['integer_scale'], permutation_integer_backend=p['integer_backend'],
                   permutation_comparison=p['comparison'],
                   ci_low=ci['low'], ci_high=ci['high'], ci_low_pp=100*ci['low'], ci_high_pp=100*ci['high'],
                   bootstrap_draws=ci['draws'], bootstrap_seed_sha256=ci['seed_hex'],
                   interval_empirically_degenerate=ci['empirical_degenerate'], status='tested')
    return row


def analyze_view(view, view_data):
    rows = []
    for task, provider, context, metric in itertools.product(TASKS, PROVIDERS, CONTEXTS, METRICS):
        strict = view.endswith('__strict_controls') and metric == 'all_target_success'
        # In all-72 views only core preservation is within the planned scope.
        if view.startswith('all72_preservation__') and metric != 'core_loss_rate':
            samples, planned = {g: [] for g in GROUPS}, Counter()
        else:
            samples, planned = sample_groups(view_data, task, provider, context, metric, strict)
        for left, right in itertools.combinations(GROUPS, 2):
            rows.append(make_result(view, task, provider, context, metric, left, right, samples, planned))
    return holm_reserved(rows)


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, separators=(',', ':')) if isinstance(v, list) else v
                             for k, v in row.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Run after passing saved preflight')
    args = parser.parse_args()
    if not args.execute:
        parser.error('A passing preflight and --execute are required')
    views, inputs = load_data()
    result = []
    for view in sorted(views):
        result.extend(analyze_view(view, views[view]))
        print(f'completed {view}', flush=True)
    assert len(result) == 24 * FAMILY_SIZE
    OUT.mkdir(parents=True, exist_ok=True)
    table = OUT / 'group_tests.csv'
    write_csv(table, result)
    manifest = dict(status='COMPLETE', description='Exploratory program-level group-label tests',
                    frozen_plan_sha256=PLAN_SHA, python=platform.python_version(), numpy=np.__version__,
                    operational_lock_sha256=inputs[LOCK], preflight_sha256=inputs[PREFLIGHT],
                    seed=BASE_SEED, draws_random=N_PERM, draws_bootstrap=N_BOOT,
                    family_size_per_view=FAMILY_SIZE, views=len(views), rows=len(result),
                    status_counts=dict(Counter(r['status'] for r in result)),
                    inputs=dict(sorted(inputs.items())),
                    operations_sha256=digest((ROOT/'code/statistical_analysis_v3_groups/OPERATIONS.md').read_bytes()),
                    script_sha256=digest(Path(__file__).read_bytes()),
                    output_sha256=digest(table.read_bytes()),
                    model_calls=0, participant_execution=0, regraded_evaluations=0)
    (OUT/'analysis_manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'rows':len(result), 'statuses':manifest['status_counts'],
                      'output_sha256':manifest['output_sha256']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
