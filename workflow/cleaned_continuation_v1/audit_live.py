"""Verify and summarize the finalized live study without changing its evidence."""

from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
import json

from cleaned_opening_v1.launch_pin import LAUNCH_SHA256 as OPENING_LAUNCH_SHA256

from . import authority, runner
from .launch_pin import LAUNCH_SHA256

records = runner.records
DIMENSIONS = ('task', 'group', 'condition', 'provider')
MONEY_FIELDS = ('known_reported_usage_usd', 'settled_ledger_usage_usd',
                'known_usage_inside_reservation_usd', 'held_reservation_usd')
WIRE_FIELDS = ('wire_markers', 'accepted', 'rejected', 'unknown',
               'markers_in_unverified_partials', 'intents_without_marker', 'usage_records')


def _require(test, message):
    if not test:
        raise records.AuthorizationError(message)


def _load_verified():
    output = records.canonical_path(authority.RUN_ROOT / authority.RUN_ID)
    summary_path = records.canonical_path(output / 'summary.json')
    _require(summary_path.is_file(), 'Wait for the final live continuation summary before auditing')
    summary_raw = records.read_regular(summary_path)
    summary = records.json_object(summary_raw)
    _require(summary.get('mode') == 'live_http', 'Audit requires the real live continuation')

    opening_config = runner._json(authority.OPENING_CONFIG_PATH)
    host = opening_config['host']
    prefix = records.validate_launch(authority.OPENING_CONFIG_PATH, OPENING_LAUNCH_SHA256,
                                     host=host, output_root=authority.OPENING_CONFIG_PATH.parent)
    launch = authority.validate_launch(authority.CONFIG_PATH, LAUNCH_SHA256,
                                       host=host, output_root=authority.RUN_ROOT)
    runner._verify_frozen(launch, prefix)
    initial = runner.verify_opening(prefix)
    approval = authority.verify_approval(launch)
    config = launch.config
    header = runner._header(launch, output, 'live_http', approval)
    grader = runner._grader(config, launch.sha256)
    entries, pending, held = runner._restore(
        launch, output, header, initial, lambda _: grader, recover=False)
    plans = config['sessions']
    runner._checkpoints(output, header, plans, entries, save=False)
    stop = runner._saved_stop(output, plans, entries, pending, held, config['scheduler'])
    _require(summary_raw == records.encode(runner._summary(launch, header, initial, entries, stop)),
             'The final summary does not reconcile with verified live evidence')
    return launch, prefix, grader, initial, entries, {p['session_id'] for p in pending}, set(held), summary


def _wire_and_usage(plan, folder, markers):
    """Recompute known usage only from journal-bound raw provider replies."""
    counts = Counter(wire_markers=len(markers))
    if folder is None:
        counts.update(unknown=len(markers), markers_in_unverified_partials=len(markers))
        return counts, Counter(), Decimal(0)

    events = runner.engine.Journal(folder).events
    statuses = {}
    raw_replies = {}
    http_codes = Counter()
    adapter = runner.prior._adapter(plan)
    known = Decimal(0)
    for event in events:
        kind = event['event']
        if kind == 'dispatch_intent' and event['attempt'] not in markers:
            counts['intents_without_marker'] += 1
        elif kind == 'http_attempt' and event['attempt'] in markers:
            attempt = event['attempt']
            saved = json.loads(records.read_regular(folder / event['files'][0]['path'],
                                                   limit=2 * records.RECORD_LIMIT))
            receipt = saved.get('receipt') if saved is not None else None
            if receipt is not None:
                http_codes[str(receipt['status_code'])] += 1
            statuses[attempt] = event['outcome']
        elif kind == 'response_saved':
            raw_replies[event['attempt']] = runner._json(folder / event['files'][0]['path'])
        elif kind == 'usage':
            attempt = event['attempt']
            _require(attempt in markers and statuses.get(attempt) == 'received',
                     'Usage does not have a verified accepted wire receipt')
            usage = adapter.parse(raw_replies[attempt])['usage']
            cost = runner.engine.usage_cost(usage, plan['pricing'])
            _require(usage == event['usage'] and cost == records.amount(event['cost_usd']),
                     'Recorded usage disagrees with the raw provider reply')
            known += cost
            counts['usage_records'] += 1
    for attempt in markers:
        outcome = statuses.get(attempt)
        counts[{'received': 'accepted', 'rejected': 'rejected'}.get(outcome, 'unknown')] += 1
    return counts, http_codes, known


