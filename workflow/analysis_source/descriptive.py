"""Descriptive reanalysis of saved grades. No submission execution or inference."""
from __future__ import annotations
import csv
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/full_analysis_v2_prelim'
PLAN = 'planning/ANALYSIS_PLAN_v2_PRESTAT.md'
PLAN_SHA = 'abf7fa160883376f0b74a35f85433522e7474a3b76142bb2ac33a6fb01afa416'
EXTENSION_ID = 'S0033_SA_openai_r1'
CONFLICTS = {'S0034','S0041','S0049','S0053','S0058','S0060','S0046'}
LABELS = ('RESTORED','RETAINED','PARTIAL','OTHER_FAILURE','INDETERMINATE')
ARMS = ('RR','SA','EW')
PROVIDERS = ('anthropic','openai')
GROUPS = ('G1','G2','G3')
FILTERS = ('main','original_limit','exclude_conflicts','conflicts_only',
           'exclude_cleaned','cleaned_only','drop_duplicate_friday',
           'strict_controls','phase_i_format','phase_i_no_conflict','phase_i_all_targets')
METRICS = ('residue_rate','restoration_rate','persistence_rate','target_rate',
           'reported_target_rate','all_target_success','strict_target_rate',
           'strict_target_success','core_loss_rate','core_loss_count','core_gains',
           'core_absolute_passes','any_core_loss','combined_success',
           'other_rate','inconclusive_rate','invalid_error_rate',
           'PP_fraction','PF_fraction','FP_fraction','FF_fraction')
RATE_METRICS = {'residue_rate','restoration_rate','persistence_rate','target_rate',
                'reported_target_rate','all_target_success','strict_target_rate',
                'strict_target_success','core_loss_rate','any_core_loss','combined_success',
                'other_rate','inconclusive_rate','invalid_error_rate',
                'PP_fraction','PF_fraction','FP_fraction','FF_fraction'}
INPUTS = {}


def digest(data): return hashlib.sha256(data).hexdigest()


def read(rel, expected=None):
    data = (ROOT / rel).read_bytes()
    found = digest(data)
    if expected is not None and found != expected:
        raise ValueError(f'Hash mismatch: {rel}')
    INPUTS[str(rel)] = found
    return json.loads(data)


def write(name, rows):
    path = OUT / 'tables' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f'Unexpected empty whole table: {name}')
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', newline='') as stream:
        w = csv.DictWriter(stream, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v,(dict,list)) else v
                        for k,v in r.items()})


def transition(before, after):
    return ('P' if before == 'passed' else 'F') + ('P' if after == 'passed' else 'F')


def validate_grade(e, session, base):
    score=e['score']; obs=e['observations']
    for key in ('session_id','participant_id','task','group','provider','condition'):
        expected=session[key] if key!='participant_id' else base[key]
        assert score[key] == expected, (session['session_id'],key)
        assert e['identity'][key] == expected
        if key!='session_id': assert obs[key] == expected
    assert score['baseline_source_sha256'] == base['starting_source_sha256']
    assert obs['source_sha256'] == e['binding']['final_source_sha256']
    assert obs['evaluation_complete'] and score['core_preservation']['complete']
    assert obs['core28']['complete'] and len(obs['core28']['results']) == 28
    assert obs['supplied5']['complete'] and len(obs['supplied5']['results']) == 5
    bp=set(base['core_baseline_pass_ids'])
    revised={t:v[0] for t,v in obs['core28']['results'].items()}
    assert set(revised)==set(score['core_preservation']['revision_suite']['outcomes'])
    assert revised==score['core_preservation']['revision_suite']['outcomes']
    losses=sorted(t for t in bp if revised[t]!='passed')
    assert losses==sorted(score['core_preservation']['known_observed_loss_ids'])
    assert len(losses)==score['core_preservation']['loss_count']
    assert len(bp)==score['core_preservation']['opportunity_count']
    assert sum(v=='passed' for v in revised.values())==score['core_preservation']['revision_suite']['passed_count']
    cases=score['withdrawal']['case_results']
    assert {c['case_id'] for c in cases}==set(base['eligible_case_ids'])
    assert all(c['status'] in LABELS for c in cases)
    assert not base['eligible_case_ids'] or score['withdrawal']['complete']
    expected='RETAINED' if session['condition']=='RR' else 'RESTORED'
    assert score['withdrawal']['expected_status']==expected
    assert sum(c['status']==expected for c in cases)==score['withdrawal']['met_count']


