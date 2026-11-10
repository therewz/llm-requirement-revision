"""Fresh hidden evaluation after a verified terminal editing session.

The agent runtime is no longer attached. A new read-only isolated workspace holds
the final source and hidden evaluator material; none is returned to the agent.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'runs/withdrawal_keys_v1'
FREEZE_SHA256 = 'b4f53052786d7ea25229d0cd4bc0dff96250b0ec5083a8f6b1f1e9bc22e6ac82'
LIMITS = {'python_timeout_seconds': 240, 'output_bytes': 262144, 'memory_mb': 512}


def _module(name):
    spec = importlib.util.spec_from_file_location('bounded_evaluator_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = _module('runtime')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _inputs(task):
    if task not in ('A', 'B'):
        raise ValueError('Unknown task')
    freeze_bytes = (BASE / 'freeze.json').read_bytes()
    if sha(freeze_bytes) != FREEZE_SHA256:
        raise ValueError('Frozen evaluator record changed')
    freeze = json.loads(freeze_bytes)
    if sha(runtime.PYTHON.read_bytes()) != freeze['runtime']['interpreter_sha256']:
        raise ValueError('Frozen evaluation interpreter changed')
    def checked(relative):
        data = (ROOT / relative).read_bytes()
        if sha(data) != freeze['hashes'][relative]:
            raise ValueError('Frozen evaluator input changed: ' + relative)
        return data
    source_hashes = json.loads(checked('runs/withdrawal_keys_v1/source_hashes.json'))
    ids = json.loads(checked('runs/withdrawal_keys_v1/suite_case_ids.json'))[task]
    key = checked(f'runs/withdrawal_keys_v1/answer_key_{task}.json')
    worker = checked('code/withdrawal_keys_v1/worker.py').decode()
    old = "    with open('out.json', 'w') as f:\n        json.dump(result, f, allow_nan=False)"
    if worker.count(old) != 1:
        raise ValueError('Unexpected original target worker output boundary')
    worker = worker.replace(old, "    print(json.dumps(result, allow_nan=False))")
    suites = {}
    for layer, stem in [('core28', '28_core'), ('supplied5', '5_new_req')]:
        relative = f'runs/withdrawal_keys_v1/input_snapshot/Data/test_suits/{stem}_{task}_test.py'
        data = (ROOT / relative).read_bytes()
        if sha(data) != source_hashes[relative]:
            raise ValueError('Original hidden suite changed: ' + relative)
        suites[layer] = {'path': relative, 'bytes': data, 'sha256': sha(data), 'ids': ids[layer]}
    return key, worker, suites


def _suite_worker():
    site = runtime.PYTHON.resolve().parent.parent / 'lib/python3.12/site-packages'
    return '''import contextlib,json,os,signal,sys
sys.path.insert(0,SITE_PACKAGES)
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
import pytest
class EvaluationTimeout(Exception): pass
def alarm(*args): raise EvaluationTimeout('two-second per-test evaluation limit')
signal.signal(signal.SIGALRM,alarm)
class Recorder:
    def __init__(self):
        self.results={};self.collected=[];self.collection_error=None
    def pytest_collection_finish(self,session):
        self.collected=[item.nodeid.split('::')[-1] for item in session.items]
    def pytest_collectreport(self,report):
        if report.failed: self.collection_error=str(report.longrepr)[:1000]
    def pytest_runtest_setup(self,item):
        signal.setitimer(signal.ITIMER_REAL,2)
    def pytest_runtest_logreport(self,report):
        name=report.nodeid.split('::')[-1]
        if report.failed:
            self.results[name]=['failed' if report.when=='call' else 'error',str(report.longrepr)[:300]]
        elif report.skipped: self.results.setdefault(name,['skipped',str(report.longrepr)[:300]])
        elif report.when=='call': self.results.setdefault(name,['passed',''])
        if report.when=='teardown': signal.setitimer(signal.ITIMER_REAL,0)
recorder=Recorder()
with open(os.devnull,'w') as sink:
    with contextlib.redirect_stdout(sink),contextlib.redirect_stderr(sink):
        exitcode=pytest.main(['-q','-s','-p','no:cacheprovider','--rootdir',os.getcwd(),
                             '--confcutdir',os.getcwd(),'--noconftest','test_target.py'],plugins=[recorder])
signal.setitimer(signal.ITIMER_REAL,0)
print(json.dumps({'results':recorder.results,'collected':recorder.collected,
                  'collection_error':recorder.collection_error,'pytest_exitcode':int(exitcode)},allow_nan=False))
'''.replace('SITE_PACKAGES', repr(str(site)), 1)


def _workspace_source(workspace, source):
    (workspace / 'src').mkdir()
    for relative in ('solution.py', 'solution2.py', 'src/solution.py'):
        (workspace / relative).write_bytes(source)


def _run_json(workspace, worker, limits):
    result = runtime._run_isolated(workspace, worker, {**runtime.DEFAULTS, **LIMITS, **(limits or {})})
    metadata = {k: v for k, v in result.items() if k not in ('stdout', 'stderr')}
    metadata.update({'stdout_tail': result['stdout'][-2000:], 'stderr_tail': result['stderr'][-2000:],
                     'timed_out_file': result['status'] == 'timeout'})
    if result['status'] != 'ok':
        return None, metadata
    try:
        parsed = json.loads(result['stdout'])
    except (ValueError, TypeError):
        metadata['invalid_evaluator_output'] = True
        return None, metadata
    if not isinstance(parsed, dict):
        metadata['invalid_evaluator_output'] = True
        return None, metadata
    return parsed, metadata


def evaluate_source_bytes(source, task, *, metadata=None, limits=None):
    """Synthetic test entry point; always labels its evidence as synthetic.

    Production callers use evaluate_session, which verifies terminal evidence first.
    """
    if not isinstance(source, bytes) or len(source) > runtime.DEFAULTS['file_bytes']:
        raise ValueError('Expected a bounded source byte string')
    key, target_worker, suites = _inputs(task)
    scratch = ROOT / 'tmp/bounded_evaluation_v1'; scratch.mkdir(exist_ok=True, parents=True)
    runtime.isolation_preflight(scratch)
    record = {**(metadata or {}), 'task': task, 'source_sha256': sha(source),
              'freeze_sha256': FREEZE_SHA256, 'evidence_class': 'SYNTHETIC_OFFLINE_EVALUATION',
              'evaluation_complete': True, 'no_feedback_to_agent': True}
    with tempfile.TemporaryDirectory(prefix='targets_', dir=scratch) as temporary:
        workspace = Path(temporary).resolve()
        _workspace_source(workspace, source)
        (workspace / 'cases.json').write_bytes(key)
        worker = workspace / 'worker.py'; worker.write_text(target_worker)
        obj, execution = _run_json(workspace, worker, limits)
        expected = {case['case_id'] for case in json.loads(key)['cases']}
        valid = obj is not None and isinstance(obj.get('cases'), dict) and 'import_error' in obj
        complete = valid and obj['import_error'] is None and set(obj['cases']) == expected
        if obj is None or not valid:
            obj = {'import_error': None, 'cases': {}, 'execution_failure': True}
        obj.update({'execution_metadata': execution, 'expected_case_count': len(expected), 'complete': complete,
                    'answer_key_sha256': sha(key)})
        record['targets'] = obj
        record['evaluation_complete'] &= complete
    for layer, suite in suites.items():
        with tempfile.TemporaryDirectory(prefix=layer + '_', dir=scratch) as temporary:
            workspace = Path(temporary).resolve()
            _workspace_source(workspace, source)
            (workspace / 'test_target.py').write_bytes(suite['bytes'])
            worker = workspace / 'suite_worker.py'; worker.write_text(_suite_worker())
            obj, execution = _run_json(workspace, worker, limits)
            valid = obj is not None and isinstance(obj.get('results'), dict) and isinstance(obj.get('collected'), list)
            if not valid:
                obj = {'results': {}, 'collected': [], 'collection_error': 'Missing or malformed evaluator output',
                       'pytest_exitcode': None}
            expected = set(suite['ids'])
            complete = (valid and type(obj.get('pytest_exitcode')) is int and obj['pytest_exitcode'] in (0, 1)
                        and obj.get('collection_error') is None and len(obj['collected']) == len(expected)
                        and set(obj['collected']) == expected and set(obj['results']) == expected
                        and all(isinstance(x, list) and len(x) == 2 and x[0] in ('passed', 'failed', 'error', 'skipped')
                                and isinstance(x[1], str) for x in obj['results'].values()))
            execution.update({'collection_error': obj['collection_error'], 'pytest_exitcode': obj['pytest_exitcode'],
                              'collected_case_ids': obj['collected'], 'complete': complete})
            record[layer] = {'results': obj['results'], 'metadata': execution, 'suite_path': suite['path'],
                             'suite_sha256': suite['sha256'], 'expected_case_count': len(expected), 'complete': complete}
            record['evaluation_complete'] &= complete
    return record


def evaluate_session(plan, session_dir, adapter, *, output_path=None):
    """Verify a completed session before exposing its final source to hidden tests."""
    engine = _module('engine')
    result = engine.verify_session(plan, session_dir, adapter)
    if result['status'] != 'completed':
        raise ValueError('Only verified completed sessions may enter this evaluator')
    source = runtime._read_regular(Path(session_dir) / 'final.py', runtime.DEFAULTS['file_bytes'])
    if sha(source) != result['final_source_sha256']:
        raise ValueError('Final source hash mismatch')
    identity = {k: plan[k] for k in ('session_id', 'participant_id', 'task', 'group', 'condition', 'provider', 'model', 'repeat')}
    record = evaluate_source_bytes(source, plan['task'], metadata=identity)
    record['evidence_class'] = 'FRESH_POST_SESSION_HIDDEN_EVALUATION'
    record['session_evidence_class'] = result.get('evidence_class', 'OFFLINE_SESSION')
    record['session_verified'] = True
    if output_path is not None:
        destination = Path(output_path)
        if (not destination.resolve().is_relative_to(ROOT)
                or destination.resolve().is_relative_to((Path(session_dir) / 'workspace').resolve())):
            raise ValueError('Evaluation output must remain project-owned and outside the model workspace')
        payload = (json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
        if destination.exists() and destination.read_bytes() != payload:
            raise ValueError('Refusing to overwrite evaluation evidence')
        destination.parent.mkdir(exist_ok=True, parents=True)
        destination.write_bytes(payload)
    return record
