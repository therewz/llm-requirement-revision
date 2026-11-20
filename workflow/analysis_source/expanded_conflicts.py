"""Additive post hoc expanded-conflict sensitivity on immutable saved rows only.

No legacy main() is called. Imports are definitions-only and bytecode writes are
disabled. Exact conditional probabilities replace simulation uniformly in this
new appendix; canonical outputs are never touched.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
from fractions import Fraction as F
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import platform
import sys
import numpy as np

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / 'reports/results_readiness_v1/conflict_update'
POLICY = DEFAULT_OUT / 'POSTHOC_ADDENDUM.json'
TABLES = ROOT / 'reports/full_analysis_v2_prelim/tables'
COHORTS = ('primary69', 'alternative62')
VARIANTS = ('exclude_conflicts', 'conflicts_only', 'phase_i_no_conflict')
TASKS = ('A', 'B')
PROVIDERS = ('anthropic', 'openai')
ARMS = ('RR', 'SA', 'EW')
GROUPS = ('G1', 'G2', 'G3')
CONTRASTS = (('SA', 'EW'), ('RR', 'SA'), ('RR', 'EW'))
LABELS = ('RESTORED', 'RETAINED', 'PARTIAL', 'OTHER_FAILURE', 'INDETERMINATE')
ORIGINAL = frozenset(('S0034', 'S0041', 'S0049', 'S0053', 'S0058', 'S0060', 'S0046'))
EXPANDED = ORIGINAL | {'S0069'}
SEED = 20261106
BOOT = 10000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def module(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def helpers():
    return (module('conflict_exact_oracles', 'code/statistical_audit_round2_numeric/oracles.py'),
            module('conflict_friedman_oracle', 'code/statistical_analysis_v3_independent/outcome_checks.py'))


def stable_write(path, data):
    """A rerun may reproduce existing bytes, but may never replace a version."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = data.encode() if isinstance(data, str) else data
    if path.exists():
        assert path.read_bytes() == encoded, f'Preserve existing differing output: {path}'
    else:
        path.write_bytes(encoded)


def csv_bytes(rows):
    import io
    buf = io.StringIO(newline='')
    keys = list(dict.fromkeys(k for row in rows for k in row))
    writer = csv.DictWriter(buf, fieldnames=keys)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: json.dumps(v, separators=(',', ':'), sort_keys=True)
                         if isinstance(v, (list, dict, tuple)) else v for k, v in row.items()})
    return buf.getvalue().encode()


def mean(values):
    values = list(values)
    return sum(values, F()) / len(values) if values else None


def num(value):
    return float(value) if value is not None else None


def fraction(value):
    return str(value) if value is not None else None


def metric(row, name):
    if row['evaluated'] != 'True':
        return None
    if name == 'residue_rate' and row.get('condition') == 'RR':
        # RR has condition-specific full/any retention endpoints. Its residue
        # display field is deliberately unavailable in the canonical data.
        assert row[name] == ''
        return None
    if name == 'residue_rate':
        den = int(row['target_n'])
        v = F(int(row['RETAINED_count']) + int(row['PARTIAL_count']), den) if den else None
    elif name == 'restoration_rate':
        den = int(row['target_n'])
        v = F(int(row['RESTORED_count']), den) if den else None
    elif name == 'core_loss_rate':
        den = int(row['core_opportunities'])
        v = F(int(row['PF']), den) if den else None
    elif name in ('all_target_success', 'strict_target_success', 'any_core_loss', 'combined_success'):
        v = F(int(row[name])) if row[name] else None
    else:
        v = F(row[name]) if row[name] else None
    stored = row[name]
    assert (v is None) == (stored == ''), (row['session_id'], name)
    if v is not None:
        assert abs(float(v) - float(stored)) < 1e-12, (row['session_id'], name)
    return v


