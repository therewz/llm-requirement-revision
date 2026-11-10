"""Offline-verifiable scope and process leases for the cleaned continuation."""

from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
from threading import Lock
from typing import BinaryIO

from cleaned_opening_v1 import authorization as opening
from cleaned_opening_v1.launch_pin import LAUNCH_SHA256 as OPENING_LAUNCH_SHA256

ROOT = opening.ROOT
RUN_ROOT = ROOT / 'runs/cleaned_continuation_v1'
CONFIG_PATH = RUN_ROOT / 'launch_config.json'
RUN_ID = 'elmira-cleaned-continuation-20261105-v1'
STATUS = 'PREPARED_REQUIRES_EXACT_CONTINUATION_APPROVAL'
OPENING = opening.OPENING_SESSIONS
FULL_SESSIONS = 432
PROVIDERS = opening.PROVIDERS
OPENING_CONFIG_PATH = ROOT / 'runs/cleaned_opening_v1/launch_config.json'
OPENING_RUN = OPENING_CONFIG_PATH.parent / opening.RUN_ID
OPENING_CHECKPOINT_SHA256 = '248a17d7b1882d1633a004298d8ce3e4f5006fac91f7208416eecbca0f71911f'
SCHEDULER = {
    'concurrency': 4,
    'per_provider_concurrency': 2,
    'run_cost_cap_usd': '36.00',
    'provider_cost_caps_usd': {'openai': '18.00', 'anthropic': '18.00'},
}
AuthorizationError = opening.AuthorizationError
_OPENING_KEYS = ('opening_count', 'opening_checkpoint_sha256', 'opening_launch_sha256',
                 'opening_ledger_sha256')
_PINNED_INPUTS = ('cleaned_preparation_sha256', 'cleaned_baseline_manifest_sha256', 'grader_parity_sha256')


class ContinuationLaunch(opening.ValidatedLaunch):
    """The complete accounting order, with permission to dispatch only its suffix."""

    @property
    def run_id(self):
        return RUN_ID

    @property
    def run_directory(self):
        return self.output_root / RUN_ID

    @property
    def claim_directory(self):
        return self.approval_path.parent / (self.run_id + '.claims')

    @property
    def controller_lock_path(self):
        return self.approval_path.parent / (self.run_id + '.controller.lock')

    def session_plan(self, session_id):
        for plan in self.config['sessions'][OPENING:]:
            if plan['session_id'] == session_id:
                return plan
        raise AuthorizationError('The session is outside the approved continuation')

    def approval_scope(self):
        config = self.config
        sessions = [
            {key: plan[key] for key in ('session_id', 'provider', 'model', 'order')}
            | {'session_cost_cap_usd': plan['limits']['session_cost_cap_usd']}
            for plan in config['sessions'][OPENING:]
        ]
        return {'run_id': self.run_id, 'config_sha256': self.sha256,
                'run_directory': str(self.run_directory), 'host': config['host'],
                'scheduler': config['scheduler'], 'sessions': sessions,
                **{key: config[key] for key in _OPENING_KEYS}}


def _pinned_bytes(path, sha256, label):
    data = opening.read_regular(path)
    if opening.digest(data) != sha256:
        raise AuthorizationError(f'The pinned {label} changed')
    return data


