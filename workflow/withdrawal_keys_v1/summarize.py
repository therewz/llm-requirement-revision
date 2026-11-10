"""Rebuild baseline classifications from immutable captured observations; no execution."""
import collections
import csv
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT/'runs/withdrawal_keys_v1'
sys.path.insert(0,str(HERE))
import task_a
import task_b
from assess import verify, sha, write


def csv_write(path, rows):
    with open(path,'w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def score_b(case, observations, byid, tuple_view=False):
    def value(obs):
        if not isinstance(obs,dict) or obs.get('kind')!='ret': return None
        if obs.get('type')=='bool' and type(obs.get('value')) is bool: return obs['value']
        if tuple_view and obs.get('type')=='tuple' and obs.get('length')==2:
            items=obs.get('items',[])
            if len(items)==2 and items[0].get('type')=='bool' and type(items[0].get('value')) is bool and items[1].get('type')=='dict':
                return items[0]['value']
        return None
    obs=observations.get(case['case_id'])
    v=value(obs)
    controls=case['linked_controls']
    control_ok=all(value(observations.get(c)) is byid[c]['retained_expectation'] for c in controls)
    if v is None:
        status='MISSING' if obs is None else 'OTHER_FAILURE'
    elif v is True: status='RESTORED'
    elif control_ok: status='RETAINED'
    else: status='INDETERMINATE'
    return {'status':status,'profile_eligible':status=='RETAINED', 'controls_ok':control_ok}


def suite_summary(rec,layer):
    obj=rec[layer]; result=obj['results']; counts=collections.Counter(v[0] for v in result.values())
    # Count alone cannot establish complete case coverage: compare to captured collection inventory.
    expected=json.loads((RUN/'suite_case_ids.json').read_text())[rec['task']][layer]
    complete=set(result)==set(expected) and not obj['metadata']['timed_out_file'] and obj['metadata']['returncode'] in (0,1) and not obj['metadata']['collection_error']
    return {'complete':complete,'observed':len(result),'passed':counts['passed'],
            'failed':counts['failed'],'error':counts['error'],'skipped':counts['skipped'],
            'passed_ids':sorted(k for k,v in result.items() if v[0]=='passed')}


def main():
    verify()
    inv=json.loads((RUN/'inventory.json').read_text())
    manifests={t:json.loads((RUN/f'answer_key_{t}.json').read_text()) for t in 'AB'}
    programs=[]; cases=[]; suites=[]
    for r in inv:
        sid,task=r['participant_id'],r['task']; manifest=manifests[task]
        raw={p:json.loads((RUN/'raw'/f'{sid}_{p}.json').read_text()) for p in ['P1','P2']}
        for p,rec in raw.items():
            assert (rec['participant_id'],rec['task'],rec['group'],rec['phase'])==(sid,task,r['group'],p)
            assert rec['source_sha256']==r[p]['sha256'] and rec['freeze_sha256']==sha(RUN/'freeze.json')
            for layer in ['core28','supplied5']:
                assert rec[layer]['suite_sha256']==sha(ROOT/rec[layer]['suite_path'])
                suites.append({'participant_id':sid,'task':task,'group':r['group'],'phase':p,'layer':layer,
                    **suite_summary(rec,layer)})
        obs={p:rec['targets']['cases'] for p,rec in raw.items()}
        targets=[c for c in manifest['cases'] if c['role'] in ['target','primary_target']]
        byid={c['case_id']:c for c in manifest['cases']}
        profile_counts=collections.Counter(); strict_counts=collections.Counter(); membership_counts=collections.Counter()
        p_rows=[]
        for case in targets:
            profile=case.get('profile','boolean')
            if task=='A': scores={p:task_a.classify(case,obs[p]) for p in obs}
            else: scores={p:score_b(case,obs[p],byid) for p in obs}
            eligible=scores['P2']['profile_eligible']
            p1match=scores['P1']['status']=='RESTORED'
            # Keep the original stricter classification, but expose the actual
            # target predicate separately from formatting of unrelated slots.
            p1obs=obs['P1'].get(case['case_id'],{})
            if task=='A':
                p1format=task_a._slots(p1obs) is not None
                p1membership=(p1obs.get('kind')=='ret' and p1obs.get('type')=='list_str'
                    and isinstance(p1obs.get('value'),list) and all(type(x) is str for x in p1obs['value'])
                    and set(case['target_slots'])<=set(p1obs['value']))
            else:
                p1format=p1obs.get('type')=='bool' and type(p1obs.get('value')) is bool
                p1membership=p1match
            if eligible: profile_counts[profile]+=1
            if eligible and p1match: strict_counts[profile]+=1
            if eligible and p1membership: membership_counts[profile]+=1
            row={'participant_id':sid,'task':task,'group':r['group'],'profile':profile,'case_id':case['case_id'],
                'p2_status':scores['P2']['status'],'p2_eligible':eligible,'p2_controls_ok':scores['P2'].get('controls_ok',False),
                'p1_status':scores['P1']['status'],'p1_target_restored':p1match,'p1_controls_ok':scores['P1'].get('controls_ok',False),
                'p1_target_predicate_match':p1membership,'p1_return_format_valid':p1format,
                'p2_and_p1_target_predicate_eligible':eligible and p1membership,
                'p1_and_p2_eligible':eligible and p1match,'selected_profile':False,
                'p2_tuple_diagnostic_eligible':False,'p1_match_for_tuple_diagnostic':False}
            if task=='B':
                diag=score_b(case,obs['P2'],byid,True)
                is_tuple=obs['P2'].get(case['case_id'],{}).get('type')=='tuple'
                row['p2_tuple_diagnostic_eligible']=is_tuple and diag['profile_eligible']
                row['p1_match_for_tuple_diagnostic']=row['p2_tuple_diagnostic_eligible'] and score_b(case,obs['P1'],byid,True)['status']=='RESTORED'
            p_rows.append(row)
        order=manifest.get('profile_priority',['boolean'])
        selected=next((p for p in order if profile_counts[p]),None)
        for row in p_rows: row['selected_profile']=row['profile']==selected
        cases.extend(p_rows)
        std='iso_primary' if task=='A' else 'boolean'
        core={p:suite_summary(raw[p],'core28') for p in raw}
        programs.append({'participant_id':sid,'task':task,'group':r['group'],
            'standard_p2_cases':profile_counts[std],'standard_p1_and_p2_cases':strict_counts[std],
            'standard_p2_eligible':bool(profile_counts[std]),'standard_p1_and_p2_eligible':bool(strict_counts[std]),
            'selected_profile':selected or '', 'interface_aware_p2_cases':profile_counts[selected] if selected else 0,
            'interface_aware_p1_and_p2_cases':strict_counts[selected] if selected else 0,
            'interface_aware_p2_eligible':selected is not None,
            'interface_aware_p1_and_p2_eligible':bool(strict_counts[selected]) if selected else False,
            'standard_p1_target_predicate_cases':membership_counts[std],
            'interface_aware_p1_target_predicate_cases':membership_counts[selected] if selected else 0,
            'interface_aware_p1_target_predicate_eligible':bool(membership_counts[selected]) if selected else False,
            'tuple_diagnostic_cases':sum(x['p2_tuple_diagnostic_eligible'] for x in p_rows) if task=='B' else 0,
            'p1_core_complete':core['P1']['complete'],'p1_core_passes':core['P1']['passed'],
            'p2_core_complete':core['P2']['complete'],'p2_core_passes':core['P2']['passed'],
            'p1_import_error':json.dumps(raw['P1']['targets'].get('import_error')),
            'p2_import_error':json.dumps(raw['P2']['targets'].get('import_error'))})
    summary={}
    for task in 'AB':
        rows=[r for r in programs if r['task']==task]
        summary[task]={'candidates':len(rows),'standard_p2_programs':sum(r['standard_p2_eligible'] for r in rows),
            'standard_p2_cases':sum(r['standard_p2_cases'] for r in rows),
            'standard_p1_and_p2_programs':sum(r['standard_p1_and_p2_eligible'] for r in rows),
            'standard_p1_and_p2_cases':sum(r['standard_p1_and_p2_cases'] for r in rows),
            'interface_aware_p2_programs':sum(r['interface_aware_p2_eligible'] for r in rows),
            'interface_aware_p2_cases':sum(r['interface_aware_p2_cases'] for r in rows),
            'interface_aware_p1_and_p2_programs':sum(r['interface_aware_p1_and_p2_eligible'] for r in rows),
            'interface_aware_p1_and_p2_cases':sum(r['interface_aware_p1_and_p2_cases'] for r in rows),
            'interface_aware_p1_target_predicate_programs':sum(r['interface_aware_p1_target_predicate_eligible'] for r in rows),
            'interface_aware_p1_target_predicate_cases':sum(r['interface_aware_p1_target_predicate_cases'] for r in rows),
            'p2_core_assessable_programs':sum(r['p2_core_complete'] and r['p2_core_passes']>0 for r in rows),
            'p2_core_pass_opportunities':sum(r['p2_core_passes'] for r in rows if r['p2_core_complete']),
            'core_denominator_scope':'all screened candidates with complete core execution, independent of withdrawal eligibility',
            'by_group':{g:{'candidates':sum(r['group']==g for r in rows),
                'standard_p2':sum(r['standard_p2_eligible'] for r in rows if r['group']==g),
                'interface_aware_p2':sum(r['interface_aware_p2_eligible'] for r in rows if r['group']==g)} for g in ['G1','G2','G3']}}
    out=RUN/'derived';out.mkdir(exist_ok=True)
    csv_write(out/'programs.csv',programs);csv_write(out/'target_cases.csv',cases)
    write(out/'suite_results.json',suites);write(out/'summary.json',summary)
    write(out/'lineage.json',{'freeze_sha256':sha(RUN/'freeze.json'),'scorer_sha256':sha(__file__),
        'raw_hashes':{p.name:sha(p) for p in sorted((RUN/'raw').glob('*.json'))},
        'scientific_unit':'participant/program, case-level flags retained; profiles never pooled as independent repetitions',
        'clarification':'After baseline inspection, added P1 target-predicate match separately from stricter whole-return format. Original strict flags and prior derived view preserved. Inputs/raw records/P2 eligibility unchanged; no model outputs used.'})
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
