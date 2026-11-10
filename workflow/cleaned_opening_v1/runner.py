"""Run only the reviewed first twelve cleaned sessions on the attested Mac."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
import argparse
import json
import os
from pathlib import Path

from live_runner_v1 import runner as prior
from cleaned_starts_v1.prepare import parent as check_original_selection
from cleaned_starts_v1.scoring import CleanedScorer

from . import authorization, engine, transport
from .evaluation import Evaluation

ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = ROOT / 'runs/cleaned_opening_v1'
CONFIG_PATH = RUN_ROOT / 'launch_config.json'
CLEANED = ROOT / 'runs/cleaned_starts_v1'
PARITY = ROOT / 'runs/separated_grader_v1/parity.json'
BASELINE_SHA256 = '059da520cb5289bc0ac5d3e17b6e1fb647d29092ea4e269b50ec3c6f7812a432'
PARITY_SHA256 = 'aec9dde3ea1ec0ed55d21c806baf993d4efb509d07a9994ace8957bde029d127'
PARITY_GRADER_CODE = {
    'code/separated_grader_v1/candidate.py': '4e3a9df15786fed6e9a8b2769a5584a114e8617cb0fd8df3b88846726667f50a',
    'code/separated_grader_v1/evaluate.py': '55bc2300d9054c08380d66ea7ee49dc52be7c17c839a87c41e2cb2d5285bca3f',
    'code/separated_grader_v1/worker.py': 'db5087cfce28dc9477dfa435b53f37ca0e8fbfe9d365a6429c884103a29626aa',
}
FULL_SESSIONS = 432
OPENING = 12


def _binding(path, expected=None):
    path = Path(path)
    if path != path.resolve() or not path.is_relative_to(ROOT) or path.is_symlink():
        raise ValueError(f'Unsafe launch binding: {path}')
    data = path.read_bytes()
    value = engine.digest(data)
    if expected is not None and value != expected:
        raise ValueError(f'Changed launch binding: {path.relative_to(ROOT)}')
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': value, 'bytes': len(data)}


def _verify_bindings(config):
    paths = set()
    for row in config['bindings']:
        if row['path'] in paths or _binding(ROOT / row['path'], row['sha256']) != row:
            raise ValueError('Duplicate or changed launch binding')
        paths.add(row['path'])


def _host():
    scratch = ROOT / 'tmp/cleaned_opening_v1_host'
    scratch.mkdir(parents=True, exist_ok=True)
    return {**prior.attest_mac(scratch), 'machine_binding_sha256': authorization.local_host_binding()}


def build_launch():
    """Freeze a concrete reviewable launch, without creating any approval."""
    original = check_original_selection()
    prep = CLEANED / 'preparation.json'
    baseline = CLEANED / 'baseline_manifest.json'
    paths = {}
    for path, expected in ((prep, authorization.PREPARATION_SHA256),
                           (baseline, BASELINE_SHA256), (PARITY, PARITY_SHA256)):
        row = _binding(path, expected)
        paths[row['path']] = row
    prepared = json.loads(prep.read_bytes())
    parity = json.loads(PARITY.read_bytes())
    if (parity['exact_target_and_status_parity'] is not True or parity['program_count'] != 72
            or parity['core_passes'] != 1221 or parity['cleaned_baseline_manifest_sha256'] != BASELINE_SHA256):
        raise ValueError('Cleaned-source grader parity has not been established')
    for info in json.loads((CLEANED / 'ARTIFACT_HASHES.json').read_bytes())['files']:
        row = _binding(ROOT / info['path'], info['sha256'])
        if row != info:
            raise ValueError('Cleaned artifact size differs')
        paths[row['path']] = row

    code_paths = [
        'code/cleaned_opening_v1/authorization.py', 'code/cleaned_opening_v1/transport.py',
        'code/cleaned_opening_v1/engine.py', 'code/cleaned_opening_v1/evaluation.py',
        'code/cleaned_opening_v1/runner.py', 'code/separated_grader_v1/candidate.py',
        'code/separated_grader_v1/worker.py', 'code/separated_grader_v1/evaluate.py',
        'code/separated_grader_v1/parity.py',
        'code/live_runner_v1/evaluation.py', 'code/live_runner_v1/runner.py',
        'code/live_runner_v1/engine.py', 'code/live_runner_v1/transport.py',
        'runs/cleaned_starts_v1/ARTIFACT_HASHES.json',
    ]
    for path in code_paths:
        paths[path] = _binding(ROOT / path, PARITY_GRADER_CODE.get(path))
    for row in original['bindings']:
        binding = _binding(ROOT / row['path'], row['sha256'])
        paths[binding['path']] = binding

    all_plans = prepared['sessions']
    if len(all_plans) != FULL_SESSIONS or len({p['session_id'] for p in all_plans}) != FULL_SESSIONS:
        raise ValueError('Cleaned schedule changed')
    plans = all_plans[:OPENING]
    if ([p['order'] for p in plans] != list(range(OPENING))
            or {p['participant_id'] for p in plans} != {'S0001', 'S0002'}):
        raise ValueError('Opening prefix changed')
    run_id = authorization.RUN_ID
    config = {
        'schema_version': 1, 'run_id': run_id, 'run_directory': str(RUN_ROOT / run_id),
        'status': 'PREPARED_REQUIRES_EXACT_ONE_USE_APPROVAL',
        'host': _host(), 'sessions': plans,
        'scheduler': {'concurrency': 4, 'per_provider_concurrency': 2,
                      'run_cost_cap_usd': '12.00',
                      'provider_cost_caps_usd': {'openai': '6.00', 'anthropic': '6.00'}},
        'full_study_session_count': FULL_SESSIONS,
        'full_study_ceiling_context': original['scheduler'],
        'cleaned_preparation_sha256': authorization.PREPARATION_SHA256,
        'cleaned_baseline_manifest_sha256': BASELINE_SHA256,
        'grader_parity_sha256': PARITY_SHA256,
        'bindings': sorted(paths.values(), key=lambda row: row['path']),
    }
    raw = authorization.encode(config)
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        if CONFIG_PATH.read_bytes() != raw:
            raise ValueError('Opening config differs from the saved version. Use a new reviewed run ID.')
    else:
        with CONFIG_PATH.open('xb') as handle:
            handle.write(raw)
    return engine.digest(raw)


def load_launch():
    """Read only the reviewed launch digest built into this version."""
    from .launch_pin import LAUNCH_SHA256
    raw = authorization.read_regular(CONFIG_PATH)
    if engine.digest(raw) != LAUNCH_SHA256:
        raise authorization.AuthorizationError('Reviewed opening config changed')
    config = authorization.json_object(raw)
    _verify_bindings(config)
    launch = authorization.validate_launch(CONFIG_PATH, LAUNCH_SHA256, host=_host(), output_root=RUN_ROOT)
    if (config['status'] != 'PREPARED_REQUIRES_EXACT_ONE_USE_APPROVAL'
            or config['full_study_session_count'] != FULL_SESSIONS
            or config['cleaned_preparation_sha256'] != authorization.PREPARATION_SHA256
            or config['cleaned_baseline_manifest_sha256'] != BASELINE_SHA256
            or config['grader_parity_sha256'] != PARITY_SHA256):
        raise authorization.AuthorizationError('Opening config has the wrong baseline or grader evidence')
    return launch


def _execute(launch, output, transport_factory, mode, *, grant=None):
    config = launch.config
    plans, scheduler = config['sessions'], config['scheduler']
    if len(plans) != OPENING:
        raise ValueError('Only the exact opening prefix may run')
    output = authorization.canonical_path(output)
    if output.parent != RUN_ROOT:
        raise ValueError('Run must be a direct child of the versioned output root')
    if mode == 'live_http':
        if grant is None or grant.launch != launch or output != launch.run_directory:
            raise authorization.AuthorizationError('Live opening requires the matching exact-run grant')
    elif mode != 'http_fixture' or grant is not None or output == launch.run_directory:
        raise ValueError('Fixture runs need a separate output path')

    # Fresh exclusive directory. A failed or interrupted launch keeps its
    # evidence and cannot be re-entered to resend previous attempts.
    output.mkdir(mode=0o700)
    header = {'run_id': launch.run_id, 'selection_sha256': launch.sha256,
              'run_directory': str(output), 'mode': mode, 'host': config['host'],
              'approval_claim_sha256': grant.claim_sha256 if grant is not None else None}
    prior._record_once(output / 'run.json', header)
    grader = Evaluation(CleanedScorer(authorization.PREPARATION_SHA256, BASELINE_SHA256), launch.sha256)
    ledger_path = output / 'ledger.json'
    entries = {}
    prior._save(ledger_path, entries)

    def one(plan):
        folder = output / 'sessions' / plan['session_id']
        adapter = prior._adapter(plan)
        connection = transport_factory(plan, folder)
        engine.run_session(plan, folder, connection, adapter, prior.runtime.WorkspaceTools)
        result = engine.verify_session(plan, folder, adapter)
        envelope = None
        if result['status'] == 'completed':
            envelope = grader.evaluate_completed(plan, folder, adapter, verify_session=engine.verify_session)
        return prior._entry(plan, folder, result, envelope, mode)

    reason = None
    with ThreadPoolExecutor(max_workers=scheduler['concurrency']) as pool:
        while len(entries) < OPENING:
            wave = prior._next_wave(plans, entries, scheduler, OPENING)
            if not wave:
                reason = 'budget_reservation_limit'
                break
            for plan in wave:
                entries[plan['session_id']] = {'status': 'reserved', 'provider': plan['provider'],
                    'charged_or_reserved_usd': plan['limits']['session_cost_cap_usd']}
            prior._save(ledger_path, entries)
            futures = {pool.submit(one, plan): plan['session_id'] for plan in wave}
            errors = []
            for future in as_completed(futures):
                sid = futures[future]
                try:
                    entries[sid] = future.result()
                except Exception as exc:
                    errors.append({'session_id': sid, 'exception_type': type(exc).__name__})
                prior._save(ledger_path, entries)
            if errors:
                prior._record_once(output / 'reconciliation_required.json', errors)
                reason = 'worker_failed_reservations_held'
                break
            reason = prior._stop_reason(entries)
            if reason:
                break

    # Revalidate stored results and evaluation before releasing the review
    # summary. No candidate source is rerun by this verification.
    by_id = {plan['session_id']: plan for plan in plans}
    for sid, entry in entries.items():
        if entry['status'] == 'terminal':
            plan = by_id[sid]
            folder = output / 'sessions' / sid
            adapter = prior._adapter(plan)
            result = engine.verify_session(plan, folder, adapter)
            envelope = (grader.verify_evaluation(plan, folder, adapter, verify_session=engine.verify_session)
                        if result['status'] == 'completed' else None)
            if prior._entry(plan, folder, result, envelope, mode) != entry:
                raise ValueError('Saved opening evidence differs from its ledger')
    _verify_bindings(config)
    terminal = [e for e in entries.values() if e['status'] == 'terminal']
    checkpoint = (prior._checkpoint(output, header, plans, entries, OPENING)
                  if len(terminal) == OPENING else None)
    cost = prior._total(entries)
    if cost > Decimal(scheduler['run_cost_cap_usd']) and reason is None:
        reason = 'reported_cost_exceeds_opening_ceiling'
    summary = {
        'run_id': launch.run_id, 'mode': mode, 'status': reason or 'opening_batch_paused',
        'config_sha256': launch.sha256, 'opening_checkpoint_sha256': checkpoint,
        'opening_sessions': OPENING, 'terminal_sessions': len(terminal),
        'reserved_without_terminal': len(entries) - len(terminal),
        'opening_unstarted': OPENING - len(entries), 'later_sessions_out_of_scope': FULL_SESSIONS - OPENING,
        'accounted_or_reserved_usd': str(cost),
        'by_provider_usd': {p: str(prior._total(entries, p)) for p in ('openai', 'anthropic')},
        'session_statuses': dict(Counter(e['session_status'] for e in terminal)),
        'evaluation_statuses': dict(Counter(e['evaluation_status'] or 'not_evaluated' for e in terminal)),
    }
    prior._record_once(output / 'summary.json', summary)
    return summary


def run_fixture(output, wire_factory):
    launch = load_launch()
    return _execute(launch, output,
                    lambda plan, _: transport.HTTPFixtureTransport(plan['provider'], wire_factory(plan)),
                    'http_fixture')


def _environment_credential(provider):
    name = {'openai': 'OPENAI_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY'}[provider]
    value = os.environ.get(name)
    if not value:
        raise authorization.AuthorizationError(f'The authorized provider credential is missing: {name}')
    return value


def run_live(credential_supplier=_environment_credential):
    launch = load_launch()
    authorization.verify_available_approval(launch)
    # Verify both accounts have local credentials after approval and before
    # either provider can receive a request. Keep the values in memory only.
    credentials = {}
    for provider in authorization.PROVIDERS:
        value = credential_supplier(provider)
        transport.build_http_request(provider, {}, value, 1)  # Pure shape check.
        credentials[provider] = value
    # Revalidate and consume atomically immediately before scheduling.
    grant = authorization.claim_approval(launch)
    return _execute(launch, launch.run_directory,
                    lambda plan, folder: transport.AuthorizedHTTPTransport(grant, plan, folder, credentials.__getitem__),
                    'live_http', grant=grant)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'check', 'approve', 'launch'))
    args = parser.parse_args()
    try:
        if args.action == 'build':
            print(build_launch())
        elif args.action == 'launch':
            print(json.dumps(run_live(), indent=2))
        else:
            launch = load_launch()
            if args.action == 'approve':
                result = authorization.record_approval(launch)
            else:
                result = {**launch.approval_scope(), 'approval_present': launch.approval_path.exists(),
                          'already_claimed': launch.claim_path.exists()}
            print(json.dumps(result, indent=2))
    except (authorization.AuthorizationError, ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, f'{exc}\n')


if __name__ == '__main__':
    main()