def selected_member(member, cohort, variant, phase_members):
    """Filters apply baseline membership only; no post-edit outcome selection."""
    if member['included'] != 'True':
        return False
    pid = member['participant_id']
    if variant == 'conflicts_only':
        return pid in EXPANDED
    if pid in EXPANDED:
        return False
    if variant == 'phase_i_no_conflict':
        return phase_members[pid]['included'] == 'True'
    return True


def build_views(session_rows, member_rows):
    mains = {c: [r for r in session_rows if r['view'] == c + '__main'] for c in COHORTS}
    mem = {(r['view'], r['participant_id']): r for r in member_rows}
    phase = {pid: r for (v, pid), r in mem.items() if v == 'alternative62__main'}
    old_index = {(r['view'], r['session_id']): r for r in session_rows}
    observations = []
    memberships = []
    deltas = []
    for cohort, variant in itertools.product(COHORTS, VARIANTS):
        view = cohort + '__expanded_' + variant
        prior = cohort + '__' + variant
        # Phase-I filter uses the saved original predicate-selected cases.
        source = 'alternative62' if variant == 'phase_i_no_conflict' else cohort
        source_rows = mains[source]
        keep = set()
        for pid in sorted(phase):
            base = mem[cohort + '__main', pid]
            yes = selected_member(base, cohort, variant, phase)
            src = phase[pid] if variant == 'phase_i_no_conflict' else base
            canonical_ids = json.loads(src['selected_case_ids'])
            if yes:
                keep.add(pid)
            original_yes = mem[prior, pid]['included'] == 'True'
            memberships.append(dict(view=view, cohort=cohort, variant='expanded_' + variant,
                original_conflict_view=prior, canonical_source_view=source + '__main',
                participant_id=pid, task=base['task'], group=base['group'], included=yes,
                included_original_conflict_view=original_yes,
                selected_case_ids=canonical_ids if yes else [], canonical_selected_case_ids=canonical_ids,
                known_conflict_original=pid in ORIGINAL, known_conflict_expanded=pid in EXPANDED,
                additional_S0069_conflict=pid == 'S0069', source_changed=base['source_changed'],
                core_baseline_passes=base['core_baseline_passes'],
                inclusion_reason=('expanded_conflict_member' if variant == 'conflicts_only' else
                                  'phase_i_predicate_and_no_expanded_flag' if variant == 'phase_i_no_conflict'
                                  else 'baseline_eligible_and_no_expanded_flag') if yes else
                                 ('expanded_conflict_excluded' if pid in EXPANDED and variant != 'conflicts_only'
                                  else 'outside_requested_baseline_subset')))
            if yes != original_yes:
                deltas.append(dict(view=view, original_view=prior, participant_id=pid,
                                   original_included=original_yes, expanded_included=yes))
        for r in source_rows:
            pid = r['participant_id']
            if pid not in keep:
                continue
            old = old_index.get((prior, r['session_id']))
            if old is not None:
                # Every retained old observation must be unchanged in all score fields.
                fields = set(r) - {'view', 'cohort', 'variant'}
                assert all(old[k] == r[k] for k in fields), (view, r['session_id'])
            else:
                assert variant == 'conflicts_only' and pid == 'S0069'
            x = dict(r)
            x.update(view=view, cohort=cohort, variant='expanded_' + variant,
                     canonical_source_view=source + '__main', original_conflict_view=prior,
                     known_conflict_original=pid in ORIGINAL, known_conflict_expanded=pid in EXPANDED,
                     additional_S0069_conflict=pid == 'S0069')
            observations.append(x)
        assert len([r for r in observations if r['view'] == view]) == len(keep) * 6
        assert all(d['participant_id'] == 'S0069' for d in deltas if d['view'] == view)
    return observations, memberships, deltas