def load():
    assert digest((ROOT/PLAN).read_bytes())==PLAN_SHA
    INPUTS[PLAN]=PLAN_SHA
    clarification='planning/ANALYSIS_PLAN_v2_PRESTAT_CLARIFICATIONS.md'
    INPUTS[clarification]=digest((ROOT/clarification).read_bytes())
    frozen=read('planning/ANALYSIS_PLAN_v2_PRESTAT_FREEZE.json')
    assert frozen['sha256']==PLAN_SHA and frozen['statistical_tests_authorized_now'] is False
    old=read('reports/full_analysis_v1/tables/analysis_manifest.json')
    expected=old['inputs']
    audit_path='reports/cleaned_continuation_v1/LIVE_AUDIT.json'
    audit=read(audit_path,expected[audit_path])
    baseline_path='runs/cleaned_starts_v1/baseline_manifest.json'
    baseline=read(baseline_path,expected[baseline_path])
    bases={r['participant_id']:r for r in baseline['records']}
    assert len(bases)==72
    baselines={}
    for pid,b in bases.items():
        raw=read(b['baseline_path'],b['baseline_sha256'])
        assert raw['participant_id']==pid and raw['source_sha256']==b['starting_source_sha256']
        assert raw['evaluation_complete']
        assert {t for t,v in raw['core28']['results'].items() if v[0]=='passed'}==set(b['core_baseline_pass_ids'])
        assert len(raw['core28']['results'])==28 and len(raw['supplied5']['results'])==5
        baselines[pid]=raw
    original={}; complete={}; sessions={}
    for s0 in audit['sessions']:
        sid=s0['session_id']; pid=sid.split('_')[0]; b=bases[pid]
        s=dict(s0,participant_id=pid)
        assert sid not in sessions
        for k in ('task','group'):assert s[k]==b[k]
        sessions[sid]=s
        rel=f"runs/cleaned_{s['phase']}_v1/elmira-cleaned-{s['phase']}-20261105-v1/sessions/{sid}/evaluation.json"
        if s['evaluation_status']=='evaluated':
            e=read(rel,expected[rel]);validate_grade(e,s,b)
            original[sid]=e;complete[sid]=e
        else:
            assert sid==EXTENSION_ID
            original[sid]=None
    ext_path=f'runs/turn_extension_v1/elmira-s0033-turn-extension-20261105-v1/sessions/{EXTENSION_ID}/evaluation.json'
    ext=read(ext_path,expected[ext_path]);validate_grade(ext,sessions[EXTENSION_ID],bases['S0033'])
    complete[EXTENSION_ID]=ext
    assert len(sessions)==432 and len(complete)==432 and sum(x is not None for x in original.values())==431
    assert len({(s['participant_id'],s['provider'],s['condition']) for s in sessions.values()})==432
    # Verify the saved final source, without executing it, for all 432 complete grades.
    slots={(x['participant_id'],x['provider'],x['condition']) for x in sessions.values()}
    for sid,session in sessions.items():
        pid=session['participant_id']
        assert all((pid,pr,c) in slots for pr in PROVIDERS for c in ARMS)
        final=Path(grade_path(session,'main')).with_name('final.py')
        actual=digest((ROOT/final).read_bytes());INPUTS[str(final)]=actual
        assert actual==complete[sid]['binding']['final_source_sha256']
        session['complete_reported_usage_usd']=session['known_reported_usage_usd']
    original_final=Path(grade_path(sessions[EXTENSION_ID],'original_limit')).with_name('final.py')
    oldsha=digest((ROOT/original_final).read_bytes());INPUTS[str(original_final)]=oldsha
    assert oldsha==ext['binding']['final_source_sha256']
    extension_result=read(str(Path(ext_path).with_name('result.json')))
    assert extension_result['model_turns']==9 and extension_result['usage_complete']
    assert extension_result['final_source_sha256']==oldsha
    sessions[EXTENSION_ID]['complete_reported_usage_usd']=extension_result['reported_cost_usd']
    return sessions,bases,baselines,original,complete


