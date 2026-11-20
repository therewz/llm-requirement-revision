"""Credential-free, scratch-only subprocesses. No network or host-home reads.

macOS: sandbox-exec, with explicit runtime reads and scratch writes.
Linux: bubblewrap unshare-all, read-only runtime mounts and scratch only.
No isolation bypass is supported. Caller copies trusted workers and input into
scratch before invoking. This helper never imports the program under test.
"""
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import threading
import struct
import tempfile
import stat

class IsolationUnavailable(RuntimeError):
    pass

class ResourceLimit(RuntimeError):
    pass

_READY = set()

ENV = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
       "PYTHONNOUSERSITE": "1", "PYTHONHASHSEED": "0", "TZ": "UTC",
       "LANG": "C.UTF-8", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}

BOOTSTRAP = '''import os,resource,runpy,sys
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024*1024,64*1024*1024))
resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
resource.setrlimit(resource.RLIMIT_CPU,(int(sys.argv[1]),int(sys.argv[1])+1))
if sys.platform.startswith('linux'):
    memory_bytes=int(sys.argv[2])*1024**2
    resource.setrlimit(resource.RLIMIT_AS,(memory_bytes,memory_bytes))
mode,target=sys.argv[3:5]
sys.argv=[target]+sys.argv[5:]
sys.path.insert(0,os.getcwd())
if mode=='module': runpy.run_module(target,run_name='__main__',alter_sys=True)
else: runpy.run_path(target,run_name='__main__')
'''


def runtime_paths(python):
    # These come from the trusted selected interpreter, before any participant runs.
    p = subprocess.run([str(python), "-I", "-S", "-c",
                        "import sys,json;print(json.dumps([sys.prefix,sys.base_prefix]))"],
                       env=ENV, text=True, capture_output=True, check=True)
    return sorted(set(json.loads(p.stdout) + [str(Path(python).resolve().parent.parent)]))


def mac_profile(scratch, runtimes):
    quote = lambda value: json.dumps(str(value))
    reads = ["/usr", "/System", "/Library/Developer", "/Library/Frameworks", "/Library/Apple", "/opt/homebrew/Cellar",
             "/opt/homebrew/opt", "/private/var/db/dyld"] + runtimes
    rules = ["(version 1)", "(deny default)", "(allow process-exec)",
             "(allow sysctl-read)", "(allow file-read-metadata)",
             # macOS ignition requires reading root directory itself, not descendants.
             '(allow file-read-data (literal "/"))',
             '(allow file-read* (subpath "/dev"))',
             '(allow file-write* (literal "/dev/null") (literal "/dev/dtracehelper"))']
    rules += ["(allow file-read* (subpath " + quote(p) + "))" for p in reads]
    rules += ["(allow file-read* file-write* (subpath " + quote(scratch) + "))",
              "(deny network*)", "(deny process-fork)"]
    return "\n".join(rules) + "\n"


def linux_seccomp():
    """Deny networking and fork/clone after bubblewrap establishes namespaces."""
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        arch, denied = 0xC000003E, [41, 42, 49, 53, 56, 57, 58, 435]
    elif machine in ("aarch64", "arm64"):
        arch, denied = 0xC00000B7, [198, 199, 200, 203, 220, 435]
    else:
        raise IsolationUnavailable("Unsupported Linux seccomp architecture")
    instructions = [(0x20, 0, 0, 4), (0x15, 1, 0, arch),
                    (0x06, 0, 0, 0x80000000), (0x20, 0, 0, 0),
                    (0x45, 0, 1, 0x40000000), (0x06, 0, 0, 0x80000000)]
    for syscall in denied:
        instructions += [(0x15, 0, 1, syscall), (0x06, 0, 0, 0x00050001)]
    instructions += [(0x06, 0, 0, 0x7FFF0000)]
    return b"".join(struct.pack("HBBI", *instruction) for instruction in instructions)