def boot_pair(ds, key):
    if len(ds) < 2:
        return dict(ci_low=None, ci_high=None, ci_low_pp=None, ci_high_pp=None,
                    bootstrap_draws=0, bootstrap_seed_sha256='', bootstrap_seed_integer='',
                    bootstrap_degenerate=None, ci_status='insufficient_pairs')
    raw = json.dumps([SEED, 'bootstrap', *key], ensure_ascii=True, separators=(',', ':')).encode()
    digest = hashlib.sha256(raw).hexdigest()
    seed = int(digest[:16], 16)
    rng = np.random.Generator(np.random.PCG64(seed))
    a = np.array([float(x) for x in ds])
    samples = a[rng.integers(0, len(a), (BOOT, len(a)))].mean(axis=1)
    lo, hi = np.quantile(samples, [.025, .975], method='linear')
    degenerate = bool(np.all(samples == samples[0]))
    return dict(ci_low=float(lo), ci_high=float(hi), ci_low_pp=100*float(lo), ci_high_pp=100*float(hi),
                bootstrap_draws=BOOT, bootstrap_seed_sha256=digest, bootstrap_seed_integer=seed,
                bootstrap_degenerate=degenerate,
                ci_status='empirical_degenerate_not_equivalence' if degenerate else 'nominal_95_percentile')


def boot_groups(a, b, key):
    raw = json.dumps([SEED, *key, 'group_bootstrap'], ensure_ascii=True, separators=(',', ':')).encode()
    digest = hashlib.sha256(raw).hexdigest()
    seed = int(digest[:32], 16)
    rng = np.random.default_rng(seed)
    aa = np.array([float(x) for x in a]); bb = np.array([float(x) for x in b])
    ia = rng.integers(0, len(a), (BOOT, len(a)))
    ib = rng.integers(0, len(b), (BOOT, len(b)))
    samples = bb[ib].mean(axis=1) - aa[ia].mean(axis=1)
    lo, hi = np.quantile(samples, [.025, .975], method='linear')
    degenerate = bool(np.all(samples == samples[0]))
    return dict(ci_low=float(lo), ci_high=float(hi), ci_low_pp=100*float(lo), ci_high_pp=100*float(hi),
                bootstrap_draws=BOOT, bootstrap_seed_sha256=digest, bootstrap_seed_integer=seed,
                bootstrap_degenerate=degenerate,
                ci_status='empirical_degenerate_not_equivalence' if degenerate else 'nominal_95_percentile')


def adjust(rows, size, oracle):
    assert len(rows) == size
    raw = [F(r['exact_raw_fraction']) if r['exact_raw_fraction'] is not None else None for r in rows]
    for r, q in zip(rows, oracle.holm(raw)):
        r.update(family_size=size, exact_holm_p=num(q), exact_holm_fraction=fraction(q),
                 strict_p_lt_0_05=(q < F(1, 20)) if q is not None else None,
                 holm_policy='untestable_internal_one_full_family_reported_NA')


