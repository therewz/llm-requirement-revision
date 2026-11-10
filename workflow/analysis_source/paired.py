"""Conditional paired inference for the frozen withdrawal study; no candidate execution."""
from __future__ import annotations
import argparse
import csv
import hashlib
import itertools
import json
import math
import os
import platform
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / 'reports/full_analysis_v2_prelim/tables/session_metrics.csv'
INPUT_MANIFEST = ROOT / 'reports/full_analysis_v2_prelim/analysis_manifest.json'
PLAN = ROOT / 'planning/ANALYSIS_PLAN_v2_PRESTAT.md'
FREEZE = ROOT / 'planning/ANALYSIS_PLAN_v2_PRESTAT_FREEZE.json'
LOCK = ROOT / 'planning/STATISTICAL_ANALYSIS_V3_OPERATIONAL_LOCK.md'
LOCK_RECORD = ROOT / 'planning/STATISTICAL_ANALYSIS_V3_OPERATIONAL_LOCK.json'
PREFLIGHT = ROOT / 'reports/statistical_analysis_v3/PREFLIGHT.json'
OUT = ROOT / 'reports/statistical_analysis_v3/paired'
SEED = 20261106
BOOT = 10000
MC = 99999
EXACT_SIGN_MAX = 20
EXACT_FRIEDMAN_MAX = 7
PROVIDERS = ('anthropic','openai')
TASKS = ('A','B')
CONTRASTS = (('SA','EW'),('RR','SA'),('RR','EW'))


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rng_for(kind, *key):
    encoded=json.dumps([SEED,kind,*key],ensure_ascii=True,separators=(',',':'))
    value=int.from_bytes(hashlib.sha256(encoded.encode()).digest()[:8], 'big')
    return np.random.Generator(np.random.PCG64(value))


def rank_twice(abs_fractions):
    """Ties exact in integer/Fraction domain. Return twice average ranks as integers."""
    indexed=sorted(enumerate(abs_fractions),key=lambda x:x[1]); result=[0]*len(indexed)
    i=0
    while i<len(indexed):
        j=i+1
        while j<len(indexed) and indexed[j][1]==indexed[i][1]: j+=1
        twice_rank=(i+1)+j
        for k in range(i,j):result[indexed[k][0]]=twice_rank
        i=j
    return result


def signedrank(differences, key=(), mc=MC, exact_max=EXACT_SIGN_MAX):
    if len(differences)<2:
        return {'status':'insufficient_pairs','p':None,'n_nonzero':sum(x!=0 for x in differences)}
    d=[x for x in differences if x != 0]; n=len(d)
    if not n:return {'status':'no_variation','p':None,'n_nonzero':0}
    ranks=rank_twice([abs(x) for x in d]);
    signed=sum(r if x>0 else -r for x,r in zip(d,ranks));obs=abs(signed)
    wplus=sum(r for x,r in zip(d,ranks) if x>0)/2
    wminus=sum(r for x,r in zip(d,ranks) if x<0)/2
    if n<=exact_max:
        # dp[j] counts sign assignments with twice-rank sum j on the positive side.
        dp=np.array([1],dtype=np.int64)
        for r in ranks:
            new=np.zeros(len(dp)+r,dtype=np.int64);new[:len(dp)]+=dp;new[r:r+len(dp)]+=dp;dp=new
        total=sum(ranks); idx=np.arange(len(dp)); extreme=int(dp[np.abs(2*idx-total)>=obs].sum())
        count=1<<n;p=extreme/count;method='exact_conditional_signs_dynamic_counts'; draws=0
    else:
        generator=rng_for('signedrank',*key); rr=np.asarray(ranks,dtype=np.int64);extreme=0
        for start in range(0,mc,10000):
            z=generator.integers(0,2,(min(10000,mc-start),n),dtype=np.int8).astype(np.int64)*2-1
            extreme+=int(np.count_nonzero(np.abs(z@rr)>=obs))
        p=(extreme+1)/(mc+1);method='monte_carlo_conditional_signs_plus_one';draws=mc
    return {'status':'tested','p':float(p),'n_nonzero':n,'w_plus':wplus,'w_minus':wminus,
            'signed_rank_sum':signed/2,'p_method':method,'draws':draws,'null_assignments':2**n,'extreme':extreme}