def selected_ids(base, cohort, variant):
    ids=list(base['eligible_case_ids'])
    predicates=base['original_phase_i_predicates']
    if cohort=='alternative62' or variant in ('phase_i_format','phase_i_no_conflict'):
        ids=[i for i in ids if predicates.get(i,{}).get('restored') is True]
    if variant=='phase_i_format':
        ids=[i for i in ids if predicates[i].get('original_return_format_valid') is True]
    if variant=='drop_duplicate_friday' and base['task']=='A' and base['source_changed']:
        ids=[i for i in ids if i!='A-F4']
    return ids


def included(base,cohort,variant):
    ids=selected_ids(base,cohort,variant)
    if cohort!='all72_preservation' and not ids:return False
    if variant in ('exclude_conflicts','phase_i_no_conflict') and base['participant_id'] in CONFLICTS:return False
    if variant=='conflicts_only' and base['participant_id'] not in CONFLICTS:return False
    if variant=='exclude_cleaned' and base['source_changed']:return False
    if variant=='cleaned_only' and not base['source_changed']:return False
    if variant=='phase_i_all_targets' and (not base['eligible_case_ids'] or not all(
        base['original_phase_i_predicates'][i]['restored'] for i in base['eligible_case_ids'])):return False
    return True


def metrics(s,base,e,ids,variant):
    row={k:s[k] for k in ('session_id','participant_id','task','group','provider','condition')}
    row.update(original_session_status=s['session_status'],
               original_accepted_requests=s['requests']['accepted'],
               original_reported_usage_usd=s['known_reported_usage_usd'],
               selected_session_reported_usage_usd=(s['known_reported_usage_usd'] if variant=='original_limit' else s.get('complete_reported_usage_usd',s['known_reported_usage_usd'])),
               model=(e['identity']['model'] if e else ('gpt-6.1-sol' if s['provider']=='openai' else 'claude-sonnet-5-5')),
               source_changed=base['source_changed'],known_conflict=base['participant_id'] in CONFLICTS,
               source_sha256=base['starting_source_sha256'],evaluated=e is not None,
               used_extra_turn=e is not None and s['session_id']==EXTENSION_ID,
               selected_case_ids=ids,target_n=len(ids),target_observed=len(ids) if e else 0,
               grade_path='' if e is None else grade_path(s,variant),
               missing_reason='original_eight_turn_limit_no_grade' if e is None else '')
    for key in METRICS:row[key]=None
    for lab in LABELS:row[lab+'_count']=None if e is None else 0
    row.update(core_opportunities=None,controls_bad=None,controls_unknown=None,
               target_met=None,PP=None,PF=None,FP=None,FF=None)
    if e is None:return row
    cases=[c for c in e['score']['withdrawal']['case_results'] if c['case_id'] in ids]
    assert len(cases)==len(ids)
    counts=Counter(c['status'] for c in cases)
    row.update({lab+'_count':counts[lab] for lab in LABELS})
    n=len(ids);expected='RETAINED' if s['condition']=='RR' else 'RESTORED'
    met=sum(c['status']==expected for c in cases)
    strict=sum(c['status']==expected and c.get('controls_ok') is True for c in cases)
    row.update(target_met=met,controls_bad=sum(c.get('controls_ok') is False for c in cases),
               controls_unknown=sum(c.get('controls_ok') is None for c in cases))
    if n:
        row.update(persistence_rate=(counts['RETAINED']+counts['PARTIAL'])/n,
                   restoration_rate=counts['RESTORED']/n,target_rate=met/n,
                   reported_target_rate=(strict if variant=='strict_controls' else met)/n,
                   all_target_success=int(met==n),strict_target_rate=strict/n,
                   strict_target_success=int(strict==n),
                   other_rate=(counts['OTHER_FAILURE']+counts['INDETERMINATE'])/n,
                   inconclusive_rate=counts['INDETERMINATE']/n,invalid_error_rate=counts['OTHER_FAILURE']/n)
        if s['condition']!='RR':row['residue_rate']=row['persistence_rate']
    outcomes={t:v[0] for t,v in e['observations']['core28']['results'].items()}
    bp=set(base['core_baseline_pass_ids'])
    transitions=Counter(('P' if t in bp else 'F')+('P' if v=='passed' else 'F') for t,v in outcomes.items())
    assert sum(transitions.values())==28
    row.update({k:transitions[k] for k in ('PP','PF','FP','FF')})
    row.update({k+'_fraction':transitions[k]/28 for k in ('PP','PF','FP','FF')})
    opp=transitions['PP']+transitions['PF']
    row.update(core_opportunities=opp,core_loss_count=transitions['PF'],core_gains=transitions['FP'],
               core_absolute_passes=transitions['PP']+transitions['FP'])
    if opp:
        row.update(core_loss_rate=transitions['PF']/opp,any_core_loss=int(transitions['PF']>0))
        if n:row['combined_success']=int(met==n and transitions['PF']==0)
    return row


