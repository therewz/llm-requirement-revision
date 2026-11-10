"""Offline orchestration. Imports trusted helpers only; participant code runs in isolation."""
import argparse
import concurrent.futures
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'runs/withdrawal_keys_v1/input_snapshot'
RUNTIME = ROOT / 'repositories/followup-offline-local-v2'
RUN = ROOT / 'runs/withdrawal_keys_v1'
PY = Path('/Users/rezatehrani/.pyenv/versions/3.12.6/bin/python3.12')
sys.path.insert(0, str(RUNTIME/'withdrawal_preparation/scripts'))
sys.path.insert(0, str(RUNTIME/'analysis/scripts'))
import isolated_exec_v3 as isolation
import runner
runner.PY = str(PY)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n'
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(data)
    os.replace(temp, path)


def inventory():
    rows = {}
    for phase, folder in [('P1','v1_human'), ('P2','v2_human')]:
        for p in sorted((SOURCE/'Data'/folder).glob('G*/G*/S*/src/solution.py')):
            sid = p.parents[1].name
            cell = p.parents[2].name
            r = rows.setdefault(sid, {'participant_id': sid, 'task': cell[-1], 'group': cell[:2], 'cell': cell})
            assert r['cell'] == cell
            r[phase] = {'path': str(p.relative_to(ROOT)), 'sha256': sha(p)}
            specs = sorted((p.parents[1]/'spec').glob('*.json'))
            r[phase]['specifications'] = [{'path': str(x.relative_to(ROOT)), 'sha256': sha(x)} for x in specs]
    assert len(rows) == 72
    assert all('P1' in r and 'P2' in r for r in rows.values())
    assert all(sum(r['cell'] == c for r in rows.values()) == 12 for c in ['G1A','G2A','G3A','G1B','G2B','G3B'])
    return list(rows.values())


def runtime_record():
    env = subprocess.run([str(PY), '-I', '-c',
        'import sys,json,pytest,numpy; print(json.dumps(dict(python=sys.version,pytest=pytest.__version__,numpy=numpy.__version__)))'],
        env=isolation.ENV, capture_output=True, text=True, check=True)
    return {'runtime': json.loads(env.stdout), 'python': str(PY), 'interpreter_sha256': sha(PY)}


def collect_suite_ids():
    """Collect trusted test IDs with a stub import, never participant code."""
    isolation.require_ready(str(PY))
    result = {}
    for task in 'AB':
        result[task] = {}
        for layer, stem in [('core28','28_core'),('supplied5','5_new_req')]:
            with tempfile.TemporaryDirectory(prefix='key_collection_') as d:
                d = Path(d)
                (d/'solution.py').write_text('def suggest_slots(*a,**k): pass\ndef is_allocation_feasible(*a,**k): pass\n')
                shutil.copyfile(SOURCE/'Data/test_suits'/f'{stem}_{task}_test.py',d/'test_target.py')
                p=isolation.run(str(PY),d,'module','pytest',['--collect-only','-q','-p','no:cacheprovider',
                       '--rootdir',str(d),'--confcutdir',str(d),'--noconftest',str(d/'test_target.py')],timeout=30)
                if p.returncode: raise RuntimeError('Collection failed: '+p.stderr+p.stdout)
                ids=[line.split('::',1)[1] for line in p.stdout.splitlines() if line.startswith('test_target.py::')]
                assert len(ids)==len(set(ids))==(28 if layer=='core28' else 5), ids
                result[task][layer]=sorted(ids)
    return result


def prepare():
    from task_a import build_manifest as a
    from task_b import build_manifest as b
    if (RUN/'freeze.json').exists():
        raise RuntimeError('Already frozen; use a new version for changed inputs')
    RUN.mkdir(parents=True, exist_ok=True)
    for task, fn in [('A',a),('B',b)]:
        manifest = fn()
        ids = [c['case_id'] for c in manifest['cases']]
        assert len(ids) == len(set(ids))
        write(RUN/f'answer_key_{task}.json', manifest)
    write(RUN/'inventory.json', inventory())
    write(RUN/'suite_case_ids.json', collect_suite_ids())
    sources = {str(p.relative_to(ROOT)): sha(p) for p in sorted((SOURCE/'Data').rglob('*')) if p.is_file()}
    write(RUN/'source_hashes.json', sources)
    frozen = [HERE/'task_a.py', HERE/'task_b.py', HERE/'worker.py', HERE/'assess.py',
              RUN/'answer_key_A.json', RUN/'answer_key_B.json', RUN/'inventory.json', RUN/'source_hashes.json', RUN/'suite_case_ids.json',
              HERE/'restore_inputs.py', RUN/'input_recovery.json',
              RUNTIME/'withdrawal_preparation/scripts/isolated_exec_v3.py', RUNTIME/'analysis/scripts/runner.py']
    write(RUN/'freeze.json', {'created_utc': datetime.now(timezone.utc).isoformat(),
        'evidence_class': 'OFFLINE_ORIGINAL_PROGRAM_BASELINES_NOT_MODEL_OUTPUT',
        'policy': 'P2 restriction plus controls; P1 flags retained; ISO and native views separate; no output repairs',
        'runtime': runtime_record(), 'hashes': {str(p.relative_to(ROOT)): sha(p) for p in frozen}})
    print('Frozen answer keys and 72 paired source records', flush=True)


