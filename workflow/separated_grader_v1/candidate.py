"""Trusted proxy for fresh calls in a read-only, network-disabled Mac sandbox."""

import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import time

from . import worker


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('separated_candidate_runtime', ROOT / 'code/bounded_sessions_v1/runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
_original_rss_reader = runtime._rss_reader


def _rss_reader_with_exit_grace():
    read = _original_rss_reader()

    def sample(pid):
        try:
            return read(pid)
        except runtime.IsolationUnavailable:
            # Darwin can revoke task info while a fast-exiting child is still
            # between process teardown and a reapable exit. Give the monitor's
            # existing Popen.poll() guard time to see that exit. A still-running
            # unmonitored process remains an isolation failure.
            time.sleep(0.025)
            return read(pid)

    return sample


# This runtime is a private loaded module, separate from the frozen runner's
# runtime instance. The preserved monitor still owns the fail-closed decision.
runtime._rss_reader = _rss_reader_with_exit_grace
WORKER_BYTES = Path(worker.__file__).read_bytes()
CALL_WALL_SECONDS = 3
IMPORT_WALL_SECONDS = 6
REQUEST_CAP = 16384
_PREFLIGHT = threading.Lock()


class CandidateProcessError(RuntimeError):
    """The candidate child failed to provide a valid result for this operation."""


class CandidateTimeout(CandidateProcessError):
    pass


class CandidateRaised(Exception):
    def __init__(self, remote_type, remote_message):
        self.remote_type = remote_type
        self.remote_message = remote_message
        super().__init__(f'{remote_type}: {remote_message}')


class CandidateImportError(CandidateRaised):
    pass


_EXCEPTION_MATCHES = {'ValueError': ValueError, 'TypeError': TypeError}


def parse_reply(stdout, *, import_only=False):
    """Accept one complete result for one operation, with no grade or test fields."""
    try:
        response = worker.parse_json(stdout)
        if not isinstance(response, dict) or type(response.get('version')) is not int or response['version'] != worker.VERSION:
            raise ValueError('Unexpected reply version')
        kind = response['kind']
        prefix = {'version', 'kind'}
        if kind == 'return' and set(response) == prefix | {'value'}:
            value = worker.decode_value(response['value'])
            if import_only and value is not None:
                raise ValueError('Unexpected import result')
            return {'kind': kind, 'value': value}
        if kind == 'timeout' and set(response) == prefix | {'stage'}:
            if response['stage'] not in ('import', 'call') or import_only and response['stage'] != 'import':
                raise ValueError('Unexpected timeout stage')
            raise CandidateTimeout(f"Candidate {response['stage']} timed out")
        if kind == 'unsupported_return' and set(response) == prefix and not import_only:
            raise CandidateProcessError('Candidate returned an unsupported value')
        if kind == 'exception' and set(response) == prefix | {'stage', 'exception_type', 'message', 'match_as'}:
            if response['stage'] not in ('import', 'call') or import_only and response['stage'] != 'import':
                raise ValueError('Unexpected exception stage')
            name, message, match = (response[k] for k in ('exception_type', 'message', 'match_as'))
            if (type(name) is not str or not 0 < len(name) <= 128 or type(message) is not str
                    or len(message) > worker.MAX_MESSAGE or match not in (None, 'ValueError', 'TypeError')):
                raise ValueError('Invalid exception payload')
            name.encode('utf-8')
            message.encode('utf-8')
            return response
        raise ValueError('Unexpected reply kind or fields')
    except (ValueError, KeyError, TypeError, RecursionError, OverflowError) as error:
        raise CandidateProcessError('Candidate did not return valid single-call evidence') from error


def _canonical(value, depth=0):
    if type(value) is bool:
        return {'type': 'bool', 'value': value}
    if type(value) is list and all(type(x) is str for x in value):
        return {'type': 'list_str', 'value': value}
    if type(value) is tuple and depth < 2:
        return {'type': 'tuple', 'items': [_canonical(x, depth + 1) for x in value[:8]],
                'length': len(value), 'repr': repr(value)[:500]}
    return {'type': type(value).__name__, 'repr': repr(value)[:500]}


class Candidate:
    """Give the sandbox only source, a call bridge, and one operation's inputs.

    Every operation imports a fresh candidate module. The supplied tests make one
    candidate call per case and do not observe mutation of arguments or module
    state. Both are therefore isolated per call at this boundary.
    """

    def __init__(self, source: bytes, *, scratch_root: Path):
        if type(source) is not bytes or len(source) > runtime.DEFAULTS['file_bytes']:
            raise ValueError('Expected bounded candidate source bytes')
        self.source = source
        self.scratch_root = Path(scratch_root)
        self.scratch_root.mkdir(parents=True, exist_ok=True)
        with _PREFLIGHT:
            runtime.isolation_preflight(self.scratch_root)

    def _exchange(self, request, *, import_only=False):
        data = json.dumps({'version': worker.VERSION, **request}, ensure_ascii=True, allow_nan=False,
                          separators=(',', ':')).encode('ascii')
        if len(data) > REQUEST_CAP:
            raise ValueError('Trusted call input exceeds the request limit')
        with tempfile.TemporaryDirectory(prefix='candidate_', dir=self.scratch_root) as tmp:
            workspace = Path(tmp).resolve()
            target = workspace / 'call_bridge.py'
            target.write_bytes(WORKER_BYTES)
            (workspace / 'solution.py').write_bytes(self.source)
            (workspace / 'request.json').write_bytes(data)
            result = runtime._run_isolated(workspace, target, {
                **runtime.DEFAULTS,
                'python_timeout_seconds': IMPORT_WALL_SECONDS if import_only else CALL_WALL_SECONDS,
            })
        if result['status'] == 'timeout':
            raise CandidateTimeout('Candidate exceeded its sandbox wall time')
        if result['status'] != 'ok' or result['returncode'] != 0 or result['output_truncated']:
            raise CandidateProcessError(f"Candidate child ended with {result['status']}")
        return parse_reply(result['stdout'], import_only=import_only)

    def check_import(self):
        result = self._exchange({'operation': 'import'}, import_only=True)
        if result['kind'] == 'exception':
            raise CandidateImportError(result['exception_type'], result['message'])

    def _call_result(self, function, args, kwargs):
        if function not in worker.FUNCTIONS:
            raise ValueError('Unrecognized candidate entry point')
        return self._exchange({'operation': 'call', 'function': function, 'args': worker.encode_value(args),
                               'kwargs': worker.encode_value(kwargs)})

    def call(self, function, *args, **kwargs):
        result = self._call_result(function, args, kwargs)
        if result['kind'] == 'return':
            return result['value']
        if result['stage'] == 'import':
            raise CandidateImportError(result['exception_type'], result['message'])
        error_type = _EXCEPTION_MATCHES.get(result['match_as'])
        if error_type is not None:
            raise error_type(result['message'])
        raise CandidateRaised(result['exception_type'], result['message'])

    def raw_observation(self, function, *args, **kwargs):
        """Match the frozen target worker's normalized records for ordinary calls."""
        try:
            result = self._call_result(function, args, kwargs)
        except CandidateTimeout:
            return {'kind': 'timeout'}
        except CandidateProcessError as error:
            return {'kind': 'exc', 'exc': type(error).__name__, 'msg': str(error)[:300]}
        if result['kind'] == 'exception':
            return {'kind': 'exc', 'exc': result['exception_type'], 'msg': result['message'][:300]}
        return {'kind': 'ret', **_canonical(result['value'])}