def grade_path(s,variant):
    sid=s['session_id']
    if sid==EXTENSION_ID and variant!='original_limit':
        return f'runs/turn_extension_v1/elmira-s0033-turn-extension-20261105-v1/sessions/{sid}/evaluation.json'
    return f"runs/cleaned_{s['phase']}_v1/elmira-cleaned-{s['phase']}-20261105-v1/sessions/{sid}/evaluation.json"


def view_rows(sessions,bases,original,complete):
    allrows=[];members=[]
    configs=[(c,v) for c in ('primary69','alternative62') for v in FILTERS]+[
        ('all72_preservation','main'),('all72_preservation','original_limit')]
    for cohort,variant in configs:
        view=cohort+'__'+variant
        for pid,b in sorted(bases.items()):
            ids=selected_ids(b,cohort,variant);yes=included(b,cohort,variant)
            members.append(dict(view=view,cohort=cohort,variant=variant,participant_id=pid,task=b['task'],group=b['group'],
                                included=yes,selected_case_ids=ids if yes else [],source_changed=b['source_changed'],
                                core_baseline_passes=len(b['core_baseline_pass_ids']),
                                known_conflict=pid in CONFLICTS))
        for sid,s in sorted(sessions.items()):
            b=bases[s['participant_id']]
            if not included(b,cohort,variant):continue
            e=(original if variant=='original_limit' else complete)[sid]
            row=metrics(s,b,e,selected_ids(b,cohort,variant),variant)
            row.update(view=view,cohort=cohort,variant=variant)
            allrows.append(row)
    return allrows,members


def summary(rows,group=False):
    out=[];keynames=['view','cohort','variant','task','provider','condition']+(['group'] if group else [])
    by=defaultdict(list)
    # Explicit empty groups are written and marked unassessable.
    byview={r['view']:(r['cohort'],r['variant']) for r in rows}
    for view,(cohort,variant) in byview.items():
        for task,provider,condition in itertools.product(('A','B'),PROVIDERS,ARMS):
            for g in (GROUPS if group else (None,)):
                key=(view,cohort,variant,task,provider,condition)+((g,) if group else ())
                by[key]=[]
    for r in rows:by[tuple(r[k] for k in keynames)].append(r)
    for key,rr in sorted(by.items()):
        x=dict(zip(keynames,key));evaluated=[r for r in rr if r['evaluated']]
        x.update(programs=len(rr),evaluated=len(evaluated),missing=len(rr)-len(evaluated),
                 assessment='observed' if evaluated else ('no_evaluations' if rr else 'empty_population'),
                 target_cases_planned=sum(r['target_n'] for r in rr),
                 target_cases_observed=sum(r['target_observed'] for r in evaluated),
                 target_cases_met=sum(r['target_met'] for r in evaluated),
                 core_opportunities=sum(r['core_opportunities'] for r in evaluated),
                 core_losses=sum(r['core_loss_count'] for r in evaluated),
                 core_gains=sum(r['core_gains'] for r in evaluated),
                 linked_controls_bad=sum(r['controls_bad'] for r in evaluated),
                 linked_controls_unknown=sum(r['controls_unknown'] for r in evaluated))
        for lab in LABELS:x[lab+'_count']=sum(r[lab+'_count'] for r in evaluated)
        for k in ('PP','PF','FP','FF'):x[k+'_count']=sum(r[k] for r in evaluated)
        for m in METRICS:
            a=[r[m] for r in rr if r[m] is not None]
            x[m+'_n']=len(a);x[m+'_mean']=mean(a) if a else None
            if m in ('all_target_success','strict_target_success','any_core_loss','combined_success'):x[m+'_count']=sum(a) if a else None
            x[m+'_median']=median(a) if a else None
            x[m+'_min']=min(a) if a else None;x[m+'_max']=max(a) if a else None
        x['pooled_core_loss_rate']=x['core_losses']/x['core_opportunities'] if x['core_opportunities'] else None
        out.append(x)
    return out