def _scores(baseline, envelope):
    """Count a layer's tests only when its verified score is complete."""
    eligible = len(baseline['eligible_case_ids'])
    starting_passes = set(baseline['core_baseline_pass_ids'])
    target = {'planned_cases': eligible, 'assessed_cases': 0, 'met_cases': None,
              'all_met': None, 'case_statuses': {}, 'linked_control_target_cases': 0,
              'linked_control_failed_target_cases': None}
    core = {'planned_baseline_passes': len(starting_passes), 'opportunities': 0, 'losses': None,
            'absolute_tests': 0, 'absolute_passes': None, 'gained_passes': None}
    supplied = {'absolute_tests': 0, 'absolute_passes': None}
    if envelope is None or envelope['status'] != 'evaluated':
        return target, core, supplied

    score = envelope['score']
    withdrawal = score['withdrawal']
    _require(withdrawal['eligible_case_count'] == eligible, 'The target denominator changed')
    if withdrawal['complete']:
        case_results = withdrawal['case_results']
        controls = [row['controls_ok'] for row in case_results if type(row.get('controls_ok')) is bool]
        target.update(assessed_cases=eligible, met_cases=withdrawal['met_count'],
                      all_met=withdrawal['all_targets_met'],
                      case_statuses=dict(Counter(row['status'] for row in case_results)),
                      linked_control_target_cases=len(controls),
                      linked_control_failed_target_cases=controls.count(False) if controls else None)

    preservation = score['core_preservation']
    _require(preservation['opportunity_count'] == len(starting_passes), 'The core denominator changed')
    if preservation['complete']:
        suite = preservation['revision_suite']
        core.update(opportunities=len(starting_passes), losses=preservation['loss_count'],
                    absolute_tests=suite['observed'], absolute_passes=suite['passed_count'],
                    gained_passes=len(set(suite['passed_ids']) - starting_passes))
    five = score['supplied_five']
    if five['complete']:
        supplied.update(absolute_tests=five['observed'], absolute_passes=five['passed_count'])
    return target, core, supplied


def _row(plan, baseline, phase, folder, entry, markers, *, pending, held):
    terminal = entry is not None and entry['status'] == 'terminal'
    envelope = None
    window = None
    counts, codes, known = _wire_and_usage(plan, folder if terminal else None, markers)
    settled = Decimal(0)
    reserve = Decimal(0)
    if terminal:
        result = runner._json(folder / 'result.json')
        status = entry['session_status']
        evaluation = entry['evaluation_status'] or 'not_evaluated'
        end = result['finished_at_utc']
        if entry['evaluation_status'] is not None:
            envelope = runner._json(folder / 'evaluation.json')
            end = max(end, envelope['timing']['finished_at_utc'])
        window = (result['started_at_utc'], end)
        recorded = records.amount(entry['charged_or_reserved_usd'])
        if entry['cost_uncertain']:
            reserve = recorded
        else:
            _require(known == recorded, 'Recomputed usage differs from the settled ledger charge')
            settled = recorded
    else:
        evaluation = 'unavailable'
        status = 'held_partial' if held else 'reserved_unstarted' if pending else 'unattempted'
        if entry is not None:
            _require(held or pending, 'Reserved session has no reconciliation status')
            reserve = records.amount(entry['charged_or_reserved_usd'])
    target, core, supplied = _scores(baseline, envelope)
    return {
        'session_id': plan['session_id'], 'session_number': plan['order'] + 1,
        **{key: plan[key] for key in DIMENSIONS}, 'phase': phase, 'terminal': terminal,
        'session_status': status, 'evaluation_status': evaluation,
        'requests': {key: counts[key] for key in WIRE_FIELDS}, 'http_receipt_statuses': dict(codes),
        'known_reported_usage_usd': str(known), 'settled_ledger_usage_usd': str(settled),
        'known_usage_inside_reservation_usd': str(known - settled), 'held_reservation_usd': str(reserve),
        'target': target, 'core': core, 'supplied_five_auxiliary': supplied,
    }, window


def _layer_totals(rows, key, sum_keys, nullable_keys):
    layers = [row[key] for row in rows]
    totals = {name: sum(layer[name] for layer in layers) for name in sum_keys}
    for name in nullable_keys:
        values = [layer[name] for layer in layers if layer[name] is not None]
        totals[name] = sum(values) if values else None
    return layers, totals