def paired_tests(rows, oracle, fried_oracle):
    results, supps, observations, fried, blocks_out = [], [], [], [], []
    pair_cache, mean_cache, fried_cache = {}, {}, {}
    index = {(r['view'], r['task'], r['provider'], r['participant_id'], r['condition']): r for r in rows}
    for view in sorted({r['view'] for r in rows}):
        view_pairs, view_means, view_fried = [], [], []
        for task, provider in itertools.product(TASKS, PROVIDERS):
            pids = sorted({r['participant_id'] for r in rows if r['view'] == view and r['task'] == task
                           and r['provider'] == provider})
            specs = [('residue_SA_EW', 'residue_rate', 'SA', 'EW'),
                     ('restoration_SA_EW', 'restoration_rate', 'SA', 'EW')] + [
                     ('core_3_contrasts', 'core_loss_rate', a, b) for a, b in CONTRASTS]
            for family, name, left, right in specs:
                valid, omitted = [], []
                for pid in pids:
                    a = metric(index[view, task, provider, pid, left], name)
                    b = metric(index[view, task, provider, pid, right], name)
                    if a is None or b is None:
                        omitted.append(pid)
                    else:
                        valid.append((pid, a, b))
                ds = [b-a for _, a, b in valid]
                status = 'insufficient_pairs' if len(ds) < 2 else 'no_variation' if not any(ds) else 'tested'
                cachekey = tuple(ds)
                p, rank, extreme, total = (None, None, 0, 0)
                mp, me, mt = (None, 0, 0)
                if status == 'tested':
                    if cachekey not in pair_cache:
                        pair_cache[cachekey] = oracle.signed_rank(ds)
                        mean_cache[cachekey] = oracle.mean_sign(ds)
                    p, rank, extreme, total = pair_cache[cachekey]
                    mp, me, mt = mean_cache[cachekey]
                delta = mean(ds)
                base = dict(view=view, task=task, provider=provider, family=family, metric=name,
                    contrast=right+' minus '+left, left_condition=left, right_condition=right,
                    n_planned=len(pids), n_pairs=len(valid), excluded_missing_or_undefined=len(omitted),
                    excluded_participants=omitted, participant_ids=[pid for pid, _, _ in valid],
                    left_mean=num(mean(a for _, a, _ in valid)), right_mean=num(mean(b for _, _, b in valid)),
                    difference=num(delta), difference_fraction=fraction(delta), difference_pp=num(delta*100) if delta is not None else None,
                    decreased=sum(x<0 for x in ds), increased=sum(x>0 for x in ds), tied=sum(x==0 for x in ds),
                    n_nonzero=sum(bool(x) for x in ds), status=status,
                    **boot_pair(ds, (view, task, provider, name, left, right)))
                view_pairs.append(dict(base, exact_raw_p=num(p), exact_raw_fraction=fraction(p),
                    signed_rank_sum=fraction(rank), exact_extreme=extreme if p is not None else None,
                    exact_assignments=total if p is not None else None,
                    exact_method='meet_in_the_middle_exact_conditional_signs' if p is not None else 'not_testable'))
                view_means.append(dict(base, exact_raw_p=num(mp), exact_raw_fraction=fraction(mp),
                    exact_extreme=me if mp is not None else None, exact_assignments=mt if mp is not None else None,
                    exact_method='meet_in_the_middle_exact_conditional_mean_signs' if mp is not None else 'not_testable'))
                for pid, a, b in valid:
                    observations.append(dict(view=view, task=task, provider=provider, family=family, metric=name,
                        contrast=right+' minus '+left, participant_id=pid,
                        group=index[view, task, provider, pid, left]['group'],
                        left_num=a.numerator, left_den=a.denominator, right_num=b.numerator, right_den=b.denominator,
                        difference_num=(b-a).numerator, difference_den=(b-a).denominator))
            blocks = []; omitted = []
            for pid in pids:
                values = tuple(metric(index[view, task, provider, pid, arm], 'core_loss_rate') for arm in ARMS)
                if any(v is None for v in values):
                    omitted.append(pid)
                else:
                    blocks.append(values)
                    blocks_out.append(dict(view=view, task=task, provider=provider, participant_id=pid,
                        **{arm+'_fraction':str(v) for arm, v in zip(ARMS, values)}))
            n = len(blocks)
            status = 'insufficient_complete_blocks' if n < 2 else 'no_within_program_variation' if all(len(set(b))==1 for b in blocks) else 'tested'
            p, q, e, total = None, None, 0, 0
            if status == 'tested':
                key = tuple(sorted(fried_oracle.row_rank_twice(b) for b in blocks))
                if key not in fried_cache:
                    fried_cache[key] = fried_oracle.friedman_exact(blocks)
                q, _, e, total = fried_cache[key]
                p = F(e, total)
            view_fried.append(dict(view=view, task=task, provider=provider, family='friedman_core', metric='core_loss_rate',
                conditions=list(ARMS), n_planned=len(pids), n_complete=n, excluded_participants=omitted,
                status=status, friedman_q=q, exact_raw_p=num(p), exact_raw_fraction=fraction(p),
                exact_extreme=e if p is not None else None, exact_assignments=total if p is not None else None,
                exact_method='exact_dynamic_counts_within_block_labels' if p is not None else 'not_testable'))
        for family, size in [('residue_SA_EW', 4), ('restoration_SA_EW', 4), ('core_3_contrasts', 12)]:
            adjust([r for r in view_pairs if r['family'] == family], size, oracle)
            adjust([r for r in view_means if r['family'] == family], size, oracle)
        adjust(view_fried, 4, oracle)
        results.extend(view_pairs); supps.extend(view_means); fried.extend(view_fried)
        print('Paired and Friedman finished:', view, flush=True)
    return results, supps, observations, fried, blocks_out