def descriptive_contrasts(rows,provider_comparison=False):
    detail=[];summ=[]
    byview=defaultdict(list)
    for r in rows:byview[r['view']].append(r)
    contexts=ARMS if provider_comparison else PROVIDERS
    for view,rr in sorted(byview.items()):
        for task,ctx in itertools.product(('A','B'),contexts):
            candidates=[r for r in rr if r['task']==task and r['condition' if provider_comparison else 'provider']==ctx]
            axis='provider' if provider_comparison else 'condition'
            by={(r['participant_id'],r[axis]):r for r in candidates}
            comparisons=[('anthropic','openai')] if provider_comparison else [('SA','EW'),('RR','SA'),('RR','EW')]
            for left,right in comparisons:
                for metric in METRICS:
                    pp=[]
                    for pid in sorted({r['participant_id'] for r in candidates}):
                        a=by.get((pid,left));b=by.get((pid,right))
                        if a and b and a[metric] is not None and b[metric] is not None:
                            delta=b[metric]-a[metric]
                            common=dict(view=view,task=task,context=ctx,axis=axis,contrast=right+' minus '+left,
                                        metric=metric,participant_id=pid,group=a['group'],left=a[metric],right=b[metric],
                                        difference=delta,known_conflict=a['known_conflict'],source_changed=a['source_changed'])
                            if metric in RATE_METRICS:common['difference_percentage_points']=100*delta
                            detail.append(common);pp.append(common)
                    x=dict(view=view,task=task,context=ctx,axis=axis,contrast=right+' minus '+left,metric=metric,
                           n_pairs=len(pp),assessment='observed' if pp else 'no_assessable_pairs',
                           left_mean=mean(p['left'] for p in pp) if pp else None,
                           right_mean=mean(p['right'] for p in pp) if pp else None,
                           difference=mean(p['difference'] for p in pp) if pp else None,
                           decreased=sum(p['difference'] < -1e-12 for p in pp),
                           increased=sum(p['difference'] > 1e-12 for p in pp),
                           tied=sum(abs(p['difference']) <= 1e-12 for p in pp))
                    if metric in RATE_METRICS:x['difference_percentage_points']=100*x['difference'] if pp else None
                    summ.append(x)
    return detail,summ


def group_contrasts(rows):
    out=[]
    byview=defaultdict(list)
    for r in rows:byview[r['view']].append(r)
    for view,rr in sorted(byview.items()):
        for task,provider,context,metric in itertools.product(('A','B'),PROVIDERS,('SA','EW','EW_minus_SA'),
                                                             ('residue_rate','all_target_success','core_loss_rate')):
            by={(r['participant_id'],r['condition']):r for r in rr if r['task']==task and r['provider']==provider}
            vals={g:[] for g in GROUPS}
            for pid in sorted({p for p,c in by}):
                if context=='EW_minus_SA':
                    a=by[pid,'SA'][metric];b=by[pid,'EW'][metric]
                    v=b-a if a is not None and b is not None else None
                else:v=by[pid,context][metric]
                if v is not None:vals[by[pid,'RR']['group']].append(v)
            for left,right in itertools.combinations(GROUPS,2):
                a=vals[left];b=vals[right];delta=mean(b)-mean(a) if a and b else None
                out.append(dict(view=view,task=task,provider=provider,context=context,metric=metric,
                                contrast=right+' minus '+left,n_left=len(a),n_right=len(b),
                                left_mean=mean(a) if a else None,right_mean=mean(b) if b else None,
                                difference=delta,difference_percentage_points=100*delta if delta is not None else None,
                                assessment='observed' if delta is not None else 'empty_group'))
    return out