def meanflip(differences,key=(),mc=MC,exact_max=EXACT_SIGN_MAX):
    if len(differences)<2:return {'status':'insufficient_pairs','p':None,'n_nonzero':sum(x!=0 for x in differences)}
    nonzero=[x for x in differences if x];n=len(nonzero)
    if not n:return {'status':'no_variation','p':None,'n_nonzero':0}
    # The extreme-tail shortcut in the accepted v1 analyzer is exact for one-direction values.
    if all(x>0 for x in nonzero) or all(x<0 for x in nonzero):
        return {'status':'tested','p':2/(2**n),'n_nonzero':n,'p_method':'exact_one_direction_analytic','draws':0,'null_assignments':2**n,'extreme':2}
    # Preserve v1's two-sided mean sign-flip statistic with exact rational comparisons.
    # v1 used floats with a 1e-10 equality tolerance; this version uses exact integer
    # weights, which can differ in the rare case that near-ties are not true ties.
    common=math.lcm(*(x.denominator for x in nonzero))
    weights=[x.numerator*(common//x.denominator) for x in nonzero]
    if sum(abs(x) for x in weights)>np.iinfo(np.int64).max:
        raise OverflowError('Exact rational sign-flip weights exceed int64')
    arr=np.asarray(weights,dtype=np.int64);obs=abs(sum(weights))
    if n<=exact_max:
        sums=np.zeros(1,dtype=np.int64)
        for x in arr:sums=np.concatenate((sums+x,sums-x))
        p=float(np.mean(np.abs(sums)>=obs));method='exact_signs_integer_weights';draws=len(sums)
    else:
        generator=rng_for('meanflip',*key);extreme=0
        for start in range(0,mc,10000):
            z=generator.integers(0,2,(min(10000,mc-start),n),dtype=np.int8).astype(np.int64)*2-1
            extreme+=int(np.count_nonzero(np.abs(z@arr)>=obs))
        p=(extreme+1)/(mc+1);method='monte_carlo_signs_integer_weights_plus_one';draws=mc
    return {'status':'tested','p':float(p),'n_nonzero':n,'p_method':method,'draws':draws,'null_assignments':2**n}


def bootstrap_ci(differences,key=(),draws=BOOT):
    if len(differences)<2:return {'ci_low':None,'ci_high':None,'bootstrap_degenerate':None,'bootstrap_draws':0}
    arr=np.array([float(x) for x in differences]);constant=all(x==differences[0] for x in differences)
    if constant:
        value=float(differences[0]);return {'ci_low':value,'ci_high':value,'bootstrap_degenerate':True,'bootstrap_draws':0}
    gen=rng_for('bootstrap',*key);means=np.empty(draws)
    for start in range(0,draws,2000):
        size=min(2000,draws-start);means[start:start+size]=arr[gen.integers(0,len(arr),(size,len(arr)))].mean(axis=1)
    lo,hi=np.quantile(means,[.025,.975],method='linear')
    return {'ci_low':float(lo),'ci_high':float(hi),'bootstrap_degenerate':False,'bootstrap_draws':draws}


def rank_row(values):
    order=sorted(enumerate(values),key=lambda x:x[1]);out=[0,0,0]; i=0; ties=[]
    while i<3:
        j=i+1
        while j<3 and order[j][1]==order[i][1]:j+=1
        val=i+1+j
        for k in range(i,j):out[order[k][0]]=val
        ties.append(j-i); i=j
    return tuple(out), sum(t**3-t for t in ties)


def friedman(rows,key=(),mc=MC,exact_max=EXACT_FRIEDMAN_MAX):
    n=len(rows)
    if n<2:return {'status':'insufficient_complete_blocks','p':None,'n_complete':n}
    ranked=[rank_row(row) for row in rows]; ranks=np.asarray([r for r,_ in ranked],dtype=np.int64)
    tie_sum=sum(t for _,t in ranked); correction=1-tie_sum/(n*24)
    if correction==0:return {'status':'no_within_program_variation','p':None,'n_complete':n,'tie_correction':0.0}
    sums=ranks.sum(axis=0);obs=int(sums@sums)
    # Since ranks are doubled, Q = (sum(R2_j^2)/4)/n - 3*n*(k+1), k=3.
    q=Fraction(obs-48*n*n,4*n)*Fraction(24*n,24*n-tie_sum)
    permutations=list(itertools.permutations(range(3)))
    patterns=np.asarray([[list(row[list(perm)]) for perm in permutations] for row in ranks],dtype=np.int64)
    if n<=exact_max:
        states={(0,0):1}
        for row in patterns:
            nxt=Counter()
            for (a,b),count in states.items():
                for x,y,_ in row:nxt[(a+int(x),b+int(y))]+=count
            states=nxt
        total_rank_sum=12*n
        extreme=sum(count for (a,b),count in states.items() if a*a+b*b+(total_rank_sum-a-b)**2>=obs)
        count=6**n;assert sum(states.values())==count
        p=extreme/count;method='exact_within_block_labels_dynamic_counts';draws=0
    else:
        generator=rng_for('friedman',*key);extreme=0
        for start in range(0,mc,10000):
            size=min(10000,mc-start);choices=generator.integers(0,6,size=(size,n))
            totals=patterns[np.arange(n)[None,:],choices,:].sum(axis=1)
            extreme+=int(np.count_nonzero(np.sum(totals*totals,axis=1)>=obs))
        draws=mc;p=(extreme+1)/(mc+1);method='monte_carlo_within_block_labels_plus_one'
    return {'status':'tested','p':float(p),'n_complete':n,'friedman_q':float(q),'tie_correction':correction,
            'p_method':method,'draws':draws,'null_assignments':6**n,'extreme':int(extreme),
            'rank_sums':(sums/2).tolist()}


def apply_holm(rows, family_size):
    """Reserve all original slots via internal p=1; never write p for untestable slots."""
    if len(rows)!=family_size:raise ValueError(f'family rows {len(rows)} != {family_size}')
    ordered=sorted(rows,key=lambda x:1.0 if x['p'] is None else x['p']);previous=0.0
    for idx,row in enumerate(ordered):
        numeric=1.0 if row['p'] is None else row['p']
        previous=max(previous,min(1.0,(family_size-idx)*numeric))
        row['p_holm']=previous if row['p'] is not None else None
        row['family_size']=family_size
        row['holm_policy']='unassessable_reserved_as_one_but_reported_missing'


def ratio(row, metric):
    if row['evaluated']!='True':return None
    if metric in ('residue_rate','restoration_rate','restoration_plus_linked_controls'):
        if not row['target_n'] or int(row['target_n'])==0:return None
        n=int(row['target_n'])
        if metric=='residue_rate':value=Fraction(int(row['RETAINED_count'])+int(row['PARTIAL_count']),n)
        elif metric=='restoration_rate':value=Fraction(int(row['RESTORED_count']),n)
        else:
            if not row['strict_target_rate']:return None
            val=float(row['strict_target_rate']);value=Fraction(val).limit_denominator(n)
            assert abs(float(value)-val)<1e-12 and value.denominator<=n
        field={'residue_rate':'residue_rate','restoration_rate':'restoration_rate','restoration_plus_linked_controls':'strict_target_rate'}[metric]
    elif metric=='core_loss_rate':
        if not row['core_opportunities'] or int(row['core_opportunities'])==0:return None
        value=Fraction(int(row['PF']),int(row['core_opportunities']));field='core_loss_rate'
    else:raise ValueError(metric)
    assert row[field] and abs(float(value)-float(row[field]))<1e-12,(row['session_id'],metric)
    return value


def mean_fraction(v): return float(sum(v,Fraction(0))/len(v)) if v else None


def load_rows():
    frozen=json.loads(FREEZE.read_text()); assert sha(PLAN)==frozen['sha256'];assert frozen['sha256']=='abf7fa160883376f0b74a35f85433522e7474a3b76142bb2ac33a6fb01afa416'
    manifest=json.loads(INPUT_MANIFEST.read_text());assert sha(INPUT)==manifest['outputs']['session_metrics.csv']
    rows=list(csv.DictReader(INPUT.open(newline='')))
    assert len(rows)==manifest['table_rows']['session_metrics.csv']
    assert len({(r['view'],r['participant_id'],r['provider'],r['condition']) for r in rows})==len(rows)
    assert len({r['view'] for r in rows})==24
    return rows


def run_analysis(rows):
    views=sorted({r['view'] for r in rows});allrows=[];mean_rows=[];fried_rows=[];observations=[]
    index={(r['view'],r['task'],r['provider'],r['participant_id'],r['condition']):r for r in rows}
    for view in views:
        by={}
        for task,provider in itertools.product(TASKS,PROVIDERS):
            rr=[r for r in rows if r['view']==view and r['task']==task and r['provider']==provider]
            pids=sorted({r['participant_id'] for r in rr})
            for pid in pids:
                assert all((view,task,provider,pid,c) in index for c in ('RR','SA','EW'))
            by[task,provider]=pids
        specs=[]
        if not view.startswith('all72_preservation__'):
            target_metric='restoration_plus_linked_controls' if view.endswith('__strict_controls') else 'restoration_rate'
            specs += [(family,metric,'SA','EW') for family,metric in [('residue_SA_EW','residue_rate'),('restoration_SA_EW',target_metric)]]
        specs += [('core_3_contrasts','core_loss_rate',left,right) for left,right in CONTRASTS]
        for family,metric,left,right in specs:
            for task,provider in itertools.product(TASKS,PROVIDERS):
                valid=[];excluded=[]
                for pid in by[task,provider]:
                    a=ratio(index[view,task,provider,pid,left],metric);b=ratio(index[view,task,provider,pid,right],metric)
                    if a is None or b is None:excluded.append(pid)
                    else:valid.append((pid,a,b))
                diffs=[b-a for _,a,b in valid];key=(view,task,provider,metric,left,right)
                base={'view':view,'task':task,'provider':provider,'family':family,'metric':metric,
                      'contrast':right+' minus '+left,'n_planned':len(by[task,provider]),'n_pairs':len(valid),
                      'excluded_missing_or_undefined':len(excluded),'excluded_participants':excluded,
                      'left_mean':mean_fraction([a for _,a,_ in valid]),'right_mean':mean_fraction([b for _,_,b in valid]),
                      'difference':mean_fraction(diffs),'difference_percentage_points':100*mean_fraction(diffs) if diffs else None,
                      'increased':sum(x>0 for x in diffs),'decreased':sum(x<0 for x in diffs),'tied':sum(x==0 for x in diffs)}
                boot=bootstrap_ci(diffs,key);signed=signedrank(diffs,key);supp=meanflip(diffs,key)
                r={**base,**boot,**signed};r['ci_low_pp']=100*r['ci_low'] if r['ci_low'] is not None else None;r['ci_high_pp']=100*r['ci_high'] if r['ci_high'] is not None else None
                m={**base,**boot,**supp};m['ci_low_pp']=100*m['ci_low'] if m['ci_low'] is not None else None;m['ci_high_pp']=100*m['ci_high'] if m['ci_high'] is not None else None
                allrows.append(r);mean_rows.append(m)
                for pid,a,b in valid:observations.append({'view':view,'task':task,'provider':provider,'family':family,'metric':metric,'contrast':right+' minus '+left,'participant_id':pid,'left_num':a.numerator,'left_den':a.denominator,'right_num':b.numerator,'right_den':b.denominator,'difference_num':(b-a).numerator,'difference_den':(b-a).denominator})
        for task,provider in itertools.product(TASKS,PROVIDERS):
            full=[];excluded=[]
            for pid in by[task,provider]:
                values=tuple(ratio(index[view,task,provider,pid,c],'core_loss_rate') for c in ('RR','SA','EW'))
                if any(v is None for v in values):excluded.append(pid)
                else:full.append(values)
            f={'view':view,'task':task,'provider':provider,'family':'friedman_core','metric':'core_loss_rate','conditions':'RR,SA,EW','n_planned':len(by[task,provider]),'excluded_missing_or_undefined':len(excluded),'excluded_participants':excluded,**friedman(full,(view,task,provider))}
            fried_rows.append(f)
        for family,size in [('residue_SA_EW',4),('restoration_SA_EW',4),('core_3_contrasts',12)]:
            for group in (allrows,mean_rows):
                selected=[r for r in group if r['view']==view and r['family']==family]
                if selected:apply_holm(selected,size)
        apply_holm([f for f in fried_rows if f['view']==view],4)
    return allrows,mean_rows,fried_rows,observations


def write_csv(path,rows):
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='',encoding='utf8') as stream:
        w=csv.DictWriter(stream,fieldnames=keys);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,sort_keys=True,separators=(',',':')) if isinstance(v,(list,dict)) else v for k,v in r.items()})


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prerequisites-confirmed',action='store_true');args=ap.parse_args()
    if not args.prerequisites_confirmed:raise SystemExit('Real-data inference requires the lead prerequisite confirmation flag.')
    gate_bytes=PREFLIGHT.read_bytes();gate=json.loads(gate_bytes)
    policy=json.loads(LOCK_RECORD.read_text())
    assert gate['status']=='PASS', 'Prerequisite gate is not PASS'
    assert gate['plan_sha256']==sha(PLAN)==policy['plan_sha256']
    assert gate['operational_lock_sha256']==sha(LOCK)==policy['operational_lock_sha256']
    assert policy['v2_manifest_sha256']==sha(INPUT_MANIFEST)
    if 'v2_manifest_sha256' in gate: assert gate['v2_manifest_sha256']==sha(INPUT_MANIFEST)
    assert gate['implementation_sha256']['paired']==sha(__file__), 'Paired implementation differs from preflight'
    rows=load_rows();OUT.mkdir(parents=True,exist_ok=True)
    rank,mean,fried,obs=run_analysis(rows)
    files={'paired_wilcoxon.csv':rank,'paired_mean_permutation.csv':mean,'friedman.csv':fried,'paired_observations.csv':obs}
    for name,tab in files.items():write_csv(OUT/name,tab)
    manifest={'plan_sha256':sha(PLAN),'freeze_sha256':sha(FREEZE),'operational_lock_sha256':sha(LOCK),'operational_lock_record_sha256':sha(LOCK_RECORD),'preflight_sha256':hashlib.sha256(gate_bytes).hexdigest(),'data_sha256':sha(INPUT),'data_manifest_sha256':sha(INPUT_MANIFEST),
              'code_sha256':sha(__file__),'seed':SEED,'rng':'numpy PCG64','numpy_version':np.__version__,'python_version':platform.python_version(),
              'exact_sign_max_nonzero':EXACT_SIGN_MAX,'exact_friedman_max_complete_blocks':EXACT_FRIEDMAN_MAX,
              'monte_carlo_draws':MC,'bootstrap_draws':BOOT,'holm':'reserve untestable family slots as p=1 internally; return NA for those tests',
              'row_counts':{k:len(v) for k,v in files.items()},'outputs':{k:sha(OUT/k) for k in files},
              'no_candidate_execution':True,'no_model_calls':True,'rng_stream':'first 64 bits SHA256 of compact JSON [20261106, purpose, view, task, provider, metric, left, right] for pairs, or [20261106, purpose, view, task, provider] for Friedman; PCG64',
              'meanflip_comparisons':'exact rational integer weights; v1 used float tolerance 1e-10','signedrank_ties':'Fraction exact; average ranks, remove exact zeros'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'complete','rows':manifest['row_counts']},indent=2))

if __name__=='__main__':main()