def group_tests(rows, oracle):
    results, samples_out = [], []
    cache = {}
    for view in sorted({r['view'] for r in rows}):
        rr = [r for r in rows if r['view'] == view]
        index = {(r['task'], r['provider'], r['participant_id'], r['condition']):r for r in rr}
        out = []
        for task, provider, context, name in itertools.product(TASKS, PROVIDERS,
                ('SA', 'EW', 'EW_minus_SA'), ('residue_rate', 'all_target_success', 'core_loss_rate')):
            samples = {g:[] for g in GROUPS}; planned = Counter()
            pids = sorted({r['participant_id'] for r in rr if r['task'] == task and r['provider'] == provider})
            for pid in pids:
                group = index[task, provider, pid, 'RR']['group']; planned[group] += 1
                if context == 'EW_minus_SA':
                    a = metric(index[task, provider, pid, 'SA'], name)
                    b = metric(index[task, provider, pid, 'EW'], name)
                    value = b-a if a is not None and b is not None else None
                else:
                    value = metric(index[task, provider, pid, context], name)
                if value is not None:
                    samples[group].append((pid, value))
                    samples_out.append(dict(view=view, task=task, provider=provider, context=context, metric=name,
                        group=group, participant_id=pid, value_num=value.numerator, value_den=value.denominator))
            for left, right in itertools.combinations(GROUPS, 2):
                aa, bb = samples[left], samples[right]
                a, b = [v for _,v in aa], [v for _,v in bb]
                lm, rm = mean(a), mean(b); d = rm-lm if lm is not None and rm is not None else None
                status = ('unassessable_empty_group' if not a or not b else
                          'descriptive_only_fewer_than_two_per_group' if min(len(a),len(b)) < 2 else
                          'no_informative_variation_in_pooled_values' if len(set(a+b)) == 1 else 'tested')
                p, e, total = None, 0, 0
                ci = dict(ci_low=None, ci_high=None, ci_low_pp=None, ci_high_pp=None, bootstrap_draws=0,
                          bootstrap_seed_sha256='', bootstrap_seed_integer='', bootstrap_degenerate=None,
                          ci_status=status)
                if status == 'tested':
                    ck = min((tuple(sorted(a)), tuple(sorted(b))), (tuple(sorted(b)), tuple(sorted(a))))
                    if ck not in cache:
                        cache[ck] = oracle.group_exact(a, b)
                    p, e, total = cache[ck]
                    ci = boot_groups(a, b, (view, task, provider, context, name, left, right))
                out.append(dict(view=view, task=task, provider=provider, family='specification_groups', context=context,
                    metric=name, source_metric=name, group_left=left, group_right=right,
                    contrast=right+' minus '+left, planned_left=planned[left], planned_right=planned[right],
                    n_left=len(a), n_right=len(b), missing_left=planned[left]-len(a), missing_right=planned[right]-len(b),
                    left_ids=[pid for pid,_ in aa], right_ids=[pid for pid,_ in bb],
                    left_mean=num(lm), right_mean=num(rm), difference=num(d), difference_fraction=fraction(d),
                    difference_pp=num(d*100) if d is not None else None, status=status,
                    exact_raw_p=num(p), exact_raw_fraction=fraction(p), exact_extreme=e if p is not None else None,
                    exact_assignments=total if p is not None else None,
                    exact_method='meet_in_the_middle_exact_group_labels' if p is not None else 'not_testable', **ci))
        adjust(out, 108, oracle)
        results.extend(out)
        print('Groups finished:', view, flush=True)
    return results, samples_out


