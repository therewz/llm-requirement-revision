"""Small, credential-free tools. Untrusted Python runs only in verified isolation.

The host can edit bounded Python files. Executed checks cannot write the workspace,
spawn children, access the network, or read the project/evaluator/home directories.
Only the tested macOS runtime is currently implemented; other hosts fail closed.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import selectors
import signal
import stat
import subprocess
import tempfile
import time

PYTHON = Path('/Users/rezatehrani/.pyenv/versions/3.12.6/bin/python3.12')
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'TZ': 'UTC',
       'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}
DEFAULTS = {'file_bytes': 131072, 'workspace_bytes': 1048576, 'workspace_files': 32,
            'output_bytes': 16384, 'python_timeout_seconds': 10, 'memory_mb': 256}
TOOL_SCHEMAS = [
    {'name': 'read_file', 'description': 'Read a Python file in this workspace.',
     'parameters': {'type': 'object', 'properties': {'path': {'type': 'string'}},
                    'required': ['path'], 'additionalProperties': False}},
    {'name': 'write_file', 'description': 'Replace src/solution.py or create/replace a Python check under checks/.',
     'parameters': {'type': 'object', 'properties': {'path': {'type': 'string'}, 'content': {'type': 'string'}},
                    'required': ['path', 'content'], 'additionalProperties': False}},
    {'name': 'run_python', 'description': 'Run a Python file in this workspace with bounded output/time, no network or subprocesses, and read-only files.',
     'parameters': {'type': 'object', 'properties': {'path': {'type': 'string'}},
                    'required': ['path'], 'additionalProperties': False}}
]


class IsolationUnavailable(RuntimeError):
    pass


class WorkspaceError(ValueError):
    pass


def _safe_relative(value):
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value:
        raise WorkspaceError('Invalid workspace path')
    path = PurePosixPath(value)
    if len(value.encode('utf-8')) > 240 or len(path.parts) > 8:
        raise WorkspaceError('Workspace path is too long or deeply nested')
    if path.is_absolute() or any(x in ('', '.', '..') for x in value.split('/')):
        raise WorkspaceError('Use a relative workspace path without traversal')
    if path.as_posix() != 'src/solution.py' and not (
        len(path.parts) >= 2 and path.parts[0] == 'checks' and path.suffix == '.py'
    ):
        raise WorkspaceError('Only src/solution.py and checks/**/*.py are accessible')
    return path


def _read_regular(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise WorkspaceError('Expected a single-link regular file')
        if info.st_size > limit:
            raise WorkspaceError('File exceeds byte limit')
        data = bytearray()
        while True:
            chunk = os.read(fd, min(65536, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > limit:
                raise WorkspaceError('File exceeds byte limit')
        return bytes(data)
    finally:
        os.close(fd)


def _mac_profile(workspace, bootstrap):
    # These are explicit runtime trees, never the user's home or project root.
    runtime = PYTHON.resolve().parent.parent
    reads = [runtime, Path('/System'), Path('/usr/lib'), Path('/private/var/db/dyld')]
    for library in ('gettext', 'openssl@3', 'libffi', 'xz', 'bzip2', 'readline', 'sqlite'):
        lib = Path('/opt/homebrew/opt') / library / 'lib'
        if lib.exists():
            reads.extend([lib, lib.resolve()])
    quote = lambda p: json.dumps(str(p))
    lines = ['(version 1)', '(deny default)', '(allow sysctl-read)',
             '(allow file-read-metadata)', '(allow file-read-data (literal "/"))',
             '(allow file-read* (literal "/dev/null") (literal "/dev/urandom") (literal "/dev/random"))',
             '(allow file-write* (literal "/dev/null") (literal "/dev/dtracehelper"))',
             '(allow process-exec (literal ' + quote(PYTHON.resolve()) + '))',
             '(deny process-fork)', '(deny network*)',
             '(allow file-read* (literal ' + quote(bootstrap) + '))',
             '(allow file-read* (subpath ' + quote(workspace) + '))']
    lines += ['(allow file-read* (subpath ' + quote(p) + '))' for p in reads]
    return '\n'.join(lines) + '\n'


BOOTSTRAP = '''import os,resource,runpy,sys
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))
resource.setrlimit(resource.RLIMIT_CPU,(int(sys.argv[1]),int(sys.argv[1])+1))
workspace,target=sys.argv[2:4]
ready_fd=int(sys.argv[4])
os.write(ready_fd,b'BOOTSTRAP_READY')
os.close(ready_fd)
sys.path[:0]=[workspace,os.path.join(workspace,'src')]
sys.argv=[target]
runpy.run_path(target,run_name='__main__')
'''


def _rss_reader():
    try:
        library = ctypes.CDLL('/usr/lib/libproc.dylib')
        proc_pidinfo = library.proc_pidinfo
        proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
        proc_pidinfo.restype = ctypes.c_int
    except (OSError, AttributeError) as exc:
        raise IsolationUnavailable('RSS monitor unavailable') from exc

    def read(pid):
        data = ctypes.create_string_buffer(96)  # Darwin proc_taskinfo
        if proc_pidinfo(pid, 4, 0, data, 96) != 96:
            raise IsolationUnavailable('RSS monitor could not inspect child')
        return int.from_bytes(data.raw[8:16], 'little')
    return read


def _kill(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        raise IsolationUnavailable('Host denied control of isolated process') from exc


def _run_isolated(workspace, target, limits):
    if platform.system() != 'Darwin' or not Path('/usr/bin/sandbox-exec').is_file() or not PYTHON.is_file():
        raise IsolationUnavailable('Validated macOS sandbox-exec runtime required; no unisolated fallback')
    rss = _rss_reader()
    # Launch files are outside the editable/model-readable workspace.
    with tempfile.TemporaryDirectory(prefix='bounded_launch_', dir=workspace.parent) as launch:
        launch = Path(launch).resolve()
        bootstrap, profile = launch / 'bootstrap.py', launch / 'sandbox.sb'
        bootstrap.write_text(BOOTSTRAP)
        profile.write_text(_mac_profile(workspace, bootstrap))
        ready_read, ready_write = os.pipe()
        command = ['/usr/bin/sandbox-exec', '-f', str(profile), str(PYTHON), '-I', '-S', '-B',
                   str(bootstrap), str(max(1, math.ceil(limits['python_timeout_seconds']))),
                   str(workspace), str(target), str(ready_write)]
        started = time.monotonic()
        try:
            process = subprocess.Popen(command, cwd=workspace, env=ENV, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                                       pass_fds=(ready_write,))
        except OSError as exc:
            os.close(ready_read); os.close(ready_write)
            raise IsolationUnavailable('Isolated process could not launch') from exc
        os.close(ready_write)
        ready_pipe = os.fdopen(ready_read, 'rb', buffering=0)
        attestation = bytearray()
        output = {'stdout': bytearray(), 'stderr': bytearray()}
        total, peak_rss, status = 0, 0, 'ok'
        monitor_error = None
        with selectors.DefaultSelector() as selector:
            for name, pipe in (('stdout', process.stdout), ('stderr', process.stderr)):
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, name)
            os.set_blocking(ready_pipe.fileno(), False)
            selector.register(ready_pipe, selectors.EVENT_READ, 'attestation')
            while selector.get_map() or process.poll() is None:
                if process.poll() is None:
                    if time.monotonic() - started > limits['python_timeout_seconds']:
                        status = 'timeout'; _kill(process)
                    try:
                        if status != 'ok':
                            process.wait(timeout=2)
                            continue
                        memory = rss(process.pid)
                        peak_rss = max(memory, peak_rss)
                        if memory > limits['memory_mb'] * 1024**2:
                            status = 'memory_limit'; _kill(process)
                    except IsolationUnavailable as exc:
                        # A racing normal exit is harmless; inability to inspect a live process is not.
                        if process.poll() is None:
                            monitor_error = exc; _kill(process)
                for key, _ in selector.select(timeout=0.02):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if key.data == 'attestation':
                        attestation.extend(chunk[:32])
                        continue
                    remaining = max(0, limits['output_bytes'] - total)
                    output[key.data].extend(chunk[:remaining])
                    total += len(chunk)
                    if total > limits['output_bytes']:
                        status = 'output_limit'; _kill(process)
                if process.poll() is not None and not selector.get_map():
                    break
        process.wait()
        process.stdout.close(); process.stderr.close()
        ready_pipe.close()
        if monitor_error:
            raise monitor_error
        stdout, stderr = (output[k].decode('utf-8', errors='replace').encode('utf-8')[:len(output[k])]
                          .decode('utf-8', errors='ignore') for k in ('stdout', 'stderr'))
        if attestation != b'BOOTSTRAP_READY':
            raise IsolationUnavailable('Isolated bootstrap did not attest successful launch')
        if status == 'ok' and process.returncode:
            status = 'tool_error'
        return {'status': status, 'returncode': process.returncode, 'stdout': stdout, 'stderr': stderr,
                'observed_output_bytes': total, 'output_truncated': total > limits['output_bytes'],
                'peak_observed_rss_bytes': peak_rss, 'elapsed_seconds': round(time.monotonic() - started, 6),
                'isolation': 'macOS sandbox-exec; no network/fork; read-only workspace; monitored RSS'}


_READY = False


def isolation_preflight(base):
    """Use synthetic, non-sensitive sentinels before running any model-produced code."""
    global _READY
    if _READY:
        return {'status': 'ok', 'cached': True}
    with tempfile.TemporaryDirectory(prefix='bounded_preflight_', dir=base) as temporary:
        root = Path(temporary).resolve()
        workspace = root / 'workspace'; workspace.mkdir()
        outside = root / 'outside.txt'; outside.write_text('synthetic isolation sentinel')
        probe = workspace / 'probe.py'
        probe.write_text('import os,socket\n' +
            f'outside={str(outside)!r}\ninside={str(workspace / "write_forbidden")!r}\n' +
            'actions=[lambda:open(outside).read(),lambda:open(outside,"w"),lambda:open(inside,"w"),'
            'lambda:socket.socket().bind(("127.0.0.1",0)),lambda:os.fork(),'
            'lambda:os.execv("/bin/sh",["/bin/sh","-c","exit 91"])]\n'
            'for action in actions:\n'
            ' try: action()\n'
            ' except PermissionError: pass\n'
            ' else: raise RuntimeError("isolation probe unexpectedly permitted")\n'
            'assert "OPENAI_API_KEY" not in os.environ\n'
            'print("ISOLATION_READY")\n')
        result = _run_isolated(workspace, probe, DEFAULTS)
        if result['status'] != 'ok' or result['stdout'].strip() != 'ISOLATION_READY':
            raise IsolationUnavailable('Isolation probes failed: ' + json.dumps(result)[:1000])
    _READY = True
    return {'status': 'ok', 'cached': False, 'probes': 6}


class WorkspaceTools:
    def __init__(self, workspace, limits=None):
        original = Path(workspace).absolute()
        if original.is_symlink() or not original.is_dir():
            raise WorkspaceError('Workspace must be a real directory')
        self.workspace = original.resolve()
        self.limits = {**DEFAULTS, **{k: v for k, v in (limits or {}).items() if k in DEFAULTS}}
        for key, value in self.limits.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise WorkspaceError('Invalid positive limit: ' + key)
        for key in ('file_bytes', 'workspace_bytes', 'workspace_files', 'output_bytes', 'memory_mb'):
            if int(self.limits[key]) != self.limits[key]:
                raise WorkspaceError('Integer limit required: ' + key)
            self.limits[key] = int(self.limits[key])
        self._inventory()

    def _path(self, name):
        relative = _safe_relative(name)
        current = self.workspace
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise WorkspaceError('Symlinks are not permitted')
            if current.exists() and not (current.is_file() or current.is_dir()):
                raise WorkspaceError('Special files are not permitted')
        if not current.resolve().is_relative_to(self.workspace):
            raise WorkspaceError('Path escaped workspace')
        return current

    def _inventory(self):
        files, size, directory_count = {}, 0, 0
        for directory, dirs, names in os.walk(self.workspace, followlinks=False):
            for name in dirs:
                directory_count += 1
                if directory_count > 128:
                    raise WorkspaceError('Workspace exceeds directory limit')
                path = Path(directory) / name
                if path.is_symlink():
                    raise WorkspaceError('Symlink directory in workspace')
                rel = path.relative_to(self.workspace)
                if len(rel.parts) > 8:
                    raise WorkspaceError('Workspace directory is too deeply nested')
                if rel.as_posix() != 'src' and rel.parts[0] != 'checks':
                    raise WorkspaceError('Unexpected workspace directory')
            for name in names:
                path = Path(directory) / name
                rel = path.relative_to(self.workspace).as_posix()
                _safe_relative(rel)
                data = _read_regular(self._path(rel), self.limits['file_bytes'])
                files[rel] = len(data); size += len(data)
                if len(files) > self.limits['workspace_files'] or size > self.limits['workspace_bytes']:
                    raise WorkspaceError('Workspace exceeds size/file limit')
        if 'src/solution.py' not in files:
            raise WorkspaceError('Missing src/solution.py')
        return files

    def execute(self, name, arguments):
        try:
            expected = {'path', 'content'} if name == 'write_file' else {'path'}
            if name not in ('read_file', 'write_file', 'run_python') or not isinstance(arguments, dict) or set(arguments) != expected:
                raise WorkspaceError('Unknown tool or invalid arguments')
            inventory = self._inventory()
            path = self._path(arguments['path'])
            if name == 'read_file':
                data = _read_regular(path, min(self.limits['file_bytes'], self.limits['output_bytes']))
                return {'status': 'ok', 'content': data.decode('utf-8'), 'sha256': hashlib.sha256(data).hexdigest()}
            if name == 'write_file':
                if not isinstance(arguments['content'], str):
                    raise WorkspaceError('File content must be text')
                data = arguments['content'].encode('utf-8')
                if len(data) > self.limits['file_bytes']:
                    raise WorkspaceError('File exceeds byte limit')
                prior = inventory.get(arguments['path'], 0)
                if sum(inventory.values()) - prior + len(data) > self.limits['workspace_bytes']:
                    raise WorkspaceError('Workspace exceeds byte limit')
                if arguments['path'] not in inventory and len(inventory) >= self.limits['workspace_files']:
                    raise WorkspaceError('Workspace exceeds file limit')
                path.parent.mkdir(parents=True, exist_ok=True)
                # No untrusted child can run concurrently or modify this tree.
                fd, temporary = tempfile.mkstemp(prefix='.write_', dir=path.parent)
                try:
                    with os.fdopen(fd, 'wb') as stream:
                        stream.write(data); stream.flush(); os.fsync(stream.fileno())
                    os.replace(temporary, path)
                finally:
                    if os.path.exists(temporary): os.unlink(temporary)
                self._inventory()
                return {'status': 'ok', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            _read_regular(path, self.limits['file_bytes'])
            isolation_preflight(self.workspace.parent)
            result = _run_isolated(self.workspace, path, self.limits)
            self._inventory()
            return result
        except IsolationUnavailable as exc:
            return {'status': 'isolation_unavailable', 'message': str(exc)[:1200]}
        except (WorkspaceError, OSError, UnicodeError) as exc:
            return {'status': 'tool_error', 'message': str(exc)[:1000]}