def validate_launch(config_path, expected_sha256, *, host, output_root):
    """Verify the exact approved schedule, original opening, host and budget."""
    if not isinstance(expected_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise AuthorizationError('Expected the pinned SHA-256 of the continuation configuration')
    config_path, output_root = opening.canonical_path(config_path), opening.canonical_path(output_root)
    if config_path != output_root / 'launch_config.json' or not output_root.is_dir():
        raise AuthorizationError('Unexpected continuation configuration location')
    raw = _pinned_bytes(config_path, expected_sha256, 'continuation config')
    config = opening.json_object(raw)
    expected_keys = {'schema_version', 'run_id', 'run_directory', 'status', 'host', 'sessions',
                     'scheduler', 'bindings', *_OPENING_KEYS, *_PINNED_INPUTS}
    if (set(config) != expected_keys or type(config['schema_version']) is not int
            or config['schema_version'] != 1 or config['run_id'] != RUN_ID
            or config['run_directory'] != str(output_root / RUN_ID) or config['status'] != STATUS
            or not isinstance(config['bindings'], list)):
        raise AuthorizationError('The continuation configuration has an unexpected scope')
    opening.canonical_path(output_root / RUN_ID)

    original = opening.json_object(_pinned_bytes(
        OPENING_CONFIG_PATH, OPENING_LAUNCH_SHA256, 'opening config'))
    checkpoint = opening.json_object(_pinned_bytes(
        OPENING_RUN / 'checkpoints/012.json', OPENING_CHECKPOINT_SHA256, 'opening checkpoint'))
    ledger_sha256 = checkpoint['verified_ledger_prefix_sha256']
    _pinned_bytes(OPENING_RUN / 'ledger.json', ledger_sha256, 'opening ledger')
    if (type(config['opening_count']) is not int or config['opening_count'] != OPENING
            or config['opening_checkpoint_sha256'] != OPENING_CHECKPOINT_SHA256
            or config['opening_launch_sha256'] != OPENING_LAUNCH_SHA256
            or config['opening_ledger_sha256'] != ledger_sha256
            or any(config[key] != original[key] for key in _PINNED_INPUTS)):
        raise AuthorizationError('The continuation does not bind the accepted opening and cleaned inputs')
    if (not isinstance(host, dict) or host.get('system') != 'Darwin'
            or host.get('machine_binding_sha256') != opening.local_host_binding()
            or opening.encode(config['host']) != opening.encode(host)
            or opening.encode(original['host']) != opening.encode(host)):
        raise AuthorizationError('The continuation does not match the reviewed Mac and interpreter')

    prepared = opening.json_object(_pinned_bytes(
        opening.PREPARATION, opening.PREPARATION_SHA256, 'cleaned preparation'))
    sessions = config['sessions']
    if (not isinstance(sessions, list) or len(sessions) != FULL_SESSIONS
            or opening.encode(sessions) != opening.encode(prepared['sessions'])
            or opening.encode(sessions[:OPENING]) != opening.encode(original['sessions'])
            or len({p['session_id'] for p in sessions}) != FULL_SESSIONS
            or [p['order'] for p in sessions] != list(range(FULL_SESSIONS))):
        raise AuthorizationError('The continuation must preserve the exact frozen 432-session order')
    suffix = sessions[OPENING:]
    if (Counter(p['provider'] for p in suffix) != {'openai': 210, 'anthropic': 210}
            or any(p['model'] != PROVIDERS[p['provider']]
                   or opening.amount(p['limits']['session_cost_cap_usd']) != 1 for p in suffix)
            or opening.encode(config['scheduler']) != opening.encode(SCHEDULER)):
        raise AuthorizationError('The continuation changes a provider, model or cumulative budget limit')
    return ContinuationLaunch(config_path, output_root, expected_sha256, raw)


def record_approval(launch, *, confirmation=None, reference=None):
    """Record a later owner approval for this continuation once."""
    launch.recheck()
    if launch.run_directory.exists() or launch.claim_directory.exists():
        raise AuthorizationError('This continuation already has run or controller evidence')
    if confirmation is None and reference is None:
        if not sys.stdin.isatty():
            raise AuthorizationError('Exact-run approval requires a terminal or a recorded owner instruction')
        print(json.dumps(launch.approval_scope(), indent=2, ensure_ascii=False), flush=True)
        print(f'To approve this continuation, type {launch.confirmation_phrase}', flush=True)
        confirmation = input()
        source = 'owner_terminal'
    elif confirmation is not None and opening._valid_reference(reference):
        source = 'coordinator_recorded_owner_instruction'
    else:
        raise AuthorizationError('A recorded owner instruction needs its exact scope and evidence reference')
    if confirmation != launch.confirmation_phrase:
        raise AuthorizationError('The approval does not match this exact continuation')
    record = {'schema_version': 1, 'scope': launch.approval_scope(),
              'approved_at_utc': opening._utc_now(), 'source': source, 'reference': reference,
              'confirmation_sha256': opening.digest(confirmation.encode())}
    opening._write_exclusive(launch.approval_path, record)
    return record


def verify_approval(launch):
    """Return the exact private owner receipt before access to credentials."""
    launch.recheck()
    return opening._approval_bytes(launch)


def _check_private_directory(path):
    info = opening.canonical_path(path).stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise AuthorizationError('Controller evidence directory must be private and operator-owned')


def _check_lock_file(stream, path):
    info = os.fstat(stream.fileno())
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid()
            or info.st_mode & 0o077 or not os.path.samestat(info, path.lstat())):
        raise AuthorizationError('Expected the original private controller lock file')


@contextmanager
def _open_lock_file(launch, *, create=False):
    path = opening.canonical_path(launch.controller_lock_path)
    try:
        if create:
            path.parent.mkdir(mode=0o700, exist_ok=True)
        _check_private_directory(path.parent)
        flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
        fd = os.open(path, flags | (os.O_CREAT if create else 0), 0o600)
    except OSError as exc:
        raise AuthorizationError('The private continuation controller lock is unavailable') from exc
    with os.fdopen(fd, 'r+b', buffering=0) as stream:
        _check_lock_file(stream, path)
        yield stream


def _write_lock_pointer(stream, raw):
    stream.seek(0)
    stream.truncate()
    if stream.write(raw) != len(raw):
        raise AuthorizationError('Could not store the active continuation lease')
    os.fsync(stream.fileno())


@dataclass
class _ControllerLock:
    launch: ContinuationLaunch
    stream: BinaryIO = field(repr=False)
    pid: int
    claimed: bool = False
    mutex: Lock = field(default_factory=Lock, repr=False)


@contextmanager
def controller_lock(launch):
    """Hold a stable private inode for the entire controller invocation."""
    launch.recheck()
    with _open_lock_file(launch, create=True) as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AuthorizationError('Another continuation controller is active') from exc
        _check_lock_file(stream, launch.controller_lock_path)
        # A prior pointer can survive a crash. Its separate immutable claim
        # remains evidence. It must become inactive before any new recovery.
        _write_lock_pointer(stream, b'')
        yield _ControllerLock(launch, stream, os.getpid())