def raw_tables(sessions,bases,baselines,complete):
    tests=[];targets=[];baseline_tests=[]
    for pid,b in sorted(bases.items()):
        for suite in ('core28','supplied5'):
            for test_id,outcome in sorted(baselines[pid][suite]['results'].items()):
                baseline_tests.append(dict(participant_id=pid,task=b['task'],group=b['group'],suite=suite,
                                           test_id=test_id,baseline_status=outcome[0],baseline_path=b['baseline_path'],
                                           baseline_sha256=b['baseline_sha256']))
    for sid,s in sorted(sessions.items()):
        e=complete[sid];base=bases[s['participant_id']]
        identity={k:s[k] for k in ('session_id','participant_id','task','group','provider','condition')}
        identity.update(used_extra_turn=sid==EXTENSION_ID,grade_path=grade_path(s,'main'),
                        grade_sha256=INPUTS[grade_path(s,'main')],final_source_sha256=e['binding']['final_source_sha256'])
        for suite in ('core28','supplied5'):
            for test_id,outcome in sorted(e['observations'][suite]['results'].items()):
                before=baselines[s['participant_id']][suite]['results'][test_id][0]
                tests.append(dict(identity,suite=suite,test_id=test_id,baseline_status=before,
                                  revision_status=outcome[0],transition=transition(before,outcome[0])))
        for c in e['score']['withdrawal']['case_results']:
            cid=c['case_id'];p1=base['original_phase_i_predicates'].get(cid,{})
            targets.append(dict(identity,case_id=cid,outcome=c['status'],controls_ok=c.get('controls_ok'),
                                morning_ok=c.get('morning_ok'),reason=c.get('reason',''),
                                target_present=c.get('target_present'),target_absent=c.get('target_absent'),
                                original_phase_i_case_id=base['original_phase_i_case_mapping'].get(cid),
                                phase_i_predicate=p1.get('restored'),phase_i_format_valid=p1.get('original_return_format_valid')))
    return tests,targets,baseline_tests


def bounds(rows):
    missing=[];attribution=[]
    byview=defaultdict(list)
    for r in rows:byview[r['view']].append(r)
    for view,rr in sorted(byview.items()):
        for task,provider in itertools.product(('A','B'),PROVIDERS):
            by={(r['participant_id'],r['condition']):r for r in rr if r['task']==task and r['provider']==provider}
            ids=sorted({p for p,c in by})
            for metric in ('residue_rate','restoration_rate','all_target_success','core_loss_rate','any_core_loss'):
                eligible=[p for p in ids if (by[p,'SA']['target_n']>0 if metric not in ('core_loss_rate','any_core_loss')
                                          else len(by[p,'SA']['selected_case_ids'])>=0 and
                                          (by[p,'SA']['core_opportunities'] or by[p,'EW']['core_opportunities']))]
                low=[];high=[];unknown=0
                for p in eligible:
                    a=by[p,'SA'][metric];b=by[p,'EW'][metric]
                    unknown+=a is None or b is None
                    low.append((b if b is not None else 0)-(a if a is not None else 1))
                    high.append((b if b is not None else 1)-(a if a is not None else 0))
                missing.append(dict(view=view,task=task,provider=provider,metric=metric,n_pairs=len(eligible),
                                    incomplete_pairs=unknown,difference_lower_bound=mean(low) if low else None,
                                    difference_upper_bound=mean(high) if high else None,
                                    interpretation='logical_missing_outcome_bounds_not_intervals'))
            for condition in ('SA','EW'):
                obs=[r for r in rr if r['task']==task and r['provider']==provider and r['condition']==condition
                     and r['evaluated'] and r['target_n']]
                lower=[r['residue_rate'] for r in obs]
                upper=[(r['RETAINED_count']+r['PARTIAL_count']+r['OTHER_FAILURE_count']+r['INDETERMINATE_count'])/r['target_n'] for r in obs]
                attribution.append(dict(view=view,task=task,provider=provider,condition=condition,programs=len(obs),
                                        clear_residue_mean=mean(lower) if lower else None,
                                        possible_residue_upper_bound=mean(upper) if upper else None,
                                        interpretation='pessimistic_attribution_bound_not_reclassification'))
    return missing,attribution


def cohort_tables(members,bases):
    cohorts=[];bg=[]
    by=defaultdict(list)
    for m in members:
        if m['included']:by[m['view']].append(m)
    for view,mm in sorted(by.items()):
        for task in ('A','B'):
            rr=[m for m in mm if m['task']==task]
            cohorts.append(dict(view=view,task=task,programs=len(rr),sessions_planned=6*len(rr),
                                target_cases_per_arm_model=sum(len(m['selected_case_ids']) for m in rr),
                                participant_ids=[m['participant_id'] for m in rr]))
            for g in GROUPS:
                gg=[m for m in rr if m['group']==g]
                passes=[m['core_baseline_passes'] for m in gg]
                bg.append(dict(view=view,task=task,group=g,programs=len(gg),
                               source_changed=sum(m['source_changed'] for m in gg),
                               conflicts=sum(m['known_conflict'] for m in gg),
                               core_baseline_pass_sum=sum(passes),
                               core_baseline_pass_mean=mean(passes) if passes else None,
                               core_baseline_pass_median=median(passes) if passes else None,
                               core_baseline_pass_min=min(passes) if passes else None,
                               core_baseline_pass_max=max(passes) if passes else None))
    return cohorts,bg


