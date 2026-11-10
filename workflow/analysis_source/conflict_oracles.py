"""Independent exact numerical oracles; no production imports."""
from fractions import Fraction as F
from itertools import product, permutations
from math import lcm, gcd, comb
import numpy as np
from scipy.stats import rankdata, permutation_test, wilcoxon, PermutationMethod, friedmanchisquare

def integerize(values):
    vals=list(map(F,values)); scale=lcm(*(v.denominator for v in vals)) if vals else 1
    ints=[v.numerator*(scale//v.denominator) for v in vals]
    divisor=gcd(*ints) if ints else 1
    if divisor: ints=[x//divisor for x in ints]
    assert max(map(abs, ints),default=0)*max(1,len(ints))*4 < 2**63
    return tuple(ints)

def half_sums(weights):
    out=np.array([0],dtype=np.int64)
    for w in weights: out=np.concatenate((out,out+w))
    return out

def tails(a,b,low,high):
    """Count a+b <=low OR >=high; disjoint caller thresholds."""
    b=np.sort(b)
    return int(np.searchsorted(b,low-a,side='right').sum()+
               (len(b)-np.searchsorted(b,high-a,side='left')).sum())

def sign_exact(weights, observed):
    weights=tuple(abs(int(v)) for v in weights if v)
    observed=abs(int(observed)); n=len(weights)
    if not observed: return F(1),2**n,2**n
    total=sum(weights); cut=n//2
    a,b=half_sums(weights[:cut]),half_sums(weights[cut:])
    extreme=tails(a,b,(total-observed)//2,-(-(total+observed)//2))
    return F(extreme,2**n),extreme,2**n

def rank2(differences):
    d=[F(x) for x in differences if x]
    unique=sorted(set(map(abs,d))); categories={x:i for i,x in enumerate(unique)}
    ranks=rankdata([categories[abs(v)] for v in d],method='average')*2
    return tuple(map(int,ranks)),d

def signed_rank(differences):
    ranks,d=rank2(differences)
    if not d:return None,0,0,0
    observed=sum(r*(1 if v>0 else -1) for r,v in zip(ranks,d))
    p,e,a=sign_exact(ranks,observed)
    return p,F(observed,2),e,a

def mean_sign(differences):
    d=[F(x) for x in differences if x]
    if not d:return None,0,0
    w=integerize(d);return sign_exact(w,sum(w))

def cardinality_sums(weights):
    buckets=[np.array([0],dtype=np.int64)]
    for w in weights:
        nxt=[None]*(len(buckets)+1)
        for k in range(len(nxt)):
            chunks=[]
            if k<len(buckets):chunks.append(buckets[k])
            if k>0:chunks.append(buckets[k-1]+w)
            nxt[k]=np.concatenate(chunks)
        buckets=nxt
    return buckets

def group_exact(left,right):
    left,right=list(map(F,left)),list(map(F,right)); n=len(left);m=len(right)
    if min(n,m)<2 or len(set(left+right))==1:return None,0,0
    vals=integerize(left+right); total=sum(vals); N=n+m
    observed=abs(n*total-N*sum(vals[:n]))
    assignments=comb(N,n)
    if observed==0:return F(1),assignments,assignments
    cut=N//2;a=cardinality_sums(vals[:cut]);b=cardinality_sums(vals[cut:])
    extreme=0
    for ka,sa in enumerate(a):
        kb=n-ka
        if 0<=kb<len(b):
            extreme+=tails(sa,b[kb],(n*total-observed)//N,-(-(n*total+observed)//N))
    return F(extreme,assignments),extreme,assignments

def group_brute(left,right):
    # SciPy uses an independent permutation engine on tractable allocations.
    def stat(x,y,axis):return np.abs(np.mean(y,axis=axis)-np.mean(x,axis=axis))
    return permutation_test((np.array(list(map(F,left)),dtype=float),np.array(list(map(F,right)),dtype=float)),stat,
        permutation_type='independent',alternative='greater',n_resamples=np.inf).pvalue

def holm(raw):
    values=[F(1) if p is None else F(p) for p in raw]
    order=sorted(range(len(values)),key=lambda i:(values[i],i));out=[None]*len(values);peak=F(0)
    for j,i in enumerate(order):
        peak=max(peak,values[i]*(len(values)-j));out[i]=min(F(1),peak) if raw[i] is not None else None
    return out

def friedman_small(blocks):
    a=np.array(blocks,dtype=float);r=rankdata(a,axis=1);obs=float(np.sum(r.sum(axis=0)**2))
    e=0;count=0
    for perms in product(list(permutations(range(3))),repeat=len(a)):
        sums=np.zeros(3)
        for row,p in zip(r,perms):sums+=row[list(p)]
        count+=1;e+=float(sums@sums)>=obs-1e-10
    return F(e,count),friedmanchisquare(*a.T).statistic