def _read_claim(launch, claim_path, approval_sha256):
    path = opening.canonical_path(claim_path)
    if path.parent != launch.claim_directory:
        raise AuthorizationError('The lease is outside this continuation')
    raw = opening.read_regular(path, private=True)
    claim = opening.json_object(raw)
    keys = {'schema_version', 'config_sha256', 'run_id', 'run_directory',
            'approval_sha256', 'controller_pid', 'claimed_at_utc', 'nonce'}
    nonce, pid = claim.get('nonce'), claim.get('controller_pid')
    if (set(claim) != keys or type(claim['schema_version']) is not int or claim['schema_version'] != 1
            or claim['config_sha256'] != launch.sha256 or claim['run_id'] != launch.run_id
            or claim['run_directory'] != str(launch.run_directory) or claim['approval_sha256'] != approval_sha256
            or type(pid) is not int or pid <= 0 or not isinstance(nonce, str)
            or not re.fullmatch(r'[0-9a-f]{32}', nonce) or path.name != nonce + '.json'
            or raw != opening.encode(claim)):
        raise AuthorizationError('The controller lease does not match this exact continuation')
    opening._verify_utc(claim['claimed_at_utc'])
    return claim, opening.digest(raw)


def _lock_pointer(claim, claim_sha256):
    return opening.encode({'nonce': claim['nonce'], 'controller_pid': claim['controller_pid'],
                           'claim_sha256': claim_sha256})


def verify_claim(launch, claim_path, claim_sha256, *, controller_pid):
    """Check the durable lease, parent PID and current exclusive controller."""
    approval_sha256 = opening.digest(verify_approval(launch))
    claim, actual_sha256 = _read_claim(launch, claim_path, approval_sha256)
    if claim['controller_pid'] != controller_pid or actual_sha256 != claim_sha256:
        raise AuthorizationError('The controller lease does not match the claimed parent or digest')
    with _open_lock_file(launch) as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            if stream.read(4096) != _lock_pointer(claim, claim_sha256):
                raise AuthorizationError('The continuation lease is inactive')
        else:
            raise AuthorizationError('No active continuation controller holds the lock')
    return claim


def verified_claim_digests(launch):
    """Verify historical leases for dispatch reconciliation without a live controller."""
    approval_sha256 = opening.digest(verify_approval(launch))
    directory = opening.canonical_path(launch.claim_directory)
    try:
        _check_private_directory(directory)
    except FileNotFoundError:
        return set()
    return {_read_claim(launch, path, approval_sha256)[1] for path in directory.iterdir()}


class RunGrant:
    """One controller invocation's authorization for the exact 420-session suffix."""

    def __init__(self, launch, claim_path, claim_sha256):
        self.launch = launch
        self.claim_path = claim_path
        self.claim_sha256 = claim_sha256
        self._assigned = set()
        self._mutex = Lock()

    def check(self, plan, session_dir):
        verify_claim(self.launch, self.claim_path, self.claim_sha256, controller_pid=os.getpid())
        session_id = plan.get('session_id')
        if opening.encode(plan) != opening.encode(self.launch.session_plan(session_id)):
            raise AuthorizationError('The session plan differs from the authorized continuation')
        if opening.canonical_path(session_dir) != self.launch.session_directory(session_id):
            raise AuthorizationError('The session output differs from the authorized continuation')

    def assign(self, plan, session_dir):
        self.check(plan, session_dir)
        session_id = plan['session_id']
        with self._mutex:
            if session_id in self._assigned:
                raise AuthorizationError('This session has already been assigned to a transport')
            self._assigned.add(session_id)


def claim_controller(launch, lock):
    """Create one durable lease after the controller has reconciled run evidence."""
    if (type(lock) is not _ControllerLock or lock.launch != launch
            or lock.pid != os.getpid() or lock.stream.closed):
        raise AuthorizationError('A matching active continuation lock is required')
    with lock.mutex:
        if lock.claimed:
            raise AuthorizationError('This controller invocation already has a lease')
        _check_lock_file(lock.stream, launch.controller_lock_path)
        try:
            fcntl.flock(lock.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AuthorizationError('Another continuation controller is active') from exc
        approval_sha256 = opening.digest(verify_approval(launch))
        nonce = secrets.token_hex(16)
        claim = {'schema_version': 1, 'config_sha256': launch.sha256, 'run_id': launch.run_id,
                 'run_directory': str(launch.run_directory), 'approval_sha256': approval_sha256,
                 'controller_pid': os.getpid(), 'claimed_at_utc': opening._utc_now(), 'nonce': nonce}
        path = launch.claim_directory / (nonce + '.json')
        claim_sha256 = opening.digest(opening._write_exclusive(path, claim))
        _write_lock_pointer(lock.stream, _lock_pointer(claim, claim_sha256))
        lock.claimed = True
        return RunGrant(launch, path, claim_sha256)
