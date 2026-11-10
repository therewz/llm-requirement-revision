"""Uniform exact numerical verification of planned v3 tests, all 24 views."""
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict, Counter
from math import isclose
import csv, hashlib, json, math
import numpy as np
from outcome_checks import (ROOT,PAIR,GROUP,TABLE,read,holm,score,row_rank_twice,
                            friedman_exact,group_exact,sample_group,signed_rank_exact,
                            paired_bootstrap,group_bootstrap,phash)

DEST=ROOT/'reports/statistical_analysis_v3/verification/all_views_exact_v1'
POLICY=ROOT/'reports/statistical_analysis_v3/verification/ALL_VIEW_PRECISION_POLICY.md'

def meanflip_exact(ds):
    nz=[x for x in ds if x]
    if not nz:return None,0,1
    common=math.lcm(*(x.denominator for x in nz))
    weights=[x.numerator*(common//x.denominator) for x in nz]
    assert sum(abs(x) for x in weights)<=np.iinfo(np.int64).max
    observed=abs(sum(weights));n=len(weights);draws=2**n
    if observed==0:return 1.,draws,draws
    def sign_sums(seq):
        values=np.array([0],dtype=np.int64)
        for x in seq:values=np.concatenate((values+x,values-x))
        return values
    left=sign_sums(weights[:n//2]);right=np.sort(sign_sums(weights[n//2:]))
    above=len(right)-np.searchsorted(right,observed-left,side='left')
    below=np.searchsorted(right,-observed-left,side='right')
    extreme=int(np.sum(above+below,dtype=np.int64))
    return extreme/draws,extreme,draws

def main():
    assert not DEST.exists(), 'Use a new versioned output directory; do not overwrite.'
    gate=json.loads((ROOT/'reports/statistical_analysis_v3/PREFLIGHT.json').read_text())
    assert gate['status']=='PASS'
    manifest=json.loads((PAIR/'manifest.json').read_text())
    for f,h in manifest['outputs'].items():assert phash(PAIR/f)==h
    gm=json.loads((GROUP/'analysis_manifest.json').read_text())
    assert phash(GROUP/'group_tests.csv')==gm['output_sha256']
    table=read(TABLE);by={(r['view'],r['task'],r['provider'],r['participant_id'],r['condition']):r for r in table}
    paired=read(PAIR/'paired_wilcoxon.csv');meanflip=read(PAIR/'paired_mean_permutation.csv');fried=read(PAIR/'friedman.csv')
    groups=read(GROUP/'group_tests.csv');observations=defaultdict(list)
    for r in read(PAIR/'paired_observations.csv'):
        observations[(r['view'],r['task'],r['provider'],r['metric'],r['contrast'])].append(r)
    caches={'group':{},'paired':{},'meanflip':{},'friedman':{}}; exact={};rows_by_family=defaultdict(list)
    ci_counts=Counter();totals=Counter()
    for i,r in enumerate(paired):
        family=('paired',r['view'],r['family']);rows_by_family[family].append((i,r))
        k=(r['view'],r['task'],r['provider'],r['metric'],r['contrast'])
        ds=[F(int(z['difference_num']),int(z['difference_den'])) for z in observations[k]]
        assert len(ds)==int(r['n_pairs'])
        if r['status']=='tested':
            key=min(tuple(sorted(ds)),tuple(sorted(-x for x in ds)))
            if key not in caches['paired']:caches['paired'][key]=signed_rank_exact(ds)
            p,extreme,draws=caches['paired'][key]
            if r['p_method'].startswith('exact'):assert abs(p-float(r['p']))<1e-12
            exact[family,i]=(p,extreme,draws,'exact_conditional_signs')
            totals['paired_tested']+=1
        else:
            assert not r['p'];exact[family,i]=(None,None,None,'not_testable')
            totals['paired_uninformative']+=1
        if r['ci_low']:
            left,right=r['contrast'].split(' minus ')[::-1]
            ci=paired_bootstrap(ds,(r['view'],r['task'],r['provider'],r['metric'],left,right))
            assert isclose(float(r['ci_low']),ci[0],abs_tol=1e-12) and isclose(float(r['ci_high']),ci[1],abs_tol=1e-12)
            ci_counts['paired']+=1
    for i,r in enumerate(meanflip):
        family=('meanflip',r['view'],r['family']);rows_by_family[family].append((i,r))
        k=(r['view'],r['task'],r['provider'],r['metric'],r['contrast'])
        ds=[F(int(z['difference_num']),int(z['difference_den'])) for z in observations[k]]
        assert len(ds)==int(r['n_pairs'])
        if r['status']=='tested':
            key=min(tuple(sorted(ds)),tuple(sorted(-x for x in ds)))
            if key not in caches['meanflip']:caches['meanflip'][key]=meanflip_exact(ds)
            p,extreme,draws=caches['meanflip'][key]
            if r['p_method'].startswith('exact'):assert abs(p-float(r['p']))<1e-12
            exact[family,i]=(p,extreme,draws,'exact_conditional_mean_signs');totals['meanflip_tested']+=1
        else:
            assert not r['p'];exact[family,i]=(None,None,None,'not_testable');totals['meanflip_uninformative']+=1
    for i,r in enumerate(fried):
        family=('friedman',r['view'],r['family']);rows_by_family[family].append((i,r))
        if r['status']=='tested':
            pids=sorted({x['participant_id'] for x in table if x['view']==r['view'] and x['task']==r['task'] and x['provider']==r['provider']})
            blocks=[]
            for pid in pids:
                block=tuple(score(by[r['view'],r['task'],r['provider'],pid,arm],'core_loss_rate') for arm in ('RR','SA','EW'))
                if all(x is not None for x in block):blocks.append(block)
            assert len(blocks)==int(r['n_complete'])
            key=tuple(sorted(row_rank_twice(block) for block in blocks))
            if key not in caches['friedman']:caches['friedman'][key]=friedman_exact(blocks)
            q,p,extreme,draws=caches['friedman'][key]
            assert isclose(q,float(r['friedman_q']),rel_tol=1e-11,abs_tol=1e-11)
            if r['p_method'].startswith('exact'):assert abs(p-float(r['p']))<1e-12
            exact[family,i]=(p,extreme,draws,'exact_within_block_labels');totals['friedman_tested']+=1
        else:
            assert not r['p'];exact[family,i]=(None,None,None,'not_testable');totals['friedman_uninformative']+=1
    for i,r in enumerate(groups):
        family=('group',r['view'],'group');rows_by_family[family].append((i,r))
        if r['status']=='tested':
            key0=(r['view'],r['task'],r['provider'],r['context'],r['metric'],r['group_left'],r['group_right'])
            a=sample_group(r,by,'left');b=sample_group(r,by,'right')
            assert len(a)==int(r['n_left']) and len(b)==int(r['n_right'])
            assert isclose(float(sum(b,F())/len(b)-sum(a,F())/len(a)),float(r['difference']),abs_tol=1e-12)
            key=min((tuple(sorted(a)),tuple(sorted(b))),(tuple(sorted(b)),tuple(sorted(a))))
            if key not in caches['group']:caches['group'][key]=group_exact(a,b,key0)
            p,extreme,draws,method=caches['group'][key]
            assert method=='exact_all_allocations' and draws<=3000000,(key0,draws,method)
            if r['permutation_method'].startswith('exact'):assert abs(p-float(r['p_raw']))<1e-12
            exact[family,i]=(p,extreme,draws,method);totals['group_tested']+=1
            ci=group_bootstrap(a,b,key0)
            assert isclose(float(r['ci_low']),ci[0],abs_tol=1e-12) and isclose(float(r['ci_high']),ci[1],abs_tol=1e-12)
            ci_counts['group']+=1
            if totals['group_tested']%100==0:print('Group rows checked:',totals['group_tested'],'unique distributions:',len(caches['group']),flush=True)
        else:
            assert not r['p_raw'];exact[family,i]=(None,None,None,'not_testable');totals['group_uninformative']+=1
    final={'paired':[],'meanflip':[],'friedman':[],'group':[]}
    for family,members in sorted(rows_by_family.items()):
        kind,view,name=family
        pairsizes={'residue_SA_EW':4,'restoration_SA_EW':4,'core_3_contrasts':12}
        size={'group':108,'friedman':4,'paired':pairsizes.get(name),'meanflip':pairsizes.get(name)}[kind]
        assert len(members)==size,(family,len(members),size)
        raw=[exact[family,i][0] for i,_ in members]
        qvalues=holm(raw)
        for (i,r),q in zip(members,qvalues):
            ep,extreme,draws,method=exact[family,i]
            primary=float(r['p_raw' if kind=='group' else 'p']) if r['p_raw' if kind=='group' else 'p'] else None
            pq=float(r['p_holm']) if r['p_holm'] else None
            label=lambda x:'NA' if x is None else ('below' if x<.05 else ('equal' if x==.05 else 'above'))
            final[kind].append({'view':view,'family':name,'task':r['task'],'provider':r['provider'],
               'context':r.get('context',''),'metric':r['metric'],'contrast':r.get('contrast',''),
               'group_left':r.get('group_left',''),'group_right':r.get('group_right',''),
               'status':r['status'],'n_pairs':r.get('n_pairs',''),'n_left':r.get('n_left',''),'n_right':r.get('n_right',''),
               'primary_raw_p':primary,'primary_holm_p':pq,'exact_raw_p':ep,'exact_holm_p':q,
               'primary_threshold':label(pq),'exact_threshold':label(q),
               'difference_at_strict_p_lt_0_05':None if pq is None or q is None else (pq<.05)!=(q<.05),
               'exact_method':method,'exact_extreme':extreme,'exact_assignments':draws})
    assert len(final['group'])==24*108 and len(final['friedman'])==24*4
    assert totals['group_tested']==991 and totals['paired_tested']==306 and totals['meanflip_tested']==306 and totals['friedman_tested']==88,totals
    # Check every main/alternate value against the already independent first audit.
    for kind in final:
        if kind=='meanflip':continue
        ref=read(ROOT/f'reports/statistical_analysis_v3/verification/EXACT_{kind.upper()}_RECALIBRATION.csv')
        keys={'paired':['view','task','provider','metric','contrast'],
              'friedman':['view','task','provider','metric'],
              'group':['view','task','provider','context','metric','group_left','group_right']}[kind]
        got={tuple(str(r[k]) for k in keys):r for r in final[kind] if r['view'] in ('primary69__main','alternative62__main')}
        assert len(got)==len(ref)
        for r in ref:
            z=got[tuple(r[k] for k in keys)]
            for x,y in [('independent_exact_raw_p','exact_raw_p'),('independent_exact_holm_p','exact_holm_p')]:
                assert (not r[x] and z[y] is None) or (r[x] and z[y] is not None and abs(float(r[x])-z[y])<1e-12)
    # Independent earlier mean-sign checks cover every SA/EW target/core cell.
    previous=json.loads((ROOT/'reports/statistical_analysis_v3/verification/OUTCOME_VERIFICATION.json').read_text())
    meanindex={(r['view'],r['task'],r['provider'],r['metric'],r['contrast']):r for r in final['meanflip']}
    for r in previous['mean_permutation_checks']:
        z=meanindex[tuple(r['key'])]
        if r['status']=='verified':assert abs(r['exact_p']-z['exact_raw_p'])<1e-12
        elif r['status']=='no_variation':assert z['exact_raw_p'] is None
    DEST.mkdir(parents=True,exist_ok=False);output_hashes={}
    for kind,rows in final.items():
        path=DEST/(kind+'_all_views_exact.csv')
        with path.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        output_hashes[path.name]=phash(path)
    changes={}
    per_view={}
    for kind,rows in final.items():
        changed=[r for r in rows if r['difference_at_strict_p_lt_0_05']]
        changes[kind]=changed
        for view in sorted({r['view'] for r in rows}):
            selected=[r for r in rows if r['view']==view]
            per_view[kind,view]=dict(slots=len(selected),testable=sum(r['status']=='tested' for r in selected),
                primary_below=sum(r['primary_threshold']=='below' for r in selected),primary_equal=sum(r['primary_threshold']=='equal' for r in selected),
                exact_below=sum(r['exact_threshold']=='below' for r in selected),exact_equal=sum(r['exact_threshold']=='equal' for r in selected))
    policy_sha=phash(POLICY)
    # Identical-observation aliases must have the same exact family results;
    # simulation streams may differ but exact values cannot.
    aliases=[('primary69__phase_i_all_targets','alternative62__main'),
             ('alternative62__phase_i_all_targets','alternative62__main')]
    for kind,rows in final.items():
        keys={'paired':['task','provider','metric','contrast'],
              'meanflip':['task','provider','metric','contrast'],
              'friedman':['task','provider','metric'],
              'group':['task','provider','context','metric','group_left','group_right']}[kind]
        for left,right in aliases:
            a={tuple(r[k] for k in keys):r for r in rows if r['view']==left}
            b={tuple(r[k] for k in keys):r for r in rows if r['view']==right}
            assert a.keys()==b.keys()
            for k,x in a.items():
                y=b[k]
                assert x['exact_raw_p']==y['exact_raw_p'] and x['exact_holm_p']==y['exact_holm_p'],(kind,left,right,k)
    result={'status':'PASS_WITH_NUMERICAL_THRESHOLD_SENSITIVITIES' if any(changes.values()) else 'PASS',
       'scope':'Uniform exact conditional recalibration of same planned tests; extended after observed Monte Carlo floor; original planned MC results remain unchanged.',
       'policy_sha256':policy_sha,'source_sha256':phash(Path(__file__)),'algorithm_source_sha256':phash(Path(__file__).with_name('outcome_checks.py')),
       'source_inputs':{'v2_session_metrics':phash(TABLE),'paired_manifest':phash(PAIR/'manifest.json'),'group_manifest':phash(GROUP/'analysis_manifest.json')},
       'counts':dict(totals),'ci_reproduced':dict(ci_counts),'distinct_distributions':{k:len(v) for k,v in caches.items()},
       'outputs':output_hashes,'threshold_changes':changes,'per_view':{kind+'|'+view:v for (kind,view),v in per_view.items()},
       'alpha_rule':'threshold flags use p<0.05; equal values labeled separately','identical_view_aliases_exactly_equal':'PASS',
       'model_calls':0,'participant_execution':0}
    (DEST/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'counts':result['counts'],'ci':result['ci_reproduced'],'unique':result['distinct_distributions'],'threshold_change_counts':{k:len(v) for k,v in changes.items()},'outputs':output_hashes},indent=2))

if __name__=='__main__':main()
