"""Freeze one supplementary extension of the capped Task B editing session."""

from copy import deepcopy
from pathlib import Path

from cleaned_continuation_v1 import authority as primary
from cleaned_continuation_v1 import audit_live
from cleaned_continuation_v1.launch_pin import LAUNCH_SHA256 as PRIMARY_SHA256
from cleaned_opening_v1 import authorization as records, runner as opening
from cleaned_starts_v1.prepare import write_same

from .history import load_history

ROOT = records.ROOT
RUN_ROOT = ROOT / 'runs/turn_extension_v1'
CONFIG_PATH = RUN_ROOT / 'launch_config.json'
RUN_ID = 'elmira-s0033-turn-extension-20261105-v1'
SESSION_ID = 'S0033_SA_openai_r1'
ORIGINAL_TURNS = 8
EXTENDED_TURNS = 13
PRIMARY_RUN = primary.RUN_ROOT / primary.RUN_ID
ORIGIN = PRIMARY_RUN / 'sessions' / SESSION_ID
CHECKPOINT = PRIMARY_RUN / 'checkpoints/432.json'
CHECKPOINT_SHA256 = 'ff13ce5fb96a2d98f7ace0b6e68e2cf809899edc959d0e7e03af40b52c462c98'
AUDIT = ROOT / 'reports/cleaned_continuation_v1/LIVE_AUDIT.json'
AUDIT_SHA256 = '0c42bc6996860b03791b6706b98ae63a8e9ef9840001df7f7396ca9d02b007f7'
STATUS = 'SUPPLEMENTARY_CAP_EXTENSION_REQUIRES_APPROVAL'
SCHEDULER = {'concurrency': 1, 'per_provider_concurrency': 1, 'run_cost_cap_usd': '1.00',
             'provider_cost_caps_usd': {'openai': '1.00', 'anthropic': '0.00'}}
BOUND_MODULES = ('scope.py', 'runner.py', 'engine.py', 'transport.py', 'history.py')


def _checked(path, digest):
    raw = records.read_regular(path)
    if records.digest(raw) != digest:
        raise records.AuthorizationError(f'Changed extension input {path.name}')
    return raw


def _primary_config():
    return records.json_object(_checked(primary.CONFIG_PATH, PRIMARY_SHA256))


def original_plan():
    plan = _primary_config()['sessions'][337]
    if (plan['session_id'] != SESSION_ID or plan['task'] != 'B' or plan['condition'] != 'SA'
            or plan['provider'] != 'openai' or plan['model'] != 'gpt-6.1-sol'
            or plan['limits']['max_model_turns'] != ORIGINAL_TURNS
            or plan['limits']['max_tool_calls'] + 1 != EXTENDED_TURNS):
        raise records.AuthorizationError('The capped study session differs from the expected one')
    return plan


def extended_plan():
    plan = deepcopy(original_plan())
    plan['limits']['max_model_turns'] = EXTENDED_TURNS
    return plan


def _prior_evidence(history):
    return {
        'study_config_sha256': PRIMARY_SHA256, 'study_checkpoint_sha256': CHECKPOINT_SHA256,
        'study_audit_sha256': AUDIT_SHA256, 'original_session_directory': str(ORIGIN),
        'session_id': SESSION_ID, 'replayed_turns': ORIGINAL_TURNS,
        'replayed_tools': len(history.tools), 'prior_usage_usd': str(history.usage_usd),
        'prior_elapsed_seconds': history.elapsed_seconds,
        'first_new_request_sha256': records.digest(records.encode(history.next_request)),
    }


def build_launch():
    """Prepare one exact config and bind the immutable main-study evidence."""
    validated, _, _, _, _, _, _, summary = audit_live._load_verified()
    if summary['status'] != 'completed' or validated.sha256 != PRIMARY_SHA256:
        raise records.AuthorizationError('The main study is not the accepted finalized run')
    _checked(CHECKPOINT, CHECKPOINT_SHA256)
    _checked(AUDIT, AUDIT_SHA256)
    history = load_history(ORIGIN, original_plan())
    config = validated.config
    rows = {row['path']: row for row in config['bindings']}
    code = Path(__file__).resolve().parent
    origin_paths = []
    for path in ORIGIN.rglob('*'):
        records.canonical_path(path)
        if path.is_file():
            origin_paths.append(path)
        elif not path.is_dir():
            raise records.AuthorizationError('Unexpected original session artifact type')
    paths = {primary.CONFIG_PATH, CHECKPOINT, AUDIT, PRIMARY_RUN / 'run.json',
             PRIMARY_RUN / 'summary.json', PRIMARY_RUN / 'ledger.json',
             Path(primary.__file__).with_name('launch_pin.py')}
    for path in paths | set(origin_paths) | {code / name for name in BOUND_MODULES}:
        row = opening._binding(path)
        if row['path'] in rows and rows[row['path']] != row:
            raise records.AuthorizationError('A main-study binding changed during extension preparation')
        rows[row['path']] = row
    launch = {
        'schema_version': 1, 'run_id': RUN_ID, 'run_directory': str(RUN_ROOT / RUN_ID),
        'status': STATUS, 'host': config['host'], 'sessions': [extended_plan()],
        'scheduler': SCHEDULER, 'origin': _prior_evidence(history),
        'cleaned_preparation_sha256': config['cleaned_preparation_sha256'],
        'cleaned_baseline_manifest_sha256': config['cleaned_baseline_manifest_sha256'],
        'grader_parity_sha256': config['grader_parity_sha256'],
        'bindings': sorted(rows.values(), key=lambda row: row['path']),
    }
    raw = records.encode(launch)
    write_same(records.canonical_path(CONFIG_PATH), raw)
    return records.digest(raw)


def load_launch():
    """Verify the compiled pin and exact case before any credential can be read."""
    from .launch_pin import LAUNCH_SHA256

    raw = _checked(CONFIG_PATH, LAUNCH_SHA256)
    config = records.json_object(raw)
    primary_config = _primary_config()
    if (config['schema_version'] != 1 or config['run_id'] != RUN_ID or config['status'] != STATUS
            or config['run_directory'] != str(RUN_ROOT / RUN_ID)
            or config['host'] != primary_config['host']
            or config['host']['machine_binding_sha256'] != records.local_host_binding()
            or config['sessions'] != [extended_plan()] or config['scheduler'] != SCHEDULER
            or any(config[k] != primary_config[k] for k in (
                'cleaned_preparation_sha256', 'cleaned_baseline_manifest_sha256', 'grader_parity_sha256'))):
        raise records.AuthorizationError('The extension differs from its exact reviewed scope')
    _checked(CHECKPOINT, CHECKPOINT_SHA256)
    _checked(AUDIT, AUDIT_SHA256)
    opening._verify_bindings(config)
    records.canonical_path(RUN_ROOT / RUN_ID)
    return records.ValidatedLaunch(CONFIG_PATH, RUN_ROOT, LAUNCH_SHA256, raw)


def verify_history(launch):
    history = load_history(ORIGIN, original_plan())
    if launch.config['origin'] != _prior_evidence(history):
        raise records.AuthorizationError('The archived eight turns differ from the approved replay')
    return history
