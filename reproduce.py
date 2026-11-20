"""Reproduce the released results from saved data without running participant programs or calling models."""
from __future__ import annotations
import argparse
from collections import defaultdict
import csv
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
HASH=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def check():
    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    for rel,record in manifest['files'].items():
        p=ROOT/rel
        if not p.is_file() or p.is_symlink() or HASH(p)!=record['sha256']:
            raise ValueError('Missing or changed package file: '+rel)
    mapping=json.loads((ROOT/'metadata/source_map.json').read_text())
    for old,new in mapping.items():
        if Path(old).is_absolute() or '..' in Path(old).parts:
            raise ValueError('Unsafe original relative path')
        if new not in manifest['files']:raise ValueError('Unbound source mapping: '+new)
    programs=list(csv.DictReader((ROOT/'metadata/programs.csv').open()))
    sessions=list(csv.DictReader((ROOT/'metadata/sessions.csv').open()))
    assert len(programs)==72 and len(sessions)==len({r['session_id'] for r in sessions})==432
    assert sum(r['eligible_main69']=='True' for r in programs)==69
    assert sum(r['eligible_alternative62']=='True' for r in programs)==62
    assert sum(r['prepared_changed']=='True' for r in programs)==13
    byid={r['participant_id']:r for r in programs}
    cleaners={task:load('replication_prepare_'+task,ROOT/'workflow/cleaned_starts_v1'/('task_'+task.lower()+'.py')) for task in 'AB'}
    for p in programs:
        original=(ROOT/p['original_phase_II']).read_bytes()
        prepared=(ROOT/p['Repo_V2']).read_bytes()
        assert hashlib.sha256(original).hexdigest()==p['original_phase_II_sha256']
        assert hashlib.sha256(prepared).hexdigest()==p['Repo_V2_sha256']
        reconstructed,reasons=cleaners[p['task']].clean(p['participant_id'],original,p['original_input_profile'])
        assert reconstructed==prepared,p['participant_id']
        assert bool(reasons)==(p['prepared_changed']=='True')
    for row in sessions:
        assert (ROOT/row['evaluation']).is_file(),row['session_id']
        b=ROOT/row['session_dir']
        e=json.loads((ROOT/row['evaluation']).read_text())
        p=byid[row['participant_id']]
        plan=json.loads((b/'plan.json').read_text())['plan']
        assert plan['source_sha256']==p['Repo_V2_sha256'],row['session_id']
        prompt=ROOT/f'model_inputs/Task_{p["task"]}/{p["group"]}/{p["participant_id"]}/{row["condition"]}/prompt.txt'
        assert HASH(prompt)==plan['prompt_sha256'],row['session_id']
        final=(b/'extra_turn/final.py') if row['session_id']=='S0033_SA_openai_r1' else b/'final.py'
        assert HASH(final)==e['binding']['final_source_sha256'],row['session_id']
    print('Package integrity: PASS; 72 programs, 432 complete grades, 69/62 cohorts, 13 prepared sources.',flush=True)
    return manifest,mapping

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def materialize(work,mapping):
    for old,new in mapping.items():
        dest=work/old;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/new,dest)

def read(path):return list(csv.DictReader(Path(path).open(newline='')))

def compare(folder,reference,comparisons):
    expected_names={p.name for p in (ROOT/reference).glob('*.csv')}
    actual_names={p.name for p in folder.glob('*.csv')}
    if actual_names!=expected_names:
        raise ValueError(f'Output inventory differs for {reference}: missing={sorted(expected_names-actual_names)}, extra={sorted(actual_names-expected_names)}')
    for p in sorted(folder.glob('*.csv')):
        expected=ROOT/reference/p.name
        if not expected.is_file() or p.read_bytes()!=expected.read_bytes():
            raise ValueError('Reproduced table differs: '+str(p))
        comparisons.append({'file':str(p.relative_to(folder.parent)), 'reference':str(expected.relative_to(ROOT)),
                            'sha256':HASH(p),'same_bytes':True})

def descriptive(work,out,comparisons):
    m=load('replication_descriptive',work/'code/full_analysis_v2_prelim/analyze.py')
    m.OUT=out/'descriptive';m.main()
    compare(m.OUT/'tables','analysis/descriptive',comparisons)
    for p in (m.OUT/'tables').glob('*.csv'):
        shutil.copy2(p,work/'reports/full_analysis_v2_prelim/tables'/p.name)
    return read(m.OUT/'tables/session_metrics.csv')

def statistics(work,out,rows,comparisons):
    paired=load('replication_paired',work/'code/statistical_analysis_v3_paired/analyze.py')
    group=load('replication_groups',work/'code/statistical_analysis_v3_groups/analyze.py')
    dest=work/'computed/statistics';dest.mkdir(parents=True)
    rank,means,fried,observations=paired.run_analysis(rows)
    tables={'paired_wilcoxon.csv':rank,'paired_mean_permutation.csv':means,'friedman.csv':fried,'paired_observations.csv':observations}
    for name,tab in tables.items():paired.write_csv(dest/name,tab)
    byview=defaultdict(dict)
    for r in rows:
        key=(r['task'],r['provider'],r['participant_id'],r['condition'])
        assert key not in byview[r['view']]
        byview[r['view']][key]=r
    assert len(byview)==24
    groups=[]
    for view in sorted(byview):
        groups.extend(group.analyze_view(view,byview[view]))
        print('Group statistics:',view,flush=True)
    group.write_csv(dest/'group_tests.csv',groups)
    expected = ROOT/'analysis/statistics/paired_observations.csv'
    if HASH(dest/'paired_observations.csv') != HASH(expected):
        raise ValueError('The paired observations differ from the released observations.')
    comparisons.append({'reference':'analysis/statistics/paired_observations.csv','sha256':HASH(expected),'same_bytes':True})
    pairdir=work/'reports/statistical_analysis_v3/paired';pairdir.mkdir(parents=True,exist_ok=True)
    groupdir=work/'reports/statistical_analysis_v3/groups';groupdir.mkdir(parents=True,exist_ok=True)
    for name in tables:shutil.copy2(dest/name,pairdir/name)
    shutil.copy2(dest/'group_tests.csv',groupdir/'group_tests.csv')