def command(python, scratch, mode, target, args, timeout, seccomp_fd=None, memory_mb=512):
    scratch = Path(scratch).resolve()
    if not scratch.is_dir():
        raise ValueError("scratch directory absent")
    bootstrap = scratch / "_isolation_bootstrap.py"
    bootstrap.write_text(BOOTSTRAP)
    # sys.prefix with -S on Python3.12 is base prefix; explicitly include venv tree.
    runtimes = sorted(set(runtime_paths(python) + [str(Path(python).absolute().parent.parent)]))
    child = [str(python), "-I", str(bootstrap), str(max(2, int(timeout))), str(int(memory_mb)), mode, str(target), *map(str, args)]
    if platform.system() == "Darwin":
        profile = scratch / "_sandbox.sb"
        profile.write_text(mac_profile(scratch, runtimes))
        return ["/usr/bin/sandbox-exec", "-f", str(profile), *child]
    if platform.system() == "Linux":
        bwrap = shutil.which("bwrap")
        if not bwrap:
            raise IsolationUnavailable("bubblewrap required on Linux; refusing unisolated execution")
        cmd = [bwrap, "--unshare-all", "--die-with-parent", "--new-session",
               "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
        for directory in sorted(set(["/usr", "/bin", "/lib", "/lib64"] + runtimes)):
            if Path(directory).exists():
                cmd += ["--ro-bind", directory, directory]
        if Path("/etc/ld.so.cache").exists():
            cmd += ["--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache"]
        if seccomp_fd is None:
            raise IsolationUnavailable("Linux seccomp descriptor required")
        # D1 (owner-approved 2026-11-04, see withdrawal_preparation/approvals/DECISION_D1_LINUX_READONLY_ROOT.md):
        # after binding scratch, make bwrap's private /tmp tmpfs and root read-only so writes outside scratch fail.
        cmd += ["--seccomp", str(seccomp_fd), "--bind", str(scratch), str(scratch),
                "--remount-ro", "/tmp", "--remount-ro", "/", "--chdir", str(scratch), "--", *child]
        return cmd
    raise IsolationUnavailable("Only macOS sandbox-exec or Linux bubblewrap is supported")


def read_regular(path, max_bytes=16*1024*1024):
    """Read a direct scratch output safely without following untrusted links."""
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("worker output must be a single-link regular file")
        if info.st_size > max_bytes:
            raise ValueError("worker output exceeds size limit")
        chunks, total = [], 0
        while True:
            chunk = os.read(fd, min(65536, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk); total += len(chunk)
            if total > max_bytes:
                raise ValueError("worker output exceeds size limit")
        return b"".join(chunks)
    finally:
        os.close(fd)


def run(python, scratch, mode, target, args=(), timeout=120, memory_mb=512):
    """Return CompletedProcess; kill entire process group if wall limit is exceeded."""
    seccomp = None
    if platform.system() == "Linux":
        seccomp = tempfile.TemporaryFile()
        seccomp.write(linux_seccomp()); seccomp.seek(0)
    cmd = command(python, scratch, mode, target, args, timeout,
                  seccomp.fileno() if seccomp else None, memory_mb)
    # Anonymous files have no attacker-controlled path to reopen afterward.
    stdout_file, stderr_file = tempfile.TemporaryFile(mode="w+b"), tempfile.TemporaryFile(mode="w+b")
    try:
        p = subprocess.Popen(cmd, cwd=scratch, env=ENV, stdout=stdout_file,
                             stderr=stderr_file, start_new_session=True,
                             pass_fds=(seccomp.fileno(),) if seccomp else ())
    except OSError as exc:
        stdout_file.close(); stderr_file.close()
        if seccomp: seccomp.close()
        raise IsolationUnavailable(str(exc)) from exc
    def tail(f):
        size = os.fstat(f.fileno()).st_size
        f.seek(max(0,size-20000))
        return f.read(20000).decode(errors="replace"), size
    stopped = threading.Event()
    memory_exceeded = []
    def watch_memory():
        # macOS has no reliable RLIMIT_AS for this runtime. Fork is denied by
        # the profile, so this PID is the complete untrusted process tree.
        while not stopped.wait(0.1):
            if p.poll() is not None:
                return
            status = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(p.pid)],
                                    env=ENV, text=True, capture_output=True)
            value = status.stdout.strip()
            if value.isdigit() and int(value) > memory_mb * 1024:
                memory_exceeded.append(int(value))
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                return
    watcher = None
    if platform.system() == "Darwin":
        watcher = threading.Thread(target=watch_memory, daemon=True)
        watcher.start()
    try:
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            p.wait()
            raise subprocess.TimeoutExpired(cmd, timeout, output=tail(stdout_file)[0], stderr=tail(stderr_file)[0])
        stdout, stdout_size = tail(stdout_file)
        stderr, stderr_size = tail(stderr_file)
        if memory_exceeded:
            raise ResourceLimit(f"isolated worker exceeded {memory_mb} MiB resident memory")
        result = subprocess.CompletedProcess(cmd, p.returncode, stdout, stderr)
        result.output_sizes = {"stdout": stdout_size, "stderr": stderr_size}
        return result
    finally:
        stopped.set()
        if watcher:
            watcher.join(timeout=2)
        stdout_file.close(); stderr_file.close()
        if seccomp: seccomp.close()


def require_ready(python):
    """Run confinement probes once per trusted parent process before untrusted code."""
    key = str(Path(python).resolve())
    if key in _READY:
        return
    with tempfile.TemporaryDirectory(prefix="isolation_preflight_") as base:
        base = Path(base); scratch = base/"allowed";scratch.mkdir()
        sentinel = base/"outside.txt";sentinel.write_text("non-sensitive sentinel")
        probe = scratch/"probe.py"
        # D1: a read-only-filesystem error (EROFS) also counts as a denied write (Linux read-only root).
        probe.write_text("import os,socket,errno\n" + f"sentinel={str(sentinel)!r}\n" +
            "for action in [lambda:open(sentinel).read(),lambda:open(sentinel+'x','w'),lambda:socket.socket(),lambda:os.fork()]:\n"
            " try:action()\n except (PermissionError,FileNotFoundError):pass\n except OSError as e:\n  if e.errno!=errno.EROFS:raise\n else:raise RuntimeError('confinement failed')\n"
            "open('inside.txt','w').write('ok')\nprint('ISOLATION_READY')\n")
        # macOS permits socket creation but rejects bind/connect; test an actual bind.
        probe.write_text(probe.read_text().replace("lambda:socket.socket(),", "lambda:socket.socket().bind(('127.0.0.1',0)),"))
        try:
            p = run(python,scratch,"file",probe,timeout=15)
        except Exception as exc:
            raise IsolationUnavailable("Isolation preflight failed: "+str(exc)) from exc
        if p.returncode or "ISOLATION_READY" not in p.stdout:
            raise IsolationUnavailable(f"Isolation preflight failed rc={p.returncode}: {p.stderr[-800:]}")
    _READY.add(key)