def per_test_tables(rows,tests):
    lookup=defaultdict(list)
    for t in tests:lookup[t['session_id']].append(t)
    core=defaultdict(Counter);five=defaultdict(Counter)
    for r in rows:
        if not r['evaluated']:continue
        for t in lookup[r['session_id']]:
            k=(r['view'],r['task'],r['provider'],r['condition'],t['test_id'])
            bag=core[k] if t['suite']=='core28' else five[k]
            bag[t['transition']]+=1;bag['observed']+=1;bag['revised_'+t['revision_status']]+=1
    def flatten(table):
        return [dict(zip(('view','task','provider','condition','test_id'),k),
                     **{label:c[label] for label in ('observed','PP','PF','FP','FF','revised_passed','revised_failed','revised_error','revised_skipped')})
                for k,c in sorted(table.items())]
    return flatten(core),flatten(five)


def sensitivity_comparisons(arms,paired):
    armmap={(r['view'],r['task'],r['provider'],r['condition']):r for r in arms}
    out=[]
    for r in arms:
        if r['cohort']=='all72_preservation':continue
        main=armmap[r['cohort']+'__main',r['task'],r['provider'],r['condition']]
        for metric in ('reported_target_rate','residue_rate','restoration_rate','core_loss_rate','any_core_loss','combined_success'):
            a=main[metric+'_mean'];b=r[metric+'_mean']
            out.append(dict(view=r['view'],reference_view=main['view'],task=r['task'],provider=r['provider'],
                            condition=r['condition'],metric=metric,programs=r['programs'],evaluated=r['evaluated'],
                            reference_mean=a,view_mean=b,change=b-a if a is not None and b is not None else None,
                            assessment=r['assessment']))
    pairmap={(r['view'],r['task'],r['context'],r['contrast'],r['metric']):r for r in paired}
    for r in paired:
        cohort=r['view'].split('__')[0]
        if cohort=='all72_preservation':continue
        if r['contrast']!='EW minus SA' or r['metric'] not in ('residue_rate','restoration_rate','core_loss_rate','any_core_loss','all_target_success','strict_target_rate','strict_target_success'):continue
        reference=pairmap[cohort+'__main',r['task'],r['context'],r['contrast'],r['metric']]
        a=reference['difference'];b=r['difference']
        out.append(dict(view=r['view'],reference_view=reference['view'],task=r['task'],provider=r['context'],
                        condition='EW_minus_SA',metric=r['metric'],programs=r['n_pairs'],evaluated=r['n_pairs'],
                        reference_mean=a,view_mean=b,change=b-a if a is not None and b is not None else None,
                        assessment=r['assessment']))
    return out


def crosscheck_exports(tests,targets,rows):
    root='output/elmira_author_package_v1/analysis/'
    checks={}
    for name,newrows,keys,fields in [
        ('raw_outcomes/test_outcomes.csv',tests,('session_id','suite','test_id'),('revision_status',)),
        ('raw_outcomes/withdrawal_outcomes.csv',targets,('session_id','case_id'),('outcome',))]:
        path=ROOT/(root+name);data=path.read_bytes();INPUTS[root+name]=digest(data)
        old=list(csv.DictReader(data.decode().splitlines()))
        if 'test_outcomes' in name:
            converted=[dict(t,suite='core' if t['suite']=='core28' else 'original_five') for t in newrows]
        else:converted=newrows
        index={tuple(r[k] for k in keys):r for r in converted}
        assert len(index)==len(old)
        for r in old:
            n=index[tuple(r[k] for k in keys)]
            assert all(r[f]==n[f] for f in fields)
        checks[name]={'records_compared':len(old),'status':'exact_identity_and_outcome_match'}
    path=root+'tables/session_metrics_with_extra_turn.csv';data=(ROOT/path).read_bytes();INPUTS[path]=digest(data)
    old=list(csv.DictReader(data.decode().splitlines()))
    new={r['session_id']:r for r in rows if r['view']=='all72_preservation__main'}
    assert len(old)==len(new)==432
    for r in old:
        for f in ('core_loss_count','core_loss_rate','core_absolute_passes','target_n','target_met'):
            a=r[f];b=new[r['session_id']][f]
            assert (a=='' and b is None) or (a!='' and b is not None and abs(float(a)-b)<1e-12),(r['session_id'],f,a,b)
    checks['session_metrics_with_extra_turn.csv']={'records_compared':432,'fields':['core_loss_count','core_loss_rate','core_absolute_passes','target_n','target_met'],'status':'match'}
    return checks


