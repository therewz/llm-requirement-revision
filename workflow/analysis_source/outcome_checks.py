"""Exact tests and resampling methods for paired and independent groups."""
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
