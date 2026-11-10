"""One-use approval for the exact cleaned 12-session opening.

This is a local operator gate. A coordinator record attests to a separately
received owner instruction; it does not authenticate chat authorship itself.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
from threading import Lock

ROOT = Path(__file__).resolve().parents[2]
PREPARATION = ROOT / 'runs/cleaned_starts_v1/preparation.json'
PREPARATION_SHA256 = '7e47fb664d89c70acb845fac90061c9d5920631d1223f3bac0e177b17b10565f'
RUN_ID = 'elmira-cleaned-opening-20261105-v1'
PROVIDERS = {'openai': 'gpt-6.1-sol', 'anthropic': 'claude-sonnet-5-5'}
OPENING_SESSIONS = 12
RECORD_LIMIT = 4 * 1024 * 1024


class AuthorizationError(RuntimeError):
    """A launch or request lacks the exact active authorization."""


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
            + '\n').encode()


def digest(data):
    return sha256(data).hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON property')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError('Nonfinite JSON number')


def json_object(data):
    try:
        value = json.loads(data, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AuthorizationError('Malformed launch or authorization data') from exc
    if not isinstance(value, dict):
        raise AuthorizationError('Expected a JSON object')
    return value


def canonical_path(path):
    value = Path(path)
    if not value.is_absolute() or value.resolve() != value:
        raise AuthorizationError('Authorization requires a canonical absolute path')
    if any(p.is_symlink() for p in (value, *value.parents)):
        raise AuthorizationError('Authorization paths cannot traverse symlinks')
    return value


def read_regular(path, *, private=False, limit=RECORD_LIMIT):
    path = canonical_path(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
                raise AuthorizationError('Expected bounded, single-link regular evidence')
            if private and (info.st_uid != os.getuid() or info.st_mode & 0o077):
                raise AuthorizationError('Approval evidence must be private and owned by this operator')
            data = stream.read(limit + 1)
    except OSError as exc:
        raise AuthorizationError('Required authorization or run evidence is unavailable') from exc
    if len(data) > limit:
        raise AuthorizationError('Authorization evidence exceeded its size limit')
    return data


def local_host_binding():
    """Record a local host fingerprint without disclosing its raw hostname."""
    info = os.uname()
    fields = {'system': info.sysname, 'hostname': info.nodename, 'release': info.release,
              'machine': info.machine, 'uid': os.getuid(), 'python': str(Path(sys.executable).resolve())}
    return digest(encode(fields))


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _verify_utc(value):
    try:
        stamp = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise AuthorizationError('Invalid authorization timestamp') from exc
    if stamp.utcoffset() != timezone.utc.utcoffset(stamp) or stamp.isoformat() != value:
        raise AuthorizationError('Authorization timestamp must use canonical UTC')


def amount(value):
    if not isinstance(value, str):
        raise AuthorizationError('Spend ceilings and ledger values must be decimal strings')
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise AuthorizationError('Invalid spend ceiling or ledger value') from exc
    if not number.is_finite() or number < 0:
        raise AuthorizationError('Invalid spend ceiling or ledger value')
    return number


@dataclass(frozen=True)
class ValidatedLaunch:
    config_path: Path
    output_root: Path
    sha256: str
    _raw: bytes = field(repr=False)

    @property
    def config(self):
        return json_object(self._raw)

    @property
    def run_id(self):
        return self.config['run_id']

    @property
    def run_directory(self):
        return Path(self.config['run_directory'])

    @property
    def approval_path(self):
        return self.output_root / 'authorizations' / (self.run_id + '.json')

    @property
    def claim_path(self):
        return self.output_root / 'authorizations' / (self.run_id + '.claimed.json')

    @property
    def confirmation_phrase(self):
        return f'APPROVE {self.run_id} {self.sha256}'

    def recheck(self):
        if read_regular(self.config_path) != self._raw or digest(self._raw) != self.sha256:
            raise AuthorizationError('The reviewed launch configuration changed')
        if self.config['host']['machine_binding_sha256'] != local_host_binding():
            raise AuthorizationError('The launch is bound to a different Mac or interpreter')
        canonical_path(self.run_directory)

    def session_plan(self, session_id):
        for plan in self.config['sessions']:
            if plan['session_id'] == session_id:
                return plan
        raise AuthorizationError('The session is outside the approved opening batch')

    def session_directory(self, session_id):
        plan = self.session_plan(session_id)
        return canonical_path(self.run_directory / 'sessions' / plan['session_id'])

    def approval_scope(self):
        config = self.config
        sessions = [{k: plan[k] for k in ('session_id', 'provider', 'model', 'order')}
                    | {'session_cost_cap_usd': plan['limits']['session_cost_cap_usd']}
                    for plan in config['sessions']]
        return {'run_id': self.run_id, 'config_sha256': self.sha256,
                'run_directory': str(self.run_directory), 'host': config['host'],
                'scheduler': config['scheduler'], 'sessions': sessions}


def validate_launch(config_path, expected_sha256, *, host, output_root):
    """Validate the caller's pinned launch digest and the fixed opening scope."""
    if not isinstance(expected_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise AuthorizationError('Expected the pinned SHA-256 of the reviewed configuration')
    config_path, output_root = canonical_path(config_path), canonical_path(output_root)
    if config_path != output_root / 'launch_config.json' or not output_root.is_dir():
        raise AuthorizationError('Unexpected launch configuration location')
    raw = read_regular(config_path)
    if digest(raw) != expected_sha256:
        raise AuthorizationError('The launch does not match the reviewed configuration digest')
    config = json_object(raw)
    if config.get('run_id') != RUN_ID or config.get('run_directory') != str(output_root / RUN_ID):
        raise AuthorizationError('The launch targets the wrong run or output directory')
    canonical_path(output_root / RUN_ID)
    if (not isinstance(host, dict) or not isinstance(config.get('host'), dict)
            or encode(config['host']) != encode(host) or host.get('system') != 'Darwin'
            or host.get('machine_binding_sha256') != local_host_binding()):
        raise AuthorizationError('The launch does not match this Mac and interpreter')
    prepared = read_regular(PREPARATION)
    if digest(prepared) != PREPARATION_SHA256:
        raise AuthorizationError('The cleaned preparation manifest changed')
    sessions = config.get('sessions')
    if (not isinstance(sessions, list) or len(sessions) != OPENING_SESSIONS
            or encode(sessions) != encode(json_object(prepared)['sessions'][:OPENING_SESSIONS])):
        raise AuthorizationError('Only the exact first twelve cleaned sessions are in scope')
    if Counter(p['provider'] for p in sessions) != {'openai': 6, 'anthropic': 6}:
        raise AuthorizationError('Opening provider balance changed')
    if any(p['model'] != PROVIDERS[p['provider']] or amount(p['limits']['session_cost_cap_usd']) != 1
           for p in sessions):
        raise AuthorizationError('Opening model or session ceiling changed')
    scheduler = config.get('scheduler')
    if (not isinstance(scheduler, dict)
            or type(scheduler.get('concurrency')) is not int or scheduler['concurrency'] != 4
            or type(scheduler.get('per_provider_concurrency')) is not int or scheduler['per_provider_concurrency'] != 2
            or amount(scheduler.get('run_cost_cap_usd')) != 12):
        raise AuthorizationError('Opening budget or scheduling limits changed')
    caps = scheduler.get('provider_cost_caps_usd')
    if not isinstance(caps, dict) or set(caps) != set(PROVIDERS) or any(amount(x) != 6 for x in caps.values()):
        raise AuthorizationError('Opening provider ceilings changed')
    return ValidatedLaunch(config_path, output_root, expected_sha256, raw)


def _write_exclusive(path, value):
    path = canonical_path(path)
    folder = path.parent
    folder.mkdir(mode=0o700, exist_ok=True)
    info = folder.stat()
    if not folder.is_dir() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise AuthorizationError('Approval directory must be private and owned by this operator')
    data = encode(value)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError as exc:
        raise AuthorizationError('Approval evidence already exists. This opening cannot be silently reused.') from exc
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    for directory in (folder, folder.parent):
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    return data


def _valid_reference(value):
    return isinstance(value, str) and len(value) <= 240 and bool(value.strip()) and value.isprintable()


def record_approval(launch, *, confirmation=None, reference=None):
    """Capture explicit later owner approval from a TTY or trusted coordinator."""
    launch.recheck()
    if launch.run_directory.exists() or launch.claim_path.exists():
        raise AuthorizationError('This opening has already been started or claimed')
    if confirmation is None and reference is None:
        if not sys.stdin.isatty():
            raise AuthorizationError('Exact-run approval requires a terminal or a recorded owner instruction')
        print(json.dumps(launch.approval_scope(), indent=2, ensure_ascii=False), flush=True)
        print(f'To approve this one opening batch, type {launch.confirmation_phrase}', flush=True)
        confirmation = input()
        source = 'owner_terminal'
    elif confirmation is not None and _valid_reference(reference):
        # The trusted coordinator supplies these only after actual owner approval.
        source = 'coordinator_recorded_owner_instruction'
    else:
        raise AuthorizationError('A recorded owner instruction needs its exact scope and evidence reference')
    if confirmation != launch.confirmation_phrase:
        raise AuthorizationError('The approval does not match this exact run')
    record = {'schema_version': 1, 'scope': launch.approval_scope(),
              'approved_at_utc': _utc_now(), 'source': source, 'reference': reference,
              'confirmation_sha256': digest(confirmation.encode())}
    _write_exclusive(launch.approval_path, record)
    return record


def _approval_bytes(launch):
    raw = read_regular(launch.approval_path, private=True)
    record = json_object(raw)
    source, reference = record.get('source'), record.get('reference')
    if (set(record) != {'schema_version', 'scope', 'approved_at_utc', 'source', 'reference', 'confirmation_sha256'}
            or type(record['schema_version']) is not int or record['schema_version'] != 1
            or encode(record.get('scope')) != encode(launch.approval_scope())
            or record.get('confirmation_sha256') != digest(launch.confirmation_phrase.encode())
            or not ((source == 'owner_terminal' and reference is None)
                    or (source == 'coordinator_recorded_owner_instruction' and _valid_reference(reference)))
            or raw != encode(record)):
        raise AuthorizationError('The approval record does not authorize this exact launch')
    _verify_utc(record['approved_at_utc'])
    return raw


def verify_available_approval(launch):
    """Check exact owner approval before credential preflight, without using it."""
    launch.recheck()
    if launch.run_directory.exists() or launch.claim_path.exists():
        raise AuthorizationError('This opening already started or was claimed')
    _approval_bytes(launch)


def verify_claim(launch, expected_claim_sha256, *, controller_pid):
    launch.recheck()
    approval = _approval_bytes(launch)
    raw = read_regular(launch.claim_path, private=True)
    claim = json_object(raw)
    if (set(claim) != {'schema_version', 'config_sha256', 'run_id', 'run_directory',
                      'approval_sha256', 'controller_pid', 'claimed_at_utc', 'nonce'}
            or type(claim['schema_version']) is not int or claim['schema_version'] != 1
            or digest(raw) != expected_claim_sha256
            or claim.get('config_sha256') != launch.sha256 or claim.get('run_id') != launch.run_id
            or claim.get('run_directory') != str(launch.run_directory)
            or claim.get('approval_sha256') != digest(approval)
            or type(claim.get('controller_pid')) is not int or claim['controller_pid'] != controller_pid
            or not isinstance(claim.get('nonce'), str) or not re.fullmatch(r'[0-9a-f]{32}', claim['nonce'])
            or raw != encode(claim)):
        raise AuthorizationError('The one-use authorization claim does not match this controller')
    _verify_utc(claim['claimed_at_utc'])
    return claim


class RunGrant:
    """An authorization lease valid only for this process and the first twelve sessions."""

    def __init__(self, launch, claim_sha256):
        self.launch = launch
        self.claim_sha256 = claim_sha256
        self._assigned = set()
        self._mutex = Lock()

    def check(self, plan, session_dir):
        verify_claim(self.launch, self.claim_sha256, controller_pid=os.getpid())
        session_id = plan.get('session_id')
        if encode(plan) != encode(self.launch.session_plan(session_id)):
            raise AuthorizationError('The session plan differs from the authorized opening')
        if canonical_path(session_dir) != self.launch.session_directory(session_id):
            raise AuthorizationError('The session output differs from the authorized opening')

    def assign(self, plan, session_dir):
        self.check(plan, session_dir)
        session_id = plan['session_id']
        with self._mutex:
            if session_id in self._assigned:
                raise AuthorizationError('This session has already been assigned to a transport')
            self._assigned.add(session_id)


def claim_approval(launch):
    """Consume an explicit, matching approval once. No automatic live restart."""
    launch.recheck()
    if launch.run_directory.exists():
        raise AuthorizationError('The opening needs a new, empty live output path')
    approval = _approval_bytes(launch)
    record = {'schema_version': 1, 'config_sha256': launch.sha256, 'run_id': launch.run_id,
              'run_directory': str(launch.run_directory), 'approval_sha256': digest(approval),
              'controller_pid': os.getpid(), 'claimed_at_utc': _utc_now(), 'nonce': secrets.token_hex(16)}
    raw = _write_exclusive(launch.claim_path, record)
    return RunGrant(launch, digest(raw))