def summaries(rows, grouped=False):
    out = []
    numeric_fields = ('residue_rate','restoration_rate','persistence_rate','target_rate','all_target_success',
        'strict_target_rate','strict_target_success','core_loss_rate','core_loss_count','core_gains',
        'core_absolute_passes','any_core_loss','combined_success','other_rate','inconclusive_rate','invalid_error_rate',
        'PP_fraction','PF_fraction','FP_fraction','FF_fraction')
    for view, task, provider, condition in itertools.product(sorted({r['view'] for r in rows}), TASKS, PROVIDERS, ARMS):
        for group in GROUPS if grouped else (None,):
            rr = [r for r in rows if r['view']==view and r['task']==task and r['provider']==provider
                  and r['condition']==condition and (group is None or r['group']==group)]
            observed = [r for r in rr if r['evaluated']=='True']
            x = dict(view=view, task=task, provider=provider, condition=condition, programs=len(rr),
                     evaluated=len(observed), missing=len(rr)-len(observed),
                     assessment='observed' if observed else 'empty_population' if not rr else 'no_evaluations')
            if grouped:
                x['group']=group
            for field in ('target_n','target_observed','target_met','core_opportunities','core_loss_count','core_gains',
                          'controls_bad','controls_unknown','PP','PF','FP','FF',*(label+'_count' for label in LABELS)):
                source = rr if field=='target_n' else observed
                x[field+'_sum'] = sum(int(r[field]) for r in source if r[field])
            for field in numeric_fields:
                values = [metric(r,field) for r in observed]
                values = [v for v in values if v is not None]
                x[field+'_n']=len(values); x[field+'_mean']=num(mean(values))
                x[field+'_min']=num(min(values)) if values else None; x[field+'_max']=num(max(values)) if values else None
                if field in ('all_target_success','strict_target_success','any_core_loss','combined_success'):
                    x[field+'_count']=sum(values,F()) if values else None
            x['pooled_core_loss_rate'] = x['PF_sum']/x['core_opportunities_sum'] if x['core_opportunities_sum'] else None
            assert sum(x[k+'_sum'] for k in ('PP','PF','FP','FF')) == 28*len(observed)
            assert sum(x[lab+'_count_sum'] for lab in LABELS) == x['target_observed_sum']
            out.append(x)
    return out


def evidence(rows):
    targets = read(TABLES/'raw_target_outcomes.csv'); tests = read(TABLES/'raw_test_outcomes.csv')
    by_target = defaultdict(list); by_test = defaultdict(list)
    for r in targets: by_target[r['session_id']].append(r)
    for r in tests: by_test[r['session_id']].append(r)
    target_out, test_out, pertest, aux = [], [], defaultdict(Counter), defaultdict(Counter)
    sources = {}
    for r in rows:
        sid = r['session_id']; view = r['view']; ids = set(json.loads(r['selected_case_ids']))
        selected = [x for x in by_target[sid] if x['case_id'] in ids]
        if r['evaluated']=='True':
            assert len(selected)==int(r['target_n'])
            assert Counter(x['outcome'] for x in selected) == Counter({lab:int(r[lab+'_count']) for lab in LABELS if int(r[lab+'_count'])})
        for x in selected:
            assert x['grade_path']==r['grade_path']
            target_out.append(dict(x, view=view, known_conflict_expanded=r['known_conflict_expanded']))
            sources[x['grade_path']]=x['grade_sha256']
        core = [x for x in by_test[sid] if x['suite']=='core28']
        if r['evaluated']=='True':
            assert len(core)==28
            assert Counter(x['transition'] for x in core)==Counter({k:int(r[k]) for k in ('PP','PF','FP','FF') if int(r[k])})
        for x in by_test[sid]:
            assert x['grade_path']==r['grade_path']
            test_out.append(dict(x,view=view,known_conflict_expanded=r['known_conflict_expanded']))
            sources[x['grade_path']]=x['grade_sha256']
            if x['suite']=='core28':
                counts=pertest[view,x['task'],x['provider'],x['condition'],x['test_id']]
                counts[x['transition']]+=1;counts['observed']+=1;counts['revision_'+x['revision_status']]+=1
            else:
                counts=aux[view,x['task'],x['provider'],x['condition'],x['test_id']]
                counts[x['revision_status']]+=1;counts['observed']+=1
    for path, expected in sources.items():
        assert sha(ROOT/path)==expected, path
    aggregate=[]
    for key,c in sorted(pertest.items()):
        aggregate.append(dict(zip(('view','task','provider','condition','test_id'),key),**{k:c[k] for k in ('observed','PP','PF','FP','FF','revision_passed','revision_failed','revision_error','revision_skipped')}))
    aux_out=[]
    for key,c in sorted(aux.items()):
        aux_out.append(dict(zip(('view','task','provider','condition','test_id'),key),**{k:c[k] for k in ('observed','passed','failed','error','skipped')}))
    return target_out,test_out,aggregate,aux_out,sources