def verify():
    frozen = json.loads((RUN/'freeze.json').read_text())
    for p, digest in frozen['hashes'].items():
        if sha(ROOT/p) != digest:
            raise RuntimeError('Frozen file changed: '+p)
    for p, digest in json.loads((RUN/'source_hashes.json').read_text()).items():
        if sha(ROOT/p) != digest:
            raise RuntimeError('Original input changed: '+p)


def targets(path, task):
    with tempfile.TemporaryDirectory(prefix='key_v1_', dir=RUN/'scratch') as scratch:
        scratch = Path(scratch).resolve()
        shutil.copyfile(path, scratch/'solution.py')
        shutil.copyfile(HERE/'worker.py', scratch/'worker.py')
        shutil.copyfile(RUN/f'answer_key_{task}.json', scratch/'cases.json')
        try:
            p = isolation.run(str(PY), scratch, 'file', scratch/'worker.py', timeout=240)
        except (subprocess.TimeoutExpired, isolation.ResourceLimit) as exc:
            return {'execution_failure': True, 'error': type(exc).__name__, 'cases': {}}
        if p.returncode or not (scratch/'out.json').exists():
            if 'sandbox_apply' in p.stderr:
                raise isolation.IsolationUnavailable(p.stderr)
            return {'execution_failure': True, 'returncode': p.returncode, 'stderr': p.stderr, 'cases': {}}
        obj = json.loads(isolation.read_regular(scratch/'out.json'))
        obj['execution_metadata'] = {'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
        expected = {c['case_id'] for c in json.loads((RUN/f'answer_key_{task}.json').read_text())['cases']}
        if not obj.get('import_error') and set(obj['cases']) != expected:
            raise RuntimeError('Incomplete/mismatched worker output')
        return obj


def execute(workers):
    verify()
    (RUN/'scratch').mkdir(exist_ok=True)
    isolation.require_ready(str(PY))
    runtime = runtime_record()
    if runtime != json.loads((RUN/'freeze.json').read_text())['runtime']:
        raise RuntimeError('Runtime changed after freeze')
    write(RUN/'environment.json', {**runtime, 'isolation_preflight': 'PASS',
          'isolation': 'sandbox-exec deny-default, no network/fork, scratch-only writes', 'workers': workers})
    rows = json.loads((RUN/'inventory.json').read_text())
    jobs = [(r, phase) for r in rows for phase in ['P1','P2']]

    def job(item):
        r, phase = item
        sid, task = r['participant_id'], r['task']
        path = ROOT/r[phase]['path']
        out = RUN/'raw'/f'{sid}_{phase}.json'
        if out.exists():
            old = json.loads(out.read_text())
            assert old['source_sha256'] == sha(path)
            assert old['freeze_sha256'] == sha(RUN/'freeze.json')
            return sid, phase, 'verified_existing'
        rec = {'participant_id': sid, 'phase': phase, 'task': task, 'group': r['group'],
               'source_path': r[phase]['path'], 'source_sha256': sha(path), 'freeze_sha256': sha(RUN/'freeze.json'),
               'evidence_class': 'FRESH_ISOLATED_ORIGINAL_PROGRAM_EXECUTION', 'started_utc': datetime.now(timezone.utc).isoformat()}
        rec['targets'] = targets(path, task)
        for layer, stem in [('core28','28_core'),('supplied5','5_new_req')]:
            suite = SOURCE/'Data/test_suits'/f'{stem}_{task}_test.py'
            result, meta = runner.run(str(path), str(suite), f'keyv1_{sid}_{phase}_{layer}')
            rec[layer] = {'results': result, 'metadata': meta, 'suite_path': str(suite.relative_to(ROOT)),
                          'suite_sha256': sha(suite), 'expected_case_count': 28 if layer=='core28' else 5}
        rec['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write(out, rec)
        return sid, phase, 'executed'

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for i, result in enumerate(pool.map(job, jobs), 1):
            if i % 12 == 0 or i == len(jobs):
                print(json.dumps({'completed': i, 'total': len(jobs), 'last': result}), flush=True)
    verify()
    write(RUN/'execution_complete.json', {'records': len(jobs), 'original_inputs_unchanged': True,
         'freeze_sha256': sha(RUN/'freeze.json'), 'completed_utc': datetime.now(timezone.utc).isoformat(),
         'model_calls': 0})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare','run','verify'])
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    {'prepare': prepare, 'verify': verify, 'run': lambda: execute(args.workers)}[args.action]()
