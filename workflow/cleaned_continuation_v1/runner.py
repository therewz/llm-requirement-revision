"""Continue the reviewed cleaned study from its immutable live opening."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path

from cleaned_opening_v1 import authorization as records
from cleaned_opening_v1 import runner as opening
from cleaned_opening_v1.evaluation import Evaluation
from cleaned_opening_v1.launch_pin import LAUNCH_SHA256 as OPENING_LAUNCH_SHA256
from cleaned_starts_v1.scoring import CleanedScorer

from . import authority, engine, transport

prior = opening.prior
STATUS = 'PREPARED_REQUIRES_EXACT_CONTINUATION_APPROVAL'
OPENING_USD = {'openai': '0.1703148', 'anthropic': '0.198530'}
BOUND_MODULES = ('authority.py', 'engine.py', 'runner.py', 'transport.py')


def _json(path):
    return records.json_object(records.read_regular(path))


def _children(directory):
    records.canonical_path(directory)
    if not directory.exists():
        return {}
    if not directory.is_dir():
        raise records.AuthorizationError('Expected an evidence directory')
    return {path.name: records.canonical_path(path) for path in directory.iterdir()}


def _opening_artifacts(launch):
    paths = {launch.config_path, Path(opening.__file__).with_name('launch_pin.py')}
    for directory in (launch.run_directory, launch.claim_path.parent):
        for path in directory.rglob('*'):
            records.canonical_path(path)
            if path.is_file():
                paths.add(path)
            elif not path.is_dir():
                raise records.AuthorizationError('Unexpected opening artifact type')
    return paths


def _markers(directory, plans, allowed_claims):
    indexed = {}
    for name, path in _children(directory).items():
        raw = records.read_regular(path, private=True)
        marker = records.json_object(raw)
        sid, attempt = marker.get('session_id'), marker.get('attempt')
        if (set(marker) != {'session_id', 'attempt', 'claim_sha256', 'dispatch_intent_sha256'}
                or not isinstance(sid, str) or sid not in plans
                or type(attempt) is not int or not 1 <= attempt <= 2 * plans[sid]['limits']['max_model_turns']
                or name != f'{sid}.{attempt:04d}.json'
                or marker.get('claim_sha256') not in allowed_claims
                or raw != records.encode(marker)):
            raise records.AuthorizationError('Unrecognized or out-of-scope dispatch marker')
        indexed.setdefault(sid, {})[attempt] = marker
    return indexed


def _verify_markers(folder, markers):
    journal = engine.Journal(folder)
    intents = {event['attempt']: event['sha256'] for event in journal.events if event['event'] == 'dispatch_intent'}
    receipts = {event['attempt'] for event in journal.events if event['event'] == 'http_attempt'
                and event['outcome'] in ('received', 'rejected')}
    if not receipts <= markers.keys() <= intents.keys():
        raise records.AuthorizationError('Dispatch markers disagree with saved HTTP evidence')
    if any(value['dispatch_intent_sha256'] != intents[number] for number, value in markers.items()):
        raise records.AuthorizationError('Dispatch marker differs from its intent')


def _grader(config, digest):
    scorer = CleanedScorer(config['cleaned_preparation_sha256'], config['cleaned_baseline_manifest_sha256'])
    return Evaluation(scorer, digest)


def _terminal(plan, folder, grader, mode, *, grade_missing=False):
    adapter = prior._adapter(plan)
    result = engine.verify_session(plan, folder, adapter)
    envelope = None
    if result['status'] == 'completed' and grader is not None:
        if grade_missing and not (folder / 'evaluation.json').exists():
            envelope = grader.evaluate_completed(plan, folder, adapter, verify_session=engine.verify_session)
        else:
            envelope = grader.verify_evaluation(plan, folder, adapter, verify_session=engine.verify_session)
    elif (folder / 'evaluation.json').exists() or (folder / 'evaluation.json').is_symlink():
        raise records.AuthorizationError('Unexpected evaluation for this terminal session')
    return prior._entry(plan, folder, result, envelope, mode)


def verify_opening(launch):
    """Reconcile the real accepted prefix without executing its programs."""
    root, config = launch.run_directory, launch.config
    header = _json(root / 'run.json')
    summary = _json(root / 'summary.json')
    ledger = _json(root / 'ledger.json')
    plans = {plan['session_id']: plan for plan in config['sessions']}
    checkpoint_path = root / 'checkpoints/012.json'
    checkpoint_raw = records.read_regular(checkpoint_path)
    checkpoint = records.json_object(checkpoint_raw)
    if (records.digest(checkpoint_raw) != authority.OPENING_CHECKPOINT_SHA256
            or launch.sha256 != OPENING_LAUNCH_SHA256
            or header != {'run_id': launch.run_id, 'selection_sha256': launch.sha256,
                          'run_directory': str(root), 'mode': 'live_http', 'host': config['host'],
                          'approval_claim_sha256': header.get('approval_claim_sha256')}
            or checkpoint != {'through_scheduled_sessions': 12, 'run': header,
                              'verified_ledger_prefix_sha256': records.digest(records.encode(ledger)),
                              'charged_or_reserved_usd': '0.3688448', 'stop_reason': None}
            or summary['opening_checkpoint_sha256'] != authority.OPENING_CHECKPOINT_SHA256
            or summary['status'] != 'opening_batch_paused' or summary['mode'] != 'live_http'
            or summary['terminal_sessions'] != 12 or summary['opening_unstarted'] != 0
            or summary['reserved_without_terminal'] != 0 or summary['by_provider_usd'] != OPENING_USD
            or set(ledger) != set(plans) or set(_children(root / 'sessions')) != set(plans)):
        raise records.AuthorizationError('Opening checkpoint, summary or session coverage changed')
    old_claim = records.json_object(records.read_regular(launch.claim_path, private=True))
    records.verify_claim(launch, header['approval_claim_sha256'], controller_pid=old_claim['controller_pid'])
    marker_dir = launch.claim_path.parent / (launch.run_id + '.dispatches')
    marks = _markers(marker_dir, plans, {header['approval_claim_sha256']})
    grader = _grader(config, launch.sha256)
    for sid, plan in plans.items():
        folder = launch.session_directory(sid)
        derived = _terminal(plan, folder, grader, 'live_http')
        _verify_markers(folder, marks.get(sid, {}))
        if (derived != ledger[sid] or derived['session_status'] != 'completed'
                or derived['evaluation_status'] != 'evaluated' or derived['cost_uncertain']):
            raise records.AuthorizationError('Opening grades or accounting changed')
    if (prior._stop_reason(ledger) or sum(map(len, marks.values())) != 48
            or {p: prior._total(ledger, p) for p in OPENING_USD}
            != {p: records.amount(cost) for p, cost in OPENING_USD.items()}):
        raise records.AuthorizationError('Opening usage did not reconcile')
    return ledger


def build_launch():
    """Prepare the exact continuation configuration without any approval."""
    prefix = opening.load_launch()
    ledger = verify_opening(prefix)
    config = prefix.config
    plans = _json(records.PREPARATION)['sessions']
    code = Path(__file__).resolve().parent
    rows = {row['path']: row for row in config['bindings']}
    for path in _opening_artifacts(prefix) | {code / name for name in BOUND_MODULES}:
        row = opening._binding(path)
        if row['path'] in rows and rows[row['path']] != row:
            raise records.AuthorizationError('An opening binding changed while freezing the continuation')
        rows[row['path']] = row
    frozen = {
        **config, 'run_id': authority.RUN_ID, 'run_directory': str(authority.RUN_ROOT / authority.RUN_ID),
        'status': STATUS, 'sessions': plans, 'scheduler': authority.SCHEDULER,
        'opening_count': authority.OPENING, 'opening_checkpoint_sha256': authority.OPENING_CHECKPOINT_SHA256,
        'opening_launch_sha256': prefix.sha256, 'opening_ledger_sha256': records.digest(records.encode(ledger)),
        'bindings': sorted(rows.values(), key=lambda row: row['path']),
    }
    frozen.pop('full_study_ceiling_context')
    frozen.pop('full_study_session_count')
    raw = records.encode(frozen)
    path = records.canonical_path(authority.CONFIG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if records.read_regular(path) != raw:
            raise records.AuthorizationError('Existing continuation config differs. Prepare a new version.')
    else:
        engine._atomic(path, raw)
    return records.digest(raw)


def load_launch():
    from .launch_pin import LAUNCH_SHA256

    prefix = opening.load_launch()
    launch = authority.validate_launch(authority.CONFIG_PATH, LAUNCH_SHA256,
                                       host=prefix.config['host'], output_root=authority.RUN_ROOT)
    _verify_frozen(launch, prefix)
    return launch, prefix, verify_opening(prefix)


def _verify_frozen(launch, prefix):
    opening._verify_bindings(launch.config)
    bound_paths = {opening.ROOT / row['path'] for row in launch.config['bindings']}
    opening_files = _opening_artifacts(prefix)
    if not opening_files <= bound_paths:
        raise records.AuthorizationError('The immutable opening artifact inventory changed')


def _header(launch, output, mode, approval):
    return {'run_id': launch.run_id, 'selection_sha256': launch.sha256, 'run_directory': str(output),
            'mode': mode, 'host': launch.config['host'],
            'opening_checkpoint_sha256': authority.OPENING_CHECKPOINT_SHA256,
            'opening_ledger_sha256': launch.config['opening_ledger_sha256'],
            'approval_sha256': None if approval is None else records.digest(approval)}


def _reservation(plan):
    return {'status': 'reserved', 'provider': plan['provider'],
            'charged_or_reserved_usd': plan['limits']['session_cost_cap_usd']}


def _restore(launch, output, header, initial, grader_for, *, recover):
    """Verify the cumulative prefix and identify safely unstarted reservations."""
    config = launch.config
    plans = config['sessions']
    mode = header['mode']
    output_files = _children(output)
    directories = _children(output / 'sessions')
    if mode == 'live_http':
        authorized = {p['session_id']: p for p in plans[authority.OPENING:]}
        marker_dir = transport.dispatch_directory(launch)
        marks = _markers(marker_dir, authorized, authority.verified_claim_digests(launch))
    else:
        marks = {}
    if ('run.json' in output_files and _json(output / 'run.json') != header
            or 'run.json' not in output_files and (directories or marks or 'ledger.json' in output_files)):
        raise records.AuthorizationError('Continuation header differs from the approved run')
    entries = _json(output / 'ledger.json') if 'ledger.json' in output_files else dict(initial)
    expected = {p['session_id'] for p in plans[:len(entries)]}
    if (set(entries) != expected or any(entries.get(sid) != row for sid, row in initial.items())
            or not (set(directories) | set(marks)) <= expected - initial.keys()):
        raise records.AuthorizationError('Ledger or session artifacts do not match the exact cumulative prefix')
    pending, held = [], []
    active = Counter()
    reserved_orders = []
    for plan in plans[authority.OPENING:len(entries)]:
        sid = plan['session_id']
        folder, markers = directories.get(sid), marks.get(sid, {})
        entry = entries[sid]
        reserved = entry == _reservation(plan)
        if reserved:
            active[plan['provider']] += 1
            reserved_orders.append(plan['order'])
            if folder is None and not markers:
                pending.append(plan)
                continue
            if folder is None:
                raise records.AuthorizationError('Dispatch marker has no matching session folder')
            result_path = records.canonical_path(folder / 'result.json')
            if not recover or not result_path.is_file():
                held.append(sid)
                continue
        elif folder is None:
            raise records.AuthorizationError('Terminal ledger entry has no session folder')
        if mode == 'live_http':
            _verify_markers(folder, markers)
        derived = _terminal(plan, folder, grader_for(plan), mode, grade_missing=reserved)
        if reserved:
            entries[sid] = derived
        elif derived != entry:
            raise records.AuthorizationError('Terminal ledger entry differs from its saved evidence')
    scheduler = config['scheduler']
    if (sum(active.values()) > scheduler['concurrency']
            or any(n > scheduler['per_provider_concurrency'] for n in active.values())):
        raise records.AuthorizationError('Prior reservations exceed the reviewed concurrency')
    if reserved_orders and (len(entries) - reserved_orders[0] > scheduler['concurrency']
                            or reserved_orders[0] // authority.OPENING != (len(entries) - 1) // authority.OPENING):
        raise records.AuthorizationError('Prior reservations do not fit one wave within a checkpoint')
    return entries, pending, held


def _checkpoints(output, header, plans, entries, *, save):
    folder = output / 'checkpoints'
    existing = _children(folder)
    settled = 0
    for plan in plans[:len(entries)]:
        if entries[plan['session_id']]['status'] != 'terminal':
            break
        settled += 1
    expected_names = set()
    for n in range(2 * authority.OPENING, settled + 1, authority.OPENING):
        name = f'{n:03d}.json'
        expected_names.add(name)
        prefix = {p['session_id']: entries[p['session_id']] for p in plans[:n]}
        record = {'through_scheduled_sessions': n, 'run': header,
                  'verified_ledger_prefix_sha256': records.digest(records.encode(prefix)),
                  'charged_or_reserved_usd': str(prior._total(prefix)), 'stop_reason': prior._stop_reason(prefix)}
        if name in existing:
            if records.read_regular(existing[name]) != records.encode(record):
                raise records.AuthorizationError('An existing continuation checkpoint differs')
        elif save:
            prior._record_once(folder / name, record)
    if set(existing) - expected_names:
        raise records.AuthorizationError('A checkpoint claims an unverified session prefix')


def _budget_fits(entries, scheduler):
    return (prior._total(entries) <= records.amount(scheduler['run_cost_cap_usd'])
            and all(prior._total(entries, provider) <= records.amount(cap)
                    for provider, cap in scheduler['provider_cost_caps_usd'].items()))


def _next_wave(plans, entries, scheduler):
    boundary = min(len(plans), (len(entries) // authority.OPENING + 1) * authority.OPENING)
    return prior._next_wave(plans, entries, scheduler, boundary)


def _saved_stop(output, plans, entries, pending, held, scheduler):
    failure_file = records.canonical_path(output / 'reconciliation_required.json')
    if failure_file.exists():
        failures = json.loads(records.read_regular(failure_file))
        reserved = {sid for sid, row in entries.items() if row['status'] == 'reserved'}
        if (not isinstance(failures, list) or not failures
                or any(not isinstance(row, dict) or set(row) != {'session_id', 'exception_type'}
                       or row['session_id'] not in reserved or not isinstance(row['exception_type'], str)
                       or not row['exception_type'].isidentifier() for row in failures)
                or len({row['session_id'] for row in failures}) != len(failures)):
            raise records.AuthorizationError('Worker failure evidence disagrees with held reservations')
        return 'worker_failed_reservations_held'
    if held:
        return 'interrupted_reservations_held'
    stop = prior._stop_reason(entries)
    if stop:
        return stop
    if not _budget_fits(entries, scheduler):
        return 'budget_reservation_limit'
    if not pending and len(entries) == len(plans):
        return None
    if not pending and not _next_wave(plans, entries, scheduler):
        return 'budget_reservation_limit'
    raise records.AuthorizationError('A final summary exists while approved sessions remain schedulable')


def _summary(launch, header, initial, entries, reason):
    suffix = {sid: entry for sid, entry in entries.items() if sid not in initial}
    terminal = [entry for entry in suffix.values() if entry['status'] == 'terminal']
    return {
        'run_id': launch.run_id, 'mode': header['mode'], 'status': reason or 'completed',
        'config_sha256': launch.sha256, 'opening_checkpoint_sha256': authority.OPENING_CHECKPOINT_SHA256,
        'study_planned_sessions': authority.FULL_SESSIONS, 'opening_terminal_sessions': len(initial),
        'continuation_planned_sessions': authority.FULL_SESSIONS - len(initial),
        'continuation_terminal_sessions': len(terminal),
        'reserved_without_terminal': len(suffix) - len(terminal),
        'continuation_unstarted': authority.FULL_SESSIONS - len(entries),
        'accounted_or_reserved_usd': str(prior._total(entries)),
        'by_provider_usd': {p: str(prior._total(entries, p)) for p in OPENING_USD},
        'continuation_usd_by_provider': {p: str(prior._total(suffix, p)) for p in OPENING_USD},
        'session_statuses': dict(Counter(row['session_status'] for row in terminal)),
        'evaluation_statuses': dict(Counter(row['evaluation_status'] or 'not_evaluated' for row in terminal)),
    }


def _execute(launch, prefix, output, header, initial, entries, pending, grader_for, make_transport, *, held):
    config = launch.config
    plans, scheduler, mode = config['sessions'], config['scheduler'], header['mode']
    output.mkdir(mode=0o700, exist_ok=True)
    prior._record_once(output / 'run.json', header)
    ledger_path = output / 'ledger.json'
    prior._save(ledger_path, entries)
    _checkpoints(output, header, plans, entries, save=True)

    def run_one(plan):
        folder = output / 'sessions' / plan['session_id']
        if folder.exists() or folder.is_symlink():
            raise records.AuthorizationError('Attempt to re-enter an existing session')
        adapter = prior._adapter(plan)
        engine.run_session(plan, folder, make_transport(plan, folder), adapter, prior.runtime.WorkspaceTools)
        return _terminal(plan, folder, grader_for(plan), mode, grade_missing=True)

    failure_file = records.canonical_path(output / 'reconciliation_required.json')
    reason = (_saved_stop(output, plans, entries, pending, held, scheduler) if failure_file.exists()
              else 'interrupted_reservations_held' if held else prior._stop_reason(entries))
    with ThreadPoolExecutor(max_workers=scheduler['concurrency']) as pool:
        while not reason:
            if not _budget_fits(entries, scheduler):
                reason = 'budget_reservation_limit'
                break
            if pending:
                wave, pending = pending, []
            elif len(entries) < len(plans):
                wave = _next_wave(plans, entries, scheduler)
                if not wave:
                    reason = 'budget_reservation_limit'
                    break
                for plan in wave:
                    entries[plan['session_id']] = _reservation(plan)
                prior._save(ledger_path, entries)
            else:
                break
            failures = []
            running = {pool.submit(run_one, plan): plan['session_id'] for plan in wave}
            for future in as_completed(running):
                sid = running[future]
                try:
                    entries[sid] = future.result()
                except Exception as exc:
                    failures.append({'session_id': sid, 'exception_type': type(exc).__name__})
                prior._save(ledger_path, entries)
            if failures:
                prior._record_once(output / 'reconciliation_required.json', sorted(failures, key=lambda row: row['session_id']))
                reason = 'worker_failed_reservations_held'
            else:
                reason = prior._stop_reason(entries)
                if len(entries) % authority.OPENING == 0:
                    _checkpoints(output, header, plans, entries, save=True)
                    if mode == 'live_http':
                        print(f'Checkpoint through session {len(entries)} of {len(plans)}.', flush=True)
    verified, _, _ = _restore(launch, output, header, initial, grader_for, recover=False)
    if verified != entries:
        raise records.AuthorizationError('The continuation ledger changed after execution')
    _checkpoints(output, header, plans, entries, save=True)
    _verify_frozen(launch, prefix)
    summary = _summary(launch, header, initial, entries, reason)
    prior._record_once(output / 'summary.json', summary)
    return summary


def run_fixture(output, wire_factory, *, grade_ids=()):
    launch, prefix, initial = load_launch()
    output = records.canonical_path(output)
    if output.parent != launch.output_root or output == launch.run_directory or output.exists():
        raise records.AuthorizationError('Fixture output must be a new nonlive run directory')
    grader = _grader(launch.config, launch.sha256)
    ids = set(grade_ids)
    return _execute(launch, prefix, output, _header(launch, output, 'http_fixture', None),
                    initial, dict(initial), [], lambda p: grader if p['session_id'] in ids else None,
                    lambda p, _: transport.HTTPFixtureTransport(p['provider'], wire_factory(p)), held=[])


def run_live(credential_supplier):
    launch, prefix, initial = load_launch()
    output = launch.run_directory
    with authority.controller_lock(launch) as lock:
        approval = authority.verify_approval(launch)
        header = _header(launch, output, 'live_http', approval)
        grader = _grader(launch.config, launch.sha256)
        grader_for = lambda _: grader
        summary_path = records.canonical_path(output / 'summary.json')
        failure_file = records.canonical_path(output / 'reconciliation_required.json')
        finalized = summary_path.exists()
        stopped = failure_file.exists()
        entries, pending, held = _restore(launch, output, header, initial, grader_for,
                                          recover=not (finalized or stopped))
        plans, scheduler = (launch.config[key] for key in ('sessions', 'scheduler'))
        _checkpoints(output, header, plans, entries, save=False)
        if finalized:
            summary = _json(summary_path)
            reason = _saved_stop(output, plans, entries, pending, held, scheduler)
            if _summary(launch, header, initial, entries, reason) != summary:
                raise records.AuthorizationError('Saved summary disagrees with the verified run')
            return summary
        if (stopped or held or prior._stop_reason(entries) or not _budget_fits(entries, scheduler)
                or not pending and not _next_wave(plans, entries, scheduler)):
            return _execute(launch, prefix, output, header, initial, entries, pending, grader_for,
                            None, held=held)
        credentials = {}
        for provider in records.PROVIDERS:
            value = credential_supplier(provider)
            transport.build_http_request(provider, {}, value, 1)
            credentials[provider] = value
        grant = authority.claim_controller(launch, lock)
        return _execute(launch, prefix, output, header, initial, entries, pending, grader_for,
                        lambda p, folder: transport.AuthorizedHTTPTransport(grant, p, folder, credentials.__getitem__),
                        held=held)
