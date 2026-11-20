"""Bounded isolated pytest execution on copied source and tests.

Uses isolated_exec_v3 (macOS sandbox-exec or Linux bubblewrap + seccomp),
credential-free environment, scratch-only writes and resource/wall limits.
An incomplete whole-suite result stays incomplete; no per-case retry amplification.
Originals are never modified; module aliases are byte-identical copies.
"""
import os, shutil, subprocess, sys, tempfile, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT

# All pytest processes use the v3 scratch-only/no-network backend.
sys.path.insert(0, os.path.join(ROOT, "withdrawal_preparation", "scripts"))
import isolated_exec_v3 as isolation
PY = os.path.join(ROOT, ".venv", "bin", "python")
SCRATCH = os.environ.get("RUN_SCRATCH", tempfile.gettempdir())
ENV = isolation.ENV
FILE_TIMEOUT = 120
TEST_TIMEOUT = 20


def _pytest(cwd, target, xml, timeout):
    cwd = os.path.realpath(cwd)
    target = target if os.path.isabs(target) else os.path.join(cwd, target)
    args = ["-q", "-p", "no:cacheprovider", "-o", "junit_family=xunit2",
            f"--junitxml={xml}", "--rootdir", cwd, "--confcutdir", cwd, "--noconftest", target]
    try:
        p = isolation.run(PY, cwd, "module", "pytest", args, timeout)
        return p.returncode, p.stdout[-20000:], p.stderr[-5000:], False
    except isolation.ResourceLimit as e:
        return -9, "", str(e), False
    except subprocess.TimeoutExpired as e:
        return None, (e.stdout or b"").decode(errors="replace")[-5000:] if isinstance(e.stdout, bytes) else (e.stdout or ""), "", True


def _parse(xml):
    out = {}
    if not os.path.exists(xml):
        return out, None
    root = ET.fromstring(isolation.read_regular(xml))
    coll_err = None
    for tc in root.iter("testcase"):
        name = tc.get("name")
        cls = tc.get("classname", "")
        status, msg = "passed", ""
        for child in tc:
            if child.tag in ("failure", "error", "skipped"):
                status = {"failure": "failed", "error": "error", "skipped": "skipped"}[child.tag]
                msg = (child.get("message") or "").strip().splitlines()[0][:300] if child.get("message") else (child.text or "").strip().splitlines()[-1][:300] if child.text else ""
                if child.tag == "error" and not name:
                    coll_err = msg
        if name:
            out[name] = (status, msg)
        else:
            coll_err = msg or "collection error"
    return out, coll_err


def run(code_rel, test_rel, tag):
    isolation.require_ready(PY)
    d = os.path.realpath(tempfile.mkdtemp(prefix=f"run_{tag}_", dir=SCRATCH))
    shutil.copy(os.path.join(ROOT, code_rel), os.path.join(d, "solution.py"))
    # Logged import adaptation (identical bytes, no code change): some participant test files
    # import `src.solution` or `solution2`; provide those module names as copies of the same file.
    os.makedirs(os.path.join(d, "src"))
    shutil.copy(os.path.join(ROOT, code_rel), os.path.join(d, "src", "solution.py"))
    shutil.copy(os.path.join(ROOT, code_rel), os.path.join(d, "solution2.py"))
    tname = "test_target.py"
    shutil.copy(os.path.join(ROOT, test_rel), os.path.join(d, tname))
    xml = os.path.join(d, "report.xml")
    rc, so, se, to = _pytest(d, tname, xml, FILE_TIMEOUT)
    try:
        res, coll = _parse(xml)
    except (ET.ParseError, OSError, ValueError) as exc:
        res, coll = {}, "invalid evaluator output: " + str(exc)[:200]
    meta = {"returncode": rc, "timed_out_file": to, "collection_error": coll, "stdout_tail": so[-3000:], "stderr_tail": se[-2000:]}
    # A bounded full-suite failure remains incomplete, not a zero-pass baseline.
    # Do not amplify a resource failure by automatically executing every test again.
    shutil.rmtree(d, ignore_errors=True)
    return res, meta
