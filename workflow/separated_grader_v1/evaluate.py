"""Run trusted tests against a proxy for an isolated candidate process.

The process importing the tests never imports candidate Python. Only one
function call and its arguments are delivered to each candidate subprocess.
"""

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TEMP_ROOT = ROOT / 'tmp/separated_grader_v1'
MAX_RESULT_BYTES = 2 * 1024 * 1024
MAX_GRADING_SECONDS = 600

spec = importlib.util.spec_from_file_location(
    'pinned_original_benchmark_inputs', ROOT / 'code/bounded_sessions_v1/evaluate.py')
frozen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frozen)
FREEZE_SHA256 = frozen.FREEZE_SHA256
runtime = frozen.runtime


class GraderUnavailable(RuntimeError):
    """A trusted worker or isolation failure, separate from a candidate result."""


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def evaluate_source_bytes(source, task, *, metadata=None):
    """Evaluate freshly via a separate, trusted grading interpreter."""
    if not isinstance(source, bytes) or len(source) > runtime.DEFAULTS['file_bytes']:
        raise ValueError('Expected a bounded final source')
    key, _, suites = frozen._inputs(task)
    started = datetime.now(timezone.utc).isoformat()
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    # This directory is outside every candidate sandbox. It is never mounted
    # into, or made an ancestor of, a candidate's permitted workspace.
    with tempfile.TemporaryDirectory(prefix='trusted_', dir=TEMP_ROOT) as temporary:
        folder = Path(temporary).resolve()
        (folder / 'candidate_bytes.py').write_bytes(source)
        (folder / 'targets.json').write_bytes(key)
        for layer, suite in suites.items():
            (folder / f'test_{layer}.py').write_bytes(suite['bytes'])
        try:
            completed = subprocess.run(
                [str(runtime.PYTHON), '-I', '-B', str(Path(__file__).resolve()), '--trusted-worker', task],
                cwd=folder, env={**runtime.ENV, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'},
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=MAX_GRADING_SECONDS, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GraderUnavailable('Trusted grading worker did not finish') from exc
        if completed.returncode != 0 or len(completed.stdout) > MAX_RESULT_BYTES:
            # Worker errors name a trusted exception class, with no test data.
            detail = completed.stderr.decode('ascii', errors='replace').strip()
            if not detail.isidentifier():
                detail = 'worker_failed'
            raise GraderUnavailable(f'Trusted grading worker failure: {detail}')
        try:
            result = json.loads(completed.stdout)
            if set(result) != {'targets', 'core28', 'supplied5'}:
                raise ValueError('Unexpected result structure')
        except (UnicodeError, ValueError, TypeError) as exc:
            raise GraderUnavailable('Trusted grading worker returned invalid evidence') from exc

    targets = result['targets']
    expected_cases = {c['case_id'] for c in json.loads(key)['cases']}
    if targets['import_error'] is None and set(targets['cases']) != expected_cases:
        raise GraderUnavailable('Trusted worker did not cover the frozen target key')
    targets.update(answer_key_sha256=sha(key), expected_case_count=len(expected_cases))
    for layer, suite in suites.items():
        result[layer].update(suite_path=suite['path'], suite_sha256=suite['sha256'],
                             expected_case_count=len(suite['ids']))
        if targets['import_error'] is None and (
            not result[layer]['complete'] or set(result[layer]['results']) != set(suite['ids'])
        ):
            raise GraderUnavailable(f'Trusted worker did not cover frozen suite {layer}')
    return {
        **(metadata or {}), **result, 'task': task, 'source_sha256': sha(source),
        'freeze_sha256': FREEZE_SHA256,
        'evaluation_complete': all(result[layer]['complete'] for layer in ('targets', 'core28', 'supplied5')),
        'grader_boundary': 'TRUSTED_PROXY_GRADER_PER_CALL_MACOS_SANDBOX_V1',
        'started_at_utc': started, 'finished_at_utc': datetime.now(timezone.utc).isoformat(),
        'effective_timezone': runtime.ENV['TZ'], 'no_feedback_to_agent': True,
    }


def _trusted_worker(task):
    """Execute only trusted Python here. The proxy never imports final.py."""
    import contextlib
    import os
    from types import ModuleType
    import pytest
    # The invocation runs in isolated interpreter mode. Add exactly our code
    # root to load the trusted bridge, never the directory holding the source.
    sys.path.insert(0, str(ROOT / 'code'))
    from separated_grader_v1.candidate import (
        Candidate, CandidateImportError, CandidateProcessError, CandidateRaised,
    )

    function = {'A': 'suggest_slots', 'B': 'is_allocation_feasible'}[task]
    folder = Path.cwd()
    scratch = TEMP_ROOT / 'candidates'
    scratch.mkdir(exist_ok=True, parents=True)
    candidate = Candidate((folder / 'candidate_bytes.py').read_bytes(), scratch_root=scratch)
    cases = json.loads((folder / 'targets.json').read_bytes())['cases']
    targets = {'import_error': None, 'cases': {}, 'execution_metadata': {'status': 'ok', 'returncode': 0},
               'complete': True}
    try:
        candidate.check_import()
    except (CandidateImportError, CandidateProcessError) as exc:
        targets.update(import_error={'type': getattr(exc, 'remote_type', type(exc).__name__),
                                     'message': getattr(exc, 'remote_message', str(exc))[:500]},
                       complete=False)
        unrun = {'results': {}, 'metadata': {'status': 'not_run', 'returncode': None,
                                             'timed_out_file': False, 'collection_error': 'candidate_import_failed'},
                 'complete': False}
        return {'targets': targets, 'core28': unrun, 'supplied5': unrun}

    for case in cases:
        if case['function'] != function:
            raise GraderUnavailable('Trusted key calls an unexpected entry point')
        targets['cases'][case['case_id']] = candidate.raw_observation(
            function, *case['args'], **case.get('kwargs', {}))

    class Recorder:
        def __init__(self):
            self.results = {}
            self.collected = []
            self.collection_error = None
            self.protocol_failure = None
            self.trusted_error = None

        def pytest_collection_finish(self, session):
            self.collected = [item.nodeid.split('::')[-1] for item in session.items]

        def pytest_collectreport(self, report):
            if report.failed:
                self.collection_error = str(report.longrepr)[:1000]

        def pytest_runtest_setup(self, item):
            self.protocol_failure = None

        def pytest_runtest_logreport(self, report):
            name = report.nodeid.split('::')[-1]
            if report.when == 'call' and self.protocol_failure:
                # A broad exception assertion must not award a pass for a
                # killed or malformed candidate process.
                self.results[name] = ['failed', self.protocol_failure]
            elif report.failed:
                self.results[name] = ['failed' if report.when == 'call' else 'error', str(report.longrepr)[:300]]
            elif report.skipped:
                self.results.setdefault(name, ['skipped', str(report.longrepr)[:300]])
            elif report.when == 'call':
                self.results.setdefault(name, ['passed', ''])

    result = {'targets': targets}
    for layer in ('core28', 'supplied5'):
        recorder = Recorder()

        def proxy(*args, **kwargs):
            try:
                return candidate.call(function, *args, **kwargs)
            except (CandidateProcessError, CandidateImportError) as exc:
                recorder.protocol_failure = type(exc).__name__
                raise
            except (CandidateRaised, ValueError, TypeError):
                raise
            except Exception as exc:
                recorder.trusted_error = exc
                raise

        module = ModuleType('solution')
        setattr(module, function, proxy)
        sys.modules['solution'] = module
        with open(os.devnull, 'w') as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            exitcode = int(pytest.main([
                '-q', '-s', '-p', 'no:cacheprovider', '--rootdir', str(folder),
                '--confcutdir', str(folder), '--noconftest', '--import-mode=importlib',
                str(folder / f'test_{layer}.py'),
            ], plugins=[recorder]))
        if recorder.trusted_error is not None:
            raise GraderUnavailable('Trusted proxy encountered a host error') from recorder.trusted_error
        complete = (exitcode in (0, 1) and recorder.collection_error is None
                    and len(recorder.collected) == len(set(recorder.collected))
                    and set(recorder.collected) == set(recorder.results)
                    and not any(value[0] == 'skipped' for value in recorder.results.values()))
        result[layer] = {
            'results': recorder.results, 'complete': complete,
            'metadata': {'status': 'ok', 'returncode': 0, 'pytest_exitcode': exitcode,
                         'collected_case_ids': recorder.collected, 'collection_error': recorder.collection_error,
                         'timed_out_file': False, 'complete': complete},
        }
    return result


if __name__ == '__main__' and len(sys.argv) == 3 and sys.argv[1] == '--trusted-worker':
    try:
        sys.stdout.buffer.write(encode(_trusted_worker(sys.argv[2])))
    except Exception as error:
        sys.stderr.write(type(error).__name__ + '\n')
        raise SystemExit(2) from None
