"""Independent outcome audit; invoke only after the preflight gate and final outputs."""
from collections import Counter, defaultdict
from fractions import Fraction as F
from itertools import combinations, islice, permutations
from pathlib import Path
import csv, hashlib, json, math
import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/statistical_analysis_v3/verification'
TABLE = ROOT / 'reports/full_analysis_v2_prelim/tables/session_metrics.csv'
PAIR = ROOT / 'reports/statistical_analysis_v3/paired'
GROUP = ROOT / 'reports/statistical_analysis_v3/groups'
MAIN = {'primary69__main','alternative62__main'}

def read(path):
    with path.open(newline='') as s:return list(csv.DictReader(s))

def phash(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def holm(raw):
    order=sorted(range(len(raw)),key=lambda i:1 if raw[i] is None else raw[i])
    results=[None]*len(raw);prev=0.0
    for rank,i in enumerate(order):
        val=1 if raw[i] is None else raw[i]
        prev=max(prev,min(1,(len(raw)-rank)*val))
        if raw[i] is not None:results[i]=prev
    return results

def signed_rank_exact(ds):
    ds=[d for d in ds if d]
    if not ds:return None,0,1
    # Rank via exact pairwise comparisons, independent of production sort/DP.
    ranks=[1+2*sum(abs(x)<abs(d) for x in ds)+sum(abs(x)==abs(d) for x in ds) for d in ds]
    observed=abs(sum((1 if d>0 else -1)*r for d,r in zip(ds,ranks)))
    dp=Counter({0:1})
    for r in ranks:
        nxt=Counter()
        for subtotal,count in dp.items():
            nxt[subtotal]+=count;nxt[subtotal+r]+=count
        dp=nxt
    total=sum(ranks)
    extreme=sum(count for subtotal,count in dp.items() if abs(2*subtotal-total)>=observed)
    draws=2**len(ds);assert sum(dp.values())==draws
    return extreme/draws,extreme,draws

def score(r,metric):
    if r['evaluated']!='True':return None
    if metric=='core_loss_rate':
        return F(int(r['PF']),int(r['core_opportunities'])) if int(r['core_opportunities']) else None
    if metric=='residue_rate':
        return F(int(r['RETAINED_count'])+int(r['PARTIAL_count']),int(r['target_n'])) if int(r['target_n']) else None
    if metric=='all_target_success':return F(int(r['all_target_success'])) if r['all_target_success'] else None
    if metric=='strict_target_success':return F(int(r['strict_target_success'])) if r['strict_target_success'] else None
    raise ValueError(metric)

def row_rank_twice(vals):
    return tuple(1+2*sum(x<v for x in vals)+sum(x==v for x in vals) for v in vals)

def friedman_exact(rows):
    n=len(rows); ranked=[row_rank_twice(row) for row in rows]
    sums=[sum(row[i] for row in ranked) for i in range(3)]
    observed=sum(x*x for x in sums);tie_sum=0
    for row in rows:
        for c in Counter(row).values():tie_sum+=c**3-c
    correction=F(1)-F(tie_sum,24*n)
    if correction==0:return None,None,0,1
    q=(F(observed,4*n)-12*n)/correction
    states={(0,0):1}
    for row in ranked:
        counts=Counter((z[0],z[1]) for z in permutations(row))
        nxt=defaultdict(int)
        for (a,b),count in states.items():
            for (x,y),multiplicity in counts.items():nxt[a+x,b+y]+=count*multiplicity
        states=nxt
    total=12*n
    extreme=sum(count for (a,b),count in states.items() if a*a+b*b+(total-a-b)**2>=observed)
    assignments=6**n;assert sum(states.values())==assignments
    return float(q),extreme/assignments,extreme,assignments

def group_exact(left,right,key,limit=3000000):
    n1=len(left);n2=len(right);n=n1+n2
    values=left+right;scale=math.lcm(*(x.denominator for x in values))
    weights=[x.numerator*(scale//x.denominator) for x in values]
    total=sum(weights);obs=abs(n1*total-n*sum(weights[:n1]));alloc=math.comb(n,n1)
    safe=(n1+n)*sum(abs(x) for x in weights)<=np.iinfo(np.int64).max
    if alloc<=limit:
        extreme=0
        for start in range(0,alloc,8192):
            # A bounded chunk avoids constructing every allocation in memory.
            if start==0:iterator=combinations(range(n),n1)
            chunk=list(islice(iterator,min(8192,alloc-start)))
            if safe:
                sums=np.asarray(weights,dtype=np.int64)[np.asarray(chunk,dtype=np.int16)].sum(axis=1)
                extreme+=int(np.count_nonzero(np.abs(n1*total-n*sums)>=obs))
            else:
                extreme+=sum(abs(n1*total-n*sum(weights[i] for i in ids))>=obs for ids in chunk)
        return extreme/alloc,extreme,alloc,'exact_all_allocations'
    seed=int.from_bytes(hashlib.sha256(json.dumps(['independent_audit',*key],separators=(',',':')).encode()).digest()[:8],'big')
    rng=np.random.Generator(np.random.PCG64(seed));extreme=0;draws=99999
    for start in range(0,draws,4096):
        size=min(4096,draws-start)
        choices=rng.permuted(np.broadcast_to(np.arange(n),(size,n)),axis=1)[:,:n1]
        if safe:
            sums=np.asarray(weights,dtype=np.int64)[choices].sum(axis=1)
            extreme+=int(np.count_nonzero(np.abs(n1*total-n*sums)>=obs))
        else:extreme+=sum(abs(n1*total-n*sum(weights[int(i)] for i in ids))>=obs for ids in choices)
    return (extreme+1)/(draws+1),extreme,draws,'independent_mc_99999_plus_one'

def sample_group(row,index,side):
    ids=json.loads(row[side+'_ids']); context=row['context'];metric=row['source_metric']
    def get(pid,arm):
        return score(index[row['view'],row['task'],row['provider'],pid,arm],metric)
    return [get(pid,'EW')-get(pid,'SA') if context=='EW_minus_SA' else get(pid,context) for pid in ids]

def paired_bootstrap(ds,key):
    text=json.dumps([20261106,'bootstrap',*key],ensure_ascii=True,separators=(',',':'))
    seed=int.from_bytes(hashlib.sha256(text.encode()).digest()[:8],'big')
    rng=np.random.Generator(np.random.PCG64(seed));a=np.asarray([float(x) for x in ds])
    samples=a[rng.integers(0,len(a),(10000,len(a)))].mean(axis=1)
    return np.quantile(samples,[.025,.975],method='linear')

def group_bootstrap(left,right,key):
    text=json.dumps([20261106,*key,'group_bootstrap'],ensure_ascii=True,separators=(',',':'))
    seed=int(hashlib.sha256(text.encode()).hexdigest()[:32],16)
    rng=np.random.default_rng(seed);a=np.asarray([float(x) for x in left]);b=np.asarray([float(x) for x in right])
    x=rng.integers(0,len(a),(10000,len(a)));y=rng.integers(0,len(b),(10000,len(b)))
    return np.quantile(b[y].mean(axis=1)-a[x].mean(axis=1),[.025,.975],method='linear')

def selected_tests(rows,method_col,p_col,q_col):
    candidates=[r for r in rows if r['view'] in MAIN and r[method_col].startswith('monte_carlo') and r[q_col]]
    selected=[r for r in candidates if float(r[q_col])<=.10]
    # The policy requires at least one non-significant MC test if available.
    nonsignificant=next((r for r in candidates if float(r[q_col])>=.05 and r not in selected),None)
    if nonsignificant is not None:selected.append(nonsignificant)
    return selected

def main():
    gate=json.loads((ROOT/'reports/statistical_analysis_v3/PREFLIGHT.json').read_text())
    assert gate['status']=='PASS'
    pm=json.loads((PAIR/'manifest.json').read_text());gm=json.loads((GROUP/'analysis_manifest.json').read_text())
    for name,sha in pm['outputs'].items():assert phash(PAIR/name)==sha
    assert phash(GROUP/'group_tests.csv')==gm['output_sha256']
    table=read(TABLE);by={(r['view'],r['task'],r['provider'],r['participant_id'],r['condition']):r for r in table}
    paired=read(PAIR/'paired_wilcoxon.csv');meanflip=read(PAIR/'paired_mean_permutation.csv')
    groups=read(GROUP/'group_tests.csv');fried=read(PAIR/'friedman.csv');obs=read(PAIR/'paired_observations.csv')
    observations=defaultdict(list)
    for r in obs:
        observations[(r['view'],r['task'],r['provider'],r['metric'],r['contrast'])].append(r)
    # Independently check Holm adjustment for every family in every view.
    families=defaultdict(list)
    for i,r in enumerate(paired):families[(r['view'],r['family'])].append(i)
    for i,r in enumerate(fried):families[(r['view'],'friedman')].append(('f',i))
    holm_checked=0
    for family,indices in families.items():
        table_ref=fried if indices and isinstance(indices[0],tuple) else paired
        ix=[i[1] if isinstance(i,tuple) else i for i in indices]
        raw=[float(table_ref[i]['p']) if table_ref[i]['p'] else None for i in ix]
        for i,q in zip(ix,holm(raw)):
            stored=table_ref[i]['p_holm']
            assert (q is None and not stored) or (q is not None and stored and abs(q-float(stored))<1e-12),(family,i,q,stored)
            holm_checked+=1
    for view in sorted({r['view'] for r in groups}):
        rr=[r for r in groups if r['view']==view];assert len(rr)==108
        expected=holm([float(r['p_raw']) if r['p_raw'] else None for r in rr])
        for r,q in zip(rr,expected):
            assert (q is None and not r['p_holm']) or (q is not None and r['p_holm'] and abs(q-float(r['p_holm']))<1e-12)
            holm_checked+=1
    # Uniform numerical verification of every informative main/alternative
    # signed-rank result. This expands the predeclared MC cutoff check and
    # avoids selecting favorable results.
    ps=[r for r in paired if r['view'] in MAIN and r['status']=='tested']
    required_paired=selected_tests(paired,'p_method','p','p_holm')
    assert all(r in ps for r in required_paired)
    pair_checks=[];pair_replacements={}
    for r in ps:
        k=(r['view'],r['task'],r['provider'],r['metric'],r['contrast'])
        oo=observations[k]; ds=[F(int(x['difference_num']),int(x['difference_den'])) for x in oo]
        assert len(ds)==int(r['n_pairs'])
        exact,extreme,draws=signed_rank_exact(ds)
        if r['p_method'].startswith('exact'):assert abs(exact-float(r['p']))<1e-12
        left,right=r['contrast'].split(' minus ')[::-1]
        ci=paired_bootstrap(ds,(r['view'],r['task'],r['provider'],r['metric'],left,right))
        assert abs(ci[0]-float(r['ci_low']))<1e-12 and abs(ci[1]-float(r['ci_high']))<1e-12
        check={'key':k,'n_pairs':len(ds),'n_nonzero':sum(bool(x) for x in ds),'primary_p':float(r['p']),'primary_holm':float(r['p_holm']),'exact_p':exact,'extreme':extreme,'assignments':draws,'primary_method':r['p_method'],'bootstrap_verified':True}
        pair_checks.append(check);pair_replacements[k]=exact
    # Independently verify the supplementary v1-style mean sign-flip test on
    # all SA/EW main/alternative core and restoration cells. Homogeneous
    # directions have two extreme assignments; other small cases are exact.
    mean_checks=[]
    for r in meanflip:
        if r['view'] not in MAIN or r['contrast']!='EW minus SA' or r['metric'] not in ('core_loss_rate','restoration_rate'):continue
        k=(r['view'],r['task'],r['provider'],r['metric'],r['contrast'])
        ds=[F(int(x['difference_num']),int(x['difference_den'])) for x in observations[k]]
        nz=[d for d in ds if d]
        if not nz:
            assert r['status']=='no_variation' and not r['p']
            mean_checks.append({'key':k,'status':'no_variation','n_nonzero':0});continue
        if all(d>0 for d in nz) or all(d<0 for d in nz):
            exact=2/(2**len(nz));method='two_extreme_signs'
        elif len(nz)<=20:
            original=abs(sum(nz,F()));extreme=0
            for signs in __import__('itertools').product((-1,1),repeat=len(nz)):
                extreme+=abs(sum((v*s for v,s in zip(nz,signs)),F()))>=original
            exact=extreme/(2**len(nz));method='exact_fraction_sign_enumeration'
        else:
            mean_checks.append({'key':k,'status':'mixed_sign_over20_not_audited','n_nonzero':len(nz)});continue
        assert abs(exact-float(r['p']))<1e-12,(k,exact,r['p'])
        mean_checks.append({'key':k,'status':'verified','n_nonzero':len(nz),'exact_p':exact,'method':method})
    # Exact tied-rank Friedman distributions for all eight main/alternative cells.
    fried_checks=[]
    for r in fried:
        if r['view'] not in MAIN:continue
        candidates=sorted({z['participant_id'] for z in table if z['view']==r['view'] and z['task']==r['task'] and z['provider']==r['provider']})
        blocks=[]
        for pid in candidates:
            vv=tuple(score(by[r['view'],r['task'],r['provider'],pid,arm],'core_loss_rate') for arm in ('RR','SA','EW'))
            if all(x is not None for x in vv):blocks.append(vv)
        q,exact,extreme,assignments=friedman_exact(blocks)
        scipy_q=stats.friedmanchisquare(*np.asarray([[float(x) for x in block] for block in blocks]).T).statistic
        assert abs(q-float(r['friedman_q']))<1e-10 and abs(q-scipy_q)<1e-9
        fried_checks.append({'view':r['view'],'task':r['task'],'provider':r['provider'],'n':len(blocks),'q':q,'primary_p':float(r['p']),'primary_holm':float(r['p_holm']),'exact_p':exact,'extreme':str(extreme),'assignments':str(assignments)})
        print('Friedman independently checked:',r['view'],r['task'],r['provider'],flush=True)
    # Uniformly audit ALL informative group cells in the two main cohorts.
    # The lead requested this after seeing Monte Carlo-floor counts. This
    # expands rather than substitutes for the pre-specified cutoff rule.
    gs=[r for r in groups if r['view'] in MAIN and r['status']=='tested']
    required_groups=selected_tests(groups,'permutation_method','p_raw','p_holm')
    assert all(r in gs for r in required_groups)
    group_checks=[];group_replacements={};distribution_cache={}
    for r in gs:
        k=(r['view'],r['task'],r['provider'],r['context'],r['metric'],r['group_left'],r['group_right'])
        a=sample_group(r,by,'left');b=sample_group(r,by,'right')
        assert len(a)==int(r['n_left']) and len(b)==int(r['n_right'])
        assert abs(float(sum(b,F())/len(b)-sum(a,F())/len(a))-float(r['difference']))<1e-12
        # Swapping labels and reordering values does not change a two-sided
        # exact null; cache only exact results from identical sample values.
        cache_key=min((tuple(sorted(a)),tuple(sorted(b))),(tuple(sorted(b)),tuple(sorted(a))))
        if cache_key in distribution_cache:
            independent,extreme,draws,method=distribution_cache[cache_key]
        else:
            independent,extreme,draws,method=group_exact(a,b,k)
            if method=='exact_all_allocations':distribution_cache[cache_key]=(independent,extreme,draws,method)
        if r['permutation_method'].startswith('exact'):assert abs(independent-float(r['p_raw']))<1e-12
        ci=group_bootstrap(a,b,k);assert abs(ci[0]-float(r['ci_low']))<1e-12 and abs(ci[1]-float(r['ci_high']))<1e-12
        check={'key':k,'n_left':len(a),'n_right':len(b),'primary_p':float(r['p_raw']),'primary_holm':float(r['p_holm']),'independent_p':independent,'extreme':extreme,'draws':draws,'independent_method':method,'bootstrap_verified':True}
        group_checks.append(check);group_replacements[k]=independent
        print('Group independently checked:',*k,'permutations',draws,flush=True)
    # Substitute validated tails into entire originally fixed Holm families; retained
    # MC values make these partial-exact audits, never fully exact family inference.
    threshold_changes=[]
    fried_replacements={(r['view'],r['task'],r['provider']):r['exact_p'] for r in fried_checks}
    for table_ref,replacements,keyfun,pcol in [
        (paired,pair_replacements,lambda r:(r['view'],r['task'],r['provider'],r['metric'],r['contrast']),'p'),
        (fried,fried_replacements,lambda r:(r['view'],r['task'],r['provider']),'p'),
        (groups,group_replacements,lambda r:(r['view'],r['task'],r['provider'],r['context'],r['metric'],r['group_left'],r['group_right']),'p_raw')]:
        fgroups=defaultdict(list)
        for r in table_ref:
            if r['view'] in MAIN:fgroups[(r['view'],r.get('family','group'))].append(r)
        for family,rr in fgroups.items():
            raw=[replacements.get(keyfun(r),float(r[pcol]) if r[pcol] else None) for r in rr]
            for r,q in zip(rr,holm(raw)):
                original=float(r['p_holm']) if r['p_holm'] else None
                if original is not None and q is not None and (original<.05)!=(q<.05):
                    threshold_changes.append({'family':family,'key':keyfun(r),'primary_holm':original,'partial_recalibration_holm':q})
    # Original-limit and strict-control facts checked independently at the subject level.
    s=[r for r in paired if r['view']=='primary69__original_limit' and r['task']=='B' and r['provider']=='openai' and r['metric']=='core_loss_rate' and r['contrast']=='EW minus SA']
    assert len(s)==1 and int(s[0]['n_planned'])==34 and int(s[0]['n_pairs'])==33 and json.loads(s[0]['excluded_participants'])==['S0033']
    strict=[r for r in obs if r['view']=='primary69__strict_controls' and r['task']=='B' and r['provider']=='openai' and r['metric']=='restoration_plus_linked_controls' and r['participant_id']=='S0069']
    assert len(strict)==1 and F(int(strict[0]['left_num']),int(strict[0]['left_den']))==F(1,2) and F(int(strict[0]['right_num']),int(strict[0]['right_den']))==F(1,2)
    ties=[r for r in paired if r['view'] in MAIN and r['metric']=='residue_rate']
    assert len(ties)==8 and all(r['status']=='no_variation' and not r['p'] and not r['p_holm'] for r in ties)
    result={'status':'PASS' if not threshold_changes else 'SIMULATION_SENSITIVE',
            'policy_sha256':phash(ROOT/'planning/STATISTICAL_ANALYSIS_V3_SIMULATION_AUDIT.md'),
            'paired_checks':pair_checks,'mean_permutation_checks':mean_checks,'friedman_checks':fried_checks,'group_checks':group_checks,
            'independent_holm_rows_checked':holm_checked,'partial_exact_recalibration_threshold_changes':threshold_changes,
            'original_limit_S0033_and_strict_S0069':'PASS','all_tied_residue_no_informative_p':'PASS',
        'method_note':'Original planned MC p-values remain primary; recalibrations only audit the same hypotheses. Full main/alternative informative tests were audited after lead expanded coverage; any independent MC fallback remains labeled.',
        'group_exact_distributions_computed':len(distribution_cache),
            'candidate_execution':False,'model_calls':False}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'OUTCOME_VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'paired':len(pair_checks),'friedman':len(fried_checks),'group':len(group_checks),'holm_rows':holm_checked,'threshold_changes':threshold_changes},indent=2))

if __name__=='__main__':main()