def comparisons(paired, groups):
    old_pairs=read(ROOT/'reports/statistical_analysis_v3/paired/paired_wilcoxon.csv')
    exact_pairs=read(ROOT/'reports/statistical_analysis_v3/verification/all_views_exact_v1/paired_all_views_exact.csv')
    old_groups=read(ROOT/'reports/statistical_analysis_v3/groups/group_tests.csv')
    exact_groups=read(ROOT/'reports/statistical_analysis_v3/verification/all_views_exact_v1/group_all_views_exact.csv')
    pk=lambda r:(r['view'],r['task'],r['provider'],r['metric'],r['contrast'])
    gk=lambda r:(r['view'],r['task'],r['provider'],r['context'],r['metric'],r['group_left'],r['group_right'])
    pi={pk(r):r for r in old_pairs};pe={pk(r):r for r in exact_pairs}
    gi={gk(r):r for r in old_groups};ge={gk(r):r for r in exact_groups}
    out=[]
    for kind, records, idx, ei, keyfunc in [('paired',paired,pi,pe,pk),('groups',groups,gi,ge,gk)]:
        for r in records:
            cohort, variant=r['view'].split('__expanded_')
            for scope,oldview in [('original_conflict_view',cohort+'__'+variant),('canonical_main',cohort+'__main')]:
                key=(oldview,*keyfunc(r)[1:]);old=idx[key];ex=ei[key]
                olddiff=F(old['difference']) if old['difference'] else None
                newdiff=F(r['difference_fraction']) if r['difference_fraction'] is not None else None
                out.append(dict(kind=kind,view=r['view'],comparison_scope=scope,compared_view=oldview,
                    task=r['task'],provider=r['provider'],metric=r['metric'],contrast=r['contrast'],
                    context=r.get('context',''),group_left=r.get('group_left',''),group_right=r.get('group_right',''),
                    old_n_pairs=old.get('n_pairs',''),new_n_pairs=r.get('n_pairs',''),
                    old_n_left=old.get('n_left',''),new_n_left=r.get('n_left',''),
                    old_n_right=old.get('n_right',''),new_n_right=r.get('n_right',''),
                    old_difference_pp=100*float(olddiff) if olddiff is not None else None,new_difference_pp=r['difference_pp'],
                    difference_change_pp=100*float(newdiff-olddiff) if newdiff is not None and olddiff is not None else None,
                    old_exact_raw_p=ex['exact_raw_p'],old_exact_holm_p=ex['exact_holm_p'],
                    new_exact_raw_p=r['exact_raw_p'],new_exact_holm_p=r['exact_holm_p'],
                    old_status=old['status'],new_status=r['status']))
    return out