def main():
    sessions,bases,baselines,original,complete=load()
    rows,members=view_rows(sessions,bases,original,complete)
    arms=summary(rows);groups=summary(rows,True)
    pairdetail,pairs=descriptive_contrasts(rows)
    provdetail,prov=descriptive_contrasts(rows,True)
    tests,targets,btests=raw_tables(sessions,bases,baselines,complete)
    cohorts,bg=cohort_tables(members,bases)
    missing,attrib=bounds(rows)
    percore,perfiv=per_test_tables(rows,tests)
    checks=crosscheck_exports(tests,targets,rows)
    programs=[]
    for pid,b in sorted(bases.items()):
        programs.append(dict(participant_id=pid,task=b['task'],group=b['group'],
                             main69=included(b,'primary69','main'),alternative62=included(b,'alternative62','main'),
                             stricter_format61=included(b,'primary69','phase_i_format'),source_changed=b['source_changed'],
                             known_conflict=pid in CONFLICTS,source_sha256=b['starting_source_sha256'],
                             fixed_profile=b['fixed_profile'],p2_eligible_cases=b['eligible_case_ids'],
                             phase_i_predicates=b['original_phase_i_predicates'],
                             phase_i_original_case_mapping=b['original_phase_i_case_mapping'],
                             baseline_core_pass_ids=b['core_baseline_pass_ids']))
    tables={'programs.csv':programs,'membership.csv':members,'cohorts.csv':cohorts,'baseline_groups.csv':bg,
            'session_metrics.csv':rows,'arm_summary.csv':arms,'group_summary.csv':groups,
            'paired_program_differences.csv':pairdetail,'paired_summary.csv':pairs,
            'provider_program_differences.csv':provdetail,'provider_summary.csv':prov,
            'group_comparisons.csv':group_contrasts(rows),'raw_test_outcomes.csv':tests,
            'raw_target_outcomes.csv':targets,'baseline_test_outcomes.csv':btests,
            'per_core_test.csv':percore,'original_five_diagnostics.csv':perfiv,
            'missingness_bounds.csv':missing,'residue_attribution_bounds.csv':attrib,
            'sensitivity_comparisons.csv':sensitivity_comparisons(arms,pairs)}
    for name,rr in tables.items():write(name,rr)
    by={(r['view'],r['task']):r for r in cohorts}
    assert [by['primary69__main',t]['programs'] for t in ('A','B')]==[35,34]
    assert [by['alternative62__main',t]['programs'] for t in ('A','B')]==[30,32]
    assert sum(p['stricter_format61'] for p in programs)==61
    assert len(tests)==432*33 and len(targets)==381*6
    manifest=dict(schema='withdrawal_descriptive_analysis_v2',plan_sha256=PLAN_SHA,
                  scope='saved_evidence_descriptive_only',new_hypothesis_tests=0,new_confidence_intervals=0,
                  participant_executions=0,model_calls=0,original_slots=432,original_grades=431,complete_grades=432,
                  extension_slot=EXTENSION_ID,views=sorted({r['view'] for r in rows}),
                  inputs=dict(sorted(INPUTS.items())),table_rows={n:len(rr) for n,rr in tables.items()},
                  checks=checks,
                  aliases={'alternative62__phase_i_all_targets':'alternative62__main in this saved dataset only',
                           'primary69__phase_i_all_targets':'alternative62__main in this saved dataset only'},
                  outputs={n:digest((OUT/'tables'/n).read_bytes()) for n in tables},
                  source_sha256=digest(Path(__file__).read_bytes()))
    (OUT/'analysis_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'PASS','views':len(manifest['views']),'table_rows':manifest['table_rows'],'checks':checks},indent=2))

if __name__=='__main__':main()