def _rollup(rows):
    requests = Counter()
    http_codes = Counter()
    money = {key: sum((records.amount(row[key]) for row in rows), Decimal(0)) for key in MONEY_FIELDS}
    for row in rows:
        requests.update(row['requests'])
        http_codes.update(row['http_receipt_statuses'])
    _require(requests['wire_markers'] == sum(requests[key] for key in ('accepted', 'rejected', 'unknown')),
             'Wire outcomes do not account for every marker')

    targets, target = _layer_totals(
        rows, 'target', ('planned_cases', 'assessed_cases', 'linked_control_target_cases'),
        ('met_cases', 'linked_control_failed_target_cases'))
    target_states = Counter()
    for layer in targets:
        target_states.update(layer['case_statuses'])
    target.update(qualified_sessions=sum(layer['planned_cases'] > 0 for layer in targets),
                  assessed_sessions=sum(layer['assessed_cases'] > 0 for layer in targets),
                  all_met_sessions=sum(layer['all_met'] is True for layer in targets),
                  case_statuses=dict(target_states))
    cores, core = _layer_totals(
        rows, 'core', ('planned_baseline_passes', 'opportunities', 'absolute_tests'),
        ('losses', 'absolute_passes', 'gained_passes'))
    core.update(preservation_assessed_sessions=sum(layer['losses'] is not None for layer in cores),
                complete_suite_sessions=sum(layer['absolute_passes'] is not None for layer in cores))
    fives, five = _layer_totals(rows, 'supplied_five_auxiliary', ('absolute_tests',), ('absolute_passes',))
    five['complete_suite_sessions'] = sum(layer['absolute_passes'] is not None for layer in fives)

    return {
        'planned_sessions': len(rows), 'terminal_sessions': sum(row['terminal'] for row in rows),
        'session_statuses': dict(Counter(row['session_status'] for row in rows)),
        'evaluation_statuses': dict(Counter(row['evaluation_status'] for row in rows)),
        'requests': {key: requests[key] for key in WIRE_FIELDS},
        'http_receipt_statuses': dict(http_codes),
        **{key: str(value) for key, value in money.items()},
        'accounted_or_reserved_usd': str(money['settled_ledger_usage_usd'] + money['held_reservation_usd']),
        'target': target, 'core': core, 'supplied_five_auxiliary': five,
    }


def _group(rows, keys):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    return [{**dict(zip(keys, values)), **_rollup(group)} for values, group in sorted(groups.items())]


def _timing(windows):
    """Report the observed terminal window, excluding unverified partials."""
    if not windows:
        return None
    started = min(datetime.fromisoformat(start) for start, _ in windows)
    finished = max(datetime.fromisoformat(end) for _, end in windows)
    return {'first_verified_edit_started_at_utc': started.isoformat(),
            'last_verified_edit_or_grade_finished_at_utc': finished.isoformat(),
            'elapsed_seconds': (finished - started).total_seconds()}


def _checkpoint(launch, prefix, rows):
    terminal_prefix = next((row['session_number'] - 1 for row in rows if not row['terminal']), len(rows))
    expected = {f'{number:03d}.json'
                for number in range(2 * authority.OPENING, terminal_prefix + 1, authority.OPENING)}
    saved = runner._children(launch.run_directory / 'checkpoints')
    _require(set(saved) == expected, 'Final continuation checkpoint coverage is incomplete')
    number = terminal_prefix // authority.OPENING * authority.OPENING
    path = (saved[f'{number:03d}.json'] if saved
            else prefix.run_directory / 'checkpoints/012.json')
    return {'through_session': number, 'path': str(path), 'sha256': records.digest(records.read_regular(path)),
            'continuation_checkpoints': len(saved)}


def audit():
    """Reconcile the real finalized opening and continuation and return JSON data."""
    launch, prefix, grader, initial, entries, pending, held, summary = _load_verified()
    plans = launch.config['sessions']
    old_header = runner._json(prefix.run_directory / 'run.json')
    opening_markers = runner._markers(
        prefix.claim_path.parent / (prefix.run_id + '.dispatches'),
        {p['session_id']: p for p in plans[:authority.OPENING]}, {old_header['approval_claim_sha256']})
    tail_markers = runner._markers(
        runner.transport.dispatch_directory(launch),
        {p['session_id']: p for p in plans[authority.OPENING:]}, authority.verified_claim_digests(launch))
    markers = {**opening_markers, **tail_markers}
    rows, windows = [], []
    for plan in plans:
        sid = plan['session_id']
        original = sid in initial
        folder = (prefix if original else launch).session_directory(sid)
        row, window = _row(
            plan, grader.scorer.rows[plan['participant_id']], 'opening' if original else 'continuation',
            folder, entries.get(sid), markers.get(sid, {}), pending=sid in pending, held=sid in held)
        rows.append(row)
        if not original and window is not None:
            windows.append(window)

    overall = _rollup(rows)
    by_provider = _group(rows, ('provider',))
    _require(len(rows) == authority.FULL_SESSIONS
             and overall['terminal_sessions'] == len(initial) + summary['continuation_terminal_sessions']
             and records.amount(overall['accounted_or_reserved_usd']) == records.amount(summary['accounted_or_reserved_usd'])
             and all(records.amount(row['accounted_or_reserved_usd'])
                     == records.amount(summary['by_provider_usd'][row['provider']]) for row in by_provider),
             'Final audited coverage or accounting disagrees with the saved summary')
    return {
        'schema_version': 1, 'mode': 'live_http', 'status': summary['status'],
        'summary_path': str(launch.run_directory / 'summary.json'), 'summary': summary,
        'last_checkpoint': _checkpoint(launch, prefix, rows), 'continuation_timing': _timing(windows),
        'overall': overall, 'by_provider': by_provider, 'by_phase': _group(rows, ('phase',)),
        'by_phase_and_provider': _group(rows, ('phase', 'provider')), 'by_cell': _group(rows, DIMENSIONS),
        'sessions': rows,
    }


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2, sort_keys=True))
