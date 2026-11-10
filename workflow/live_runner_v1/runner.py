"""Mac runner for the frozen bounded study. Only HTTP fixture runs are enabled."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
import json
from importlib.metadata import distributions
import platform
from pathlib import Path
import sys

from . import engine, evaluation, transport

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / 'runs/protocol_freeze_v1/selected_config.json'
FROZEN_SHA256 = '211d0ab082a81ab11ae133e72bb70a65fe42456f4e5cf24aeb6f2a1d2e15a5d3'
OUTPUT_ROOT = ROOT / 'runs/live_runner_v1'
LIVE_SEALED = True
STOP_STATES = {
    'delivery_uncertain', 'infrastructure_failure', 'response_identity_failure',
    'usage_or_parse_unassessable', 'malformed_response', 'malformed',
    'artifact_missing', 'request_rejected',
}

# The frozen modules are separate from the new versioned engine.
sys.path.insert(0, str(ROOT / 'code/bounded_sessions_v1'))
from adapters import OpenAIAdapter, ClaudeAdapter
import runtime
from protocol_freeze_v1.freeze import validate


def _read(path):
    if path.is_symlink() or not path.is_file():
        raise engine.IntegrityError(f'Missing or unsafe runner record: {path.name}')
    return json.loads(path.read_bytes())


def _save(path, obj):
    engine._atomic(path, engine.encoded(obj))


def _record_once(path, obj):
    if path.exists() or path.is_symlink():
        if _read(path) != obj:
            raise engine.IntegrityError(f'Existing {path.name} does not match verified evidence')
    else:
        _save(path, obj)


def _config():
    if not __debug__:
        raise engine.IntegrityError('Run verification requires Python assertions enabled')
    raw = FROZEN.read_bytes()
    if engine.digest(raw) != FROZEN_SHA256:
        raise engine.IntegrityError('Frozen selection hash changed')
    config = json.loads(raw)
    validate(config)
    return config


def attest_mac(base):
    """Check the frozen interpreter and exercise the existing Mac isolation."""
    if platform.system() != 'Darwin':
        raise RuntimeError('The selected isolation backend requires macOS')
    if not sys.executable or Path(sys.executable).resolve() != runtime.PYTHON.resolve():
        raise RuntimeError('Start with the frozen Mac interpreter')
    baseline = _read(ROOT / 'runs/withdrawal_keys_v1/freeze.json')
    interpreter_sha = engine.digest(runtime.PYTHON.read_bytes())
    if interpreter_sha != baseline['runtime']['interpreter_sha256'] or runtime.ENV['TZ'] != 'UTC':
        raise RuntimeError('Frozen evaluation interpreter or timezone changed')
    site = runtime.PYTHON.resolve().parent.parent / 'lib/python3.12/site-packages'
    expected = {name: baseline['runtime']['runtime'][name] for name in ('numpy', 'pytest')}
    actual = {dist.metadata['Name'].lower(): dist.version for dist in distributions(path=[str(site)])
              if dist.metadata['Name'].lower() in expected}
    if actual != expected:
        raise RuntimeError('Frozen evaluator package versions changed')
    runtime.isolation_preflight(base)
    return {
        'system': platform.system(),
        'release': platform.release(),
        'architecture': platform.machine(),
        'python_version': platform.python_version(),
        'interpreter_sha256': interpreter_sha,
        'sandbox_exec_sha256': engine.digest(Path('/usr/bin/sandbox-exec').read_bytes()),
        'timezone': runtime.ENV['TZ'],
        'evaluator_packages': actual,
    }


def _adapter(plan):
    return {'openai': OpenAIAdapter, 'anthropic': ClaudeAdapter}[plan['provider']]()


def _entry(plan, session_dir, result, envelope, mode):
    if result['mode'] != mode:
        raise engine.IntegrityError('Session transport mode differs from its run')
    # Parsed response IDs come from verified hash-linked files, not cached ledger fields.
    journal = engine.Journal(session_dir)
    response_ids = []
    for event in journal.events:
        if event['event'] == 'response_parsed':
            for ref in event['files']:
                response_ids.append(_read(session_dir / ref['path'])['response_id'])
    cost = result['reported_cost_usd']
    reserve = Decimal(plan['limits']['session_cost_cap_usd'])
    charge = reserve if cost is None else Decimal(cost)
    if not charge.is_finite() or charge < 0:
        raise engine.IntegrityError('Invalid session accounting')
    reason = None
    if result['status'] in STOP_STATES or cost is None:
        reason = result['status'] if result['status'] in STOP_STATES else 'unknown_usage'
    elif charge > reserve:
        reason = 'reported_cost_exceeds_session_ceiling'
    elif envelope is not None and envelope['status'] == 'evaluator_failure':
        reason = 'evaluation_infrastructure_failure'
    return {
        'status': 'terminal', 'provider': plan['provider'],
        'session_status': result['status'],
        'result_sha256': engine.digest(engine.encoded(result)),
        'evaluation_status': envelope['status'] if envelope is not None else None,
        'evaluation_sha256': engine.digest((session_dir / 'evaluation.json').read_bytes()) if envelope is not None else None,
        'charged_or_reserved_usd': str(charge), 'cost_uncertain': cost is None,
        'response_ids': response_ids, 'stop_reason': reason,
    }


def _verify_existing(plans, output, entries, mode):
    actual = set(entries)
    if actual != {p['session_id'] for p in plans[:len(actual)]}:
        raise engine.IntegrityError('Ledger is not a prefix of the frozen schedule')
    sessions = output / 'sessions'
    if sessions.is_symlink():
        raise engine.IntegrityError('Session directory is a symlink')
    if sessions.exists() and {p.name for p in sessions.iterdir()} != actual:
        raise engine.IntegrityError('Unrecorded or missing session directory')
    for p in plans[:len(actual)]:
        sid = p['session_id']
        if entries[sid]['status'] != 'terminal':
            raise engine.IntegrityError('Interrupted reservation requires reconciliation')
        directory = sessions / sid
        if directory.is_symlink() or not directory.is_dir():
            raise engine.IntegrityError('Unsafe session directory')
        adapter = _adapter(p)
        result = engine.verify_session(p, directory, adapter)
        envelope = None
        if result['status'] == 'completed':
            envelope = evaluation.verify_evaluation(p, directory, adapter, verify_session=engine.verify_session)
        elif (directory / 'evaluation.json').exists():
            raise engine.IntegrityError('Uncompleted session has unexpected evaluation')
        if _entry(p, directory, result, envelope, mode) != entries[sid]:
            raise engine.IntegrityError('Ledger entry differs from verified session evidence')


def _stop_reason(entries):
    seen = set()
    for entry in entries.values():
        for response_id in entry.get('response_ids', []):
            key = entry['provider'], response_id
            if key in seen:
                return 'duplicate_provider_response_id'
            seen.add(key)
    return next((entries[sid]['stop_reason'] for sid in sorted(entries) if entries[sid].get('stop_reason')), None)


def _total(entries, provider=None):
    return sum(
        (Decimal(row['charged_or_reserved_usd']) for row in entries.values()
         if provider is None or provider == row['provider']),
        Decimal(0),
    )


def _next_wave(plans, entries, scheduler, boundary):
    counts = Counter()
    wave = []
    reserved = Counter()
    start = len(entries)
    for plan in plans[start:min(start + scheduler['concurrency'], boundary)]:
        provider = plan['provider']
        reserve = Decimal(plan['limits']['session_cost_cap_usd'])
        if counts[provider] >= scheduler['per_provider_concurrency']:
            break
        if (_total(entries) + sum(reserved.values()) + reserve > Decimal(scheduler['run_cost_cap_usd'])
                or _total(entries, provider) + reserved[provider] + reserve > Decimal(scheduler['provider_cost_caps_usd'][provider])):
            break
        counts[provider] += 1
        reserved[provider] += reserve
        wave.append(plan)
    return wave


def _checkpoint(output, header, plans, entries, through):
    subset = {p['session_id']: entries[p['session_id']] for p in plans[:through]}
    record = {
        'through_scheduled_sessions': through, 'run': header,
        'verified_ledger_prefix_sha256': engine.digest(engine.encoded(subset)),
        'charged_or_reserved_usd': str(_total(subset)), 'stop_reason': _stop_reason(subset),
    }
    _record_once(output / 'checkpoints' / f'{through:03d}.json', record)
    return engine.digest(engine.encoded(record))


def _run(config, output, make_transport, mode, continuation):
    output = Path(output).absolute()
    if output != output.resolve() or output.parent != OUTPUT_ROOT:
        raise engine.IntegrityError('Choose a direct run directory under the versioned output root')
    if any(path.is_symlink() for path in (output, *output.parents)):
        raise engine.IntegrityError('Runner output must not traverse symlinks')
    output.mkdir(parents=True, exist_ok=True)
    lock = output / 'running.lock'
    with lock.open('x') as handle:
        handle.write('Runner active or interrupted. Reconcile before removing an abandoned lock.\n')
    try:
        return _run_locked(config, output, make_transport, mode, continuation)
    finally:
        lock.unlink()


def _run_locked(config, output, make_transport, mode, continuation):
    plans = config['sessions']
    opening = config['opening_batch']['mandatory_pause_after']
    if config['opening_batch']['session_ids'] != [p['session_id'] for p in plans[:opening]]:
        raise engine.IntegrityError('Opening schedule does not match the frozen selection')
    scheduler = config['scheduler']
    header = {
        'selection_sha256': FROZEN_SHA256, 'run_directory': str(output),
        'host': attest_mac(output), 'mode': mode,
    }
    for name in ('checkpoints', 'sessions'):
        if (output / name).is_symlink():
            raise engine.IntegrityError(f'Unsafe runner subdirectory: {name}')
    ledger_path = output / 'ledger.json'
    if not (output / 'run.json').exists() and any(p.name != 'running.lock' for p in output.iterdir()):
        raise engine.IntegrityError('Refusing an unrecognized nonempty output directory')
    _record_once(output / 'run.json', header)
    if ledger_path.exists() or ledger_path.is_symlink():
        entries = _read(ledger_path)
        _verify_existing(plans, output, entries, mode)
    else:
        if any(p.name not in ('running.lock', 'run.json') for p in output.iterdir()):
            raise engine.IntegrityError('Runner evidence exists without its ledger')
        entries = {}
        _save(ledger_path, entries)

    continuation_file = output / 'continuation.json'
    continued = False
    opening_digest = None
    if len(entries) < opening and (continuation is not None or continuation_file.exists()):
        raise engine.IntegrityError('Continuation precedes the verified opening batch')

    def one(plan):
        directory = output / 'sessions' / plan['session_id']
        adapter = _adapter(plan)
        engine.run_session(plan, directory, make_transport(plan), adapter, runtime.WorkspaceTools)
        result = engine.verify_session(plan, directory, adapter)
        if result['mode'] != mode:
            raise engine.IntegrityError('Session transport mode differs from its run')
        envelope = None
        if result['status'] == 'completed':
            envelope = evaluation.evaluate_completed(plan, directory, adapter, verify_session=engine.verify_session)
        return _entry(plan, directory, result, envelope, mode)

    reason = _stop_reason(entries)
    with ThreadPoolExecutor(max_workers=scheduler['concurrency']) as pool:
        while True:
            count = len(entries)
            # Recheck prior checkpoints on resume against their exact ledger prefixes.
            for through in range(opening, count + 1, opening):
                checkpoint_digest = _checkpoint(output, header, plans, entries, through)
                if through == opening:
                    opening_digest = checkpoint_digest
            if count >= opening and not continued:
                if reason and count == opening:
                    break
                approval = {'opening_checkpoint_sha256': opening_digest, 'run': header}
                if continuation_file.exists() or continuation_file.is_symlink():
                    if _read(continuation_file) != approval:
                        raise engine.IntegrityError('Continuation does not bind this opening checkpoint')
                    continued = True
                if continuation is not None:
                    if continuation != opening_digest:
                        raise engine.IntegrityError('Wrong opening checkpoint digest')
                    _record_once(continuation_file, approval)
                    continued = True
                if count > opening and not continued:
                    raise engine.IntegrityError('Work beyond the opening batch lacks continuation evidence')
                if not continued:
                    reason = 'opening_batch_paused'
                    break
            if reason or count == len(plans):
                break
            boundary = min(len(plans), (count // opening + 1) * opening)
            wave = _next_wave(plans, entries, scheduler, boundary)
            if not wave:
                reason = 'budget_reservation_limit'
                break
            for p in wave:
                entries[p['session_id']] = {
                    'status': 'reserved', 'provider': p['provider'],
                    'charged_or_reserved_usd': p['limits']['session_cost_cap_usd'],
                }
            _save(ledger_path, entries)
            pending = {pool.submit(one, p): p['session_id'] for p in wave}
            errors = []
            for future in as_completed(pending):
                sid = pending[future]
                try:
                    entries[sid] = future.result()
                except Exception as exc:
                    errors.append({'session_id': sid, 'exception_type': type(exc).__name__})
                _save(ledger_path, entries)
            if errors:
                _record_once(output / 'reconciliation_required.json', errors)
                raise engine.IntegrityError('A worker failed. Reservations remain held for reconciliation')
            reason = _stop_reason(entries)
    summary = {
        'mode': mode, 'planned_sessions': len(plans), 'terminal_sessions': len(entries),
        'unattempted_sessions': len(plans) - len(entries),
        'status': reason or 'completed', 'opening_checkpoint_sha256': opening_digest,
        'accounted_or_reserved_usd': str(_total(entries)),
        'states': dict(Counter(entry['session_status'] for entry in entries.values())),
        'evaluation_states': dict(Counter(entry['evaluation_status'] or 'not_evaluated' for entry in entries.values())),
    }
    _save(output / 'summary.json', summary)
    return summary


def run_fixture(output, wire_factory, *, continuation=None):
    """Exercise the actual runner with a supplied local HTTP response fixture."""
    config = _config()
    return _run(config, output, lambda p: transport.HTTPFixtureTransport(p['provider'], wire_factory(p)),
                'http_fixture', continuation)


def run_live(output, credential_supplier, *, continuation=None):
    """Reserved entry point for a later reviewed, run-specific launch."""
    if LIVE_SEALED or transport.LIVE_LOCK:
        raise transport.LiveDisabled('Live runner is sealed')
    config = _config()
    return _run(config, output,
                lambda p: transport.LockedHTTPTransport(p['provider'], lambda: credential_supplier(p['provider'])),
                'live_http', continuation)