def alias_checks(tables, rows):
    signatures={}
    for view in sorted({r['view'] for r in rows}):
        # Includes program identities and selected evidence, excludes only view names.
        signatures[view]=tuple(sorted((r['session_id'],r['selected_case_ids'],r['grade_path']) for r in rows if r['view']==view))
    aliases=[]
    for left,right in itertools.combinations(sorted(signatures),2):
        if signatures[left]!=signatures[right]:continue
        for name in ('paired_wilcoxon.csv','paired_mean_sign.csv','friedman.csv','group_tests.csv'):
            fields=lambda r:(r['task'],r['provider'],r.get('family'),r.get('metric'),r.get('contrast'),r.get('context'),r.get('group_left'),r.get('group_right'))
            a={fields(r):r for r in tables[name] if r['view']==left};b={fields(r):r for r in tables[name] if r['view']==right}
            assert set(a)==set(b)
            assert all(a[k]['exact_raw_fraction']==b[k]['exact_raw_fraction'] and
                       a[k]['exact_holm_fraction']==b[k]['exact_holm_fraction'] for k in a)
        aliases.append(dict(left=left,right=right,exact_raw_and_holm_equal=True))
    return aliases


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=DEFAULT_OUT);args=parser.parse_args()
    out=args.out.resolve();assert out==DEFAULT_OUT or DEFAULT_OUT in out.parents
    policy=json.loads(POLICY.read_text());assert policy['status']=='FROZEN BEFORE NEW SUBSET CALCULATION'
    for path, expected in policy['source_sha256'].items():
        # The saved data and recalculated statistics must match the design record.
        if not path.startswith('code/'):
            assert sha(ROOT/path)==expected,path
    original_rows=read(TABLES/'session_metrics.csv'); members=read(TABLES/'membership.csv')
    rows,membership,deltas=build_views(original_rows,members)
    oracle,fried_oracle=helpers()
    # Audited synthetic input checks precede new real-outcome inference.
    assert oracle.signed_rank([F(1),F(1),F(0)])[0]==F(1,2)
    assert oracle.group_exact([F(0),F(0)],[F(1),F(1)])[0]==F(1,3)
    assert oracle.holm([F(1,100),None,F(1,10)])==[F(3,100),None,F(1,5)]
    assert metric({'evaluated':'False'},'core_loss_rate') is None
    target_evidence,test_evidence,per_core,aux,grade_hashes=evidence(rows)
    paired,mean_sign,pair_observations,friedman,blocks=paired_tests(rows,oracle,fried_oracle)
    groups,group_samples=group_tests(rows,oracle)
    tables={'membership.csv':membership,'membership_changes.csv':deltas,'session_metrics.csv':rows,
            'arm_summary.csv':summaries(rows),'group_summary.csv':summaries(rows,True),
            'target_outcomes.csv':target_evidence,'test_outcomes.csv':test_evidence,
            'per_core_test.csv':per_core,'original_five_diagnostics.csv':aux,
            'paired_wilcoxon.csv':paired,'paired_mean_sign.csv':mean_sign,'paired_observations.csv':pair_observations,
            'friedman.csv':friedman,'friedman_blocks.csv':blocks,'group_tests.csv':groups,'group_samples.csv':group_samples,
            'comparison_to_original.csv':comparisons(paired,groups)}
    family_registry=[]
    for method,rr in [('wilcoxon',paired),('supplementary_mean_sign',mean_sign),('friedman',friedman),('group',groups)]:
        for r in rr:
            family_registry.append({k:r.get(k) for k in ('view','family','family_size','task','provider','metric','context',
                'contrast','group_left','group_right','status','exact_raw_p','exact_raw_fraction','exact_holm_p','exact_holm_fraction') } | {'method':method})
    tables['family_slot_registry.csv']=family_registry
    aliases=alias_checks(tables,rows)
    for name,tab in tables.items():
        if name not in {'test_outcomes.csv','target_outcomes.csv','family_slot_registry.csv'}:
            stable_write(out/'tables'/name,csv_bytes(tab))