def exact(work,out,comparisons):
    helpers=work/'code/statistical_analysis_v3_independent'
    sys.path.insert(0,str(helpers))
    try:
        sys.modules.pop('outcome_checks',None)
        m=load('replication_exact',helpers/'all_view_precision.py')
        m.DEST=work/'computed/exact'
        m.main()
        target=work/'reports/statistical_analysis_v3/verification/all_views_exact_v1'
        target.mkdir(parents=True,exist_ok=True)
        for p in m.DEST.glob('*.csv'):shutil.copy2(p,target/p.name)
        shutil.copy2(m.DEST/'SUMMARY.json',target/'SUMMARY.json')
    finally:sys.path.remove(str(helpers))

def reporting(work,out,comparisons):
    m=load('replication_reporting',work/'code/statistical_analysis_v3_lead/build_reporting_tables.py')
    m.OUT=out/'statistics/reporting';m.main()
    compare(m.OUT,'analysis/statistics/reporting',comparisons)
def conflicts(work,out,comparisons):
    m=load('replication_expanded_conflicts',work/'code/results_readiness_conflicts_v1/analyze.py')
    m.DEFAULT_OUT=out/'expanded_conflicts';m.POLICY=ROOT/'metadata/expanded_conflict_policy.json'
    previous=sys.argv
    try:
        sys.argv=[m.__file__];m.main()
    finally:sys.argv=previous
    compare(m.DEFAULT_OUT/'tables','analysis/sensitivity/expanded_conflicts',comparisons)

def figures(out, comparisons):
    source = ROOT/'analysis/figures/build_figures.py'
    subprocess.run([sys.executable, str(source), '--output', str(out/'figures')],check=True)
    for line in (ROOT/'analysis/figures/plot_data.sha256').read_text().splitlines():
        expected, name = line.split('  ', 1)
        if HASH(out/'figures'/name) != expected:
            raise ValueError('Figure data differs: '+name)
        comparisons.append({'file':'figures/'+name,'sha256':expected,'same_bytes':True})


def manual(out, comparisons):
    script=ROOT/'manual_review/analyze.py'
    target=out/'manual_review'
    subprocess.run([sys.executable,str(script),'--output',str(target)],check=True)
    expected={p.name for p in (ROOT/'manual_review/results').iterdir() if p.is_file()}
    actual={p.name for p in target.iterdir() if p.is_file()}
    if not expected or actual != expected:
        raise ValueError('Manual result inventory differs.')
    for name in sorted(expected):
        ref=ROOT/'manual_review/results'/name
        if HASH(target/name)!=HASH(ref):
            raise ValueError('Manual result differs: '+name)
        comparisons.append({'reference':str(ref.relative_to(ROOT)),'sha256':HASH(ref),'same_bytes':True})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part',choices=['check','descriptive','statistics','exact','conflicts','figures','supplement','manual','all'],default='check')
    parser.add_argument('--output',default='outputs/reproduction')
    args=parser.parse_args()
    _,mapping=check()
    if args.part=='check':return
    out=Path(args.output);out=(ROOT/out if not out.is_absolute() else out).resolve()
    allowed=(ROOT/'outputs').resolve()
    if not out.is_relative_to(allowed) or out==allowed or out.exists():
        parser.error('--output must be a new directory under outputs/. Existing output is never overwritten.')
    out.mkdir(parents=True)
    comparisons=[];started=time.monotonic()
    if args.part in ('descriptive','statistics','exact','conflicts','all'):
        with tempfile.TemporaryDirectory(prefix='workspace_',dir=out) as scratch:
            work=Path(scratch)
            materialize(work,mapping)
            if args.part in ('descriptive','all'):
                rows=descriptive(work,out,comparisons)
            else:
                rows=read(work/'reports/full_analysis_v2_prelim/tables/session_metrics.csv')
            if args.part in ('statistics','exact','conflicts','all'):
                statistics(work,out,rows,comparisons)
                exact(work,out,comparisons)
                reporting(work,out,comparisons)
            if args.part in ('conflicts','all'):
                conflicts(work,out,comparisons)
    if args.part in ('figures','all'):
        figures(out, comparisons)
    if args.part in ('supplement','all'):
        script=ROOT/'analysis/supplement/scripts/verify.py'
        subprocess.run([sys.executable,str(script),'--output',str(out/'supplement')],check=True)
        for name in ('joint_success', 'recovery', 'count_audit'):
            compare(out/'supplement'/name, 'analysis/supplement/'+name, comparisons)
    if args.part in ('manual','all'):
        manual(out,comparisons)
    result={'status':'PASS','part':args.part,'seconds':time.monotonic()-started,'compared_tables':comparisons,
            'model_calls':0,'candidate_execution':0,'saved_grades':432,'main_programs':69,'alternative_programs':62}
    (out/'REPRODUCTION.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Reproduction complete:',out,flush=True)

if __name__=='__main__':main()
