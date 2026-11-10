"""Store fresh hidden-evaluation evidence for a verified terminal session.

The frozen evaluator and scorer retain their benchmark definitions. The
envelope detects corruption across resume, but cannot authenticate what
model-written Python does inside the frozen evaluator's process.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time


BOUNDED = Path(__file__).resolve().parents[1] / 'bounded_sessions_v1'
EVIDENCE_NAME = 'evaluation.json'
INTENT_NAME = 'evaluation.intent'
IDENTITY_FIELDS = ('session_id', 'participant_id', 'task', 'group',
                   'condition', 'provider', 'model', 'repeat')
MAX_RECORD_BYTES = 4 * 1024 * 1024


class EvaluationIntegrityError(ValueError):
    """Existing session or evaluator evidence needs reconciliation."""


def _frozen_module(name):
    spec = importlib.util.spec_from_file_location(f'live_runner_frozen_{name}', BOUNDED / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evaluator = _frozen_module('evaluate')
scorer = _frozen_module('scoring')


def _encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                       separators=(',', ':')) + '\n').encode()


def _hash(data):
    return sha256(data).hexdigest()


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _timestamp(value):
    if not isinstance(value, str):
        raise EvaluationIntegrityError('Missing UTC evaluation timestamp')
    stamp = datetime.fromisoformat(value)
    if stamp.utcoffset() != timezone.utc.utcoffset(stamp) or stamp.isoformat() != value:
        raise EvaluationIntegrityError('Noncanonical UTC evaluation timestamp')
    return stamp


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_once(path, value):
    data = _encode(value)
    if len(data) > MAX_RECORD_BYTES:
        raise EvaluationIntegrityError('Evaluation envelope exceeds record limit')
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.evaluation-', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            if path.exists() or path.is_symlink():
                raise EvaluationIntegrityError('Evaluation record already exists')
            # The caller holds the exclusive, durable evaluation intent.
            os.replace(temporary, path)
            _sync_directory(path.parent)
        finally:
            temporary.unlink(missing_ok=True)


def _session_context(plan, session_dir, adapter, verify_session):
    identity = {field: plan[field] for field in IDENTITY_FIELDS}
    read_regular = evaluator.runtime._read_regular
    journal = session_dir / 'events.jsonl'
    events = read_regular(journal, MAX_RECORD_BYTES)
    result = verify_session(plan, session_dir, adapter)
    if any(result.get(key) != value for key, value in identity.items()):
        raise EvaluationIntegrityError('Terminal session identity differs from evaluation plan')
    if read_regular(journal, MAX_RECORD_BYTES) != events:
        raise EvaluationIntegrityError('Session journal changed during verification')

    source = None
    if result['status'] == 'completed':
        source = read_regular(session_dir / 'final.py', evaluator.runtime.DEFAULTS['file_bytes'])
        if _hash(source) != result.get('final_source_sha256'):
            raise EvaluationIntegrityError('Final source differs from verified terminal session')

    binding = {
        'plan_sha256': _hash(_encode(plan)),
        'terminal_result_sha256': _hash(_encode(result)),
        'session_journal_sha256': _hash(events),
        'final_source_sha256': result.get('final_source_sha256'),
        'benchmark_freeze_sha256': evaluator.FREEZE_SHA256,
        'session_mode': result.get('mode'),
        'live_session': result.get('live_execution') is True,
    }
    return identity, result, binding, source


def _status(observations):
    """Interpret explicit runtime/worker evidence without attributing missingness."""
    targets = observations['targets']
    layers = [('targets', targets, targets['execution_metadata']),
              ('core28', observations['core28'], observations['core28']['metadata']),
              ('supplied5', observations['supplied5'], observations['supplied5']['metadata'])]
    for name, _, meta in layers:
        if (meta.get('status') != 'ok' or type(meta.get('returncode')) is not int
                or meta['returncode'] != 0 or meta.get('invalid_evaluator_output') is True):
            return 'evaluator_failure', f'{name}_worker_incomplete'
    if targets.get('execution_failure') or not isinstance(targets.get('cases'), dict):
        return 'evaluator_failure', 'target_observations_missing'
    import_error = targets.get('import_error')
    if import_error is not None:
        if (not isinstance(import_error, dict) or targets['cases']
                or not isinstance(import_error.get('type'), str)
                or not isinstance(import_error.get('message'), str)):
            return 'evaluator_failure', 'invalid_import_failure_evidence'
        # pytest collection exit code 2 can accompany an observed invalid import.
        # Internal pytest failure or a missing record still needs reconciliation.
        for name, _, meta in layers[1:]:
            if type(meta.get('pytest_exitcode')) is not int or meta['pytest_exitcode'] not in (0, 1, 2):
                return 'evaluator_failure', f'{name}_pytest_failure'
        return 'code_failure', 'final_source_import_failed'
    for name, observed, _ in layers:
        if observed.get('complete') is not True:
            return 'evaluator_failure', f'{name}_evidence_incomplete'
    return 'evaluated', 'fresh_observations_recorded'


def _score(plan, result, observations):
    score = scorer.score_observations(plan, result, observations)
    core = score.get('core_preservation')
    if core is not None:
        suite = core['revision_suite']
        core['gained_pass_ids'] = (
            sorted(set(suite['passed_ids']) - set(core['opportunity_ids']))
            if suite['complete'] and score['baseline_program_flags']['p2_core_complete'] == 'True'
            else None
        )
    return score


def _run_fresh(plan, identity, result, source):
    if source is None:
        return {'status': 'not_completed', 'reason': 'terminal_session_not_completed',
                'timing': None, 'observations': None, 'score': None, 'error': None}

    if evaluator.runtime.ENV.get('TZ') != 'UTC':
        raise EvaluationIntegrityError('Frozen evaluator subprocess timezone differs from UTC')
    started_at = _utc_now()
    started = time.monotonic_ns()
    observations, score, error = None, None, None
    stage = 'evaluate'
    try:
        observations = evaluator.evaluate_source_bytes(source, plan['task'], metadata=identity)
        observations['evidence_class'] = (
            'FRESH_POST_SESSION_HIDDEN_EVALUATION' if result.get('live_execution') is True
            else 'FRESH_OFFLINE_HIDDEN_EVALUATION'
        )
        observations['session_verified'] = True
        status, reason = _status(observations)
        if status != 'evaluator_failure':
            stage = 'score'
            score = _score(plan, result, observations)
    except Exception as exc:
        status, reason = 'evaluator_failure', f'{stage}_exception'
        error = {'stage': stage, 'exception_type': type(exc).__name__}

    finished_at = _utc_now()
    timing = {
        'started_at_utc': started_at,
        'finished_at_utc': finished_at,
        'effective_timezone': 'UTC',
        'clock': 'system_wall_clock',
        'wall_clock_regressed': _timestamp(finished_at) < _timestamp(started_at),
        'elapsed_monotonic_ns': time.monotonic_ns() - started,
    }
    return {'status': status, 'reason': reason, 'timing': timing,
            'observations': observations, 'score': score, 'error': error}


def _verify_record(path, plan, identity, result, binding):
    data = evaluator.runtime._read_regular(path, MAX_RECORD_BYTES)
    try:
        record = json.loads(data)
        if not isinstance(record, dict):
            raise EvaluationIntegrityError('Evaluation envelope must be an object')
        digest = record.pop('envelope_sha256')
        if digest != _hash(_encode(record)) or data != _encode({**record, 'envelope_sha256': digest}):
            raise EvaluationIntegrityError('Evaluation envelope hash or encoding differs')
        if (record['schema_version'] != 1 or record['identity'] != identity
                or record['binding'] != binding or record['terminal_status'] != result['status']):
            raise EvaluationIntegrityError('Evaluation envelope does not match verified session')

        status, timing, observations = record['status'], record['timing'], record['observations']
        score, error = record['score'], record['error']
        if result['status'] != 'completed':
            if (status != 'not_completed' or record['reason'] != 'terminal_session_not_completed'
                    or any(value is not None for value in (timing, observations, score, error))):
                raise EvaluationIntegrityError('Non-completed session has claimed evaluation evidence')
        else:
            first = _timestamp(timing['started_at_utc'])
            last = _timestamp(timing['finished_at_utc'])
            if (timing['effective_timezone'] != 'UTC' or timing['clock'] != 'system_wall_clock'
                    or timing['wall_clock_regressed'] is not (last < first)
                    or type(timing['elapsed_monotonic_ns']) is not int
                    or timing['elapsed_monotonic_ns'] < 0):
                raise EvaluationIntegrityError('Invalid UTC timing evidence')
            if error is not None:
                stage = error['stage']
                if (status != 'evaluator_failure' or score is not None
                        or stage not in ('evaluate', 'score')
                        or record['reason'] != f'{stage}_exception'
                        or not isinstance(error['exception_type'], str)):
                    raise EvaluationIntegrityError('Invalid exception evidence')
            else:
                expected = 'FRESH_POST_SESSION_HIDDEN_EVALUATION' if binding['live_session'] else 'FRESH_OFFLINE_HIDDEN_EVALUATION'
                if (observations['evidence_class'] != expected or observations['session_verified'] is not True
                        or observations['source_sha256'] != binding['final_source_sha256']
                        or observations['freeze_sha256'] != binding['benchmark_freeze_sha256']
                        or any(observations.get(key) != value for key, value in identity.items())):
                    raise EvaluationIntegrityError('Observation provenance differs')
                if (status, record['reason']) != _status(observations):
                    raise EvaluationIntegrityError('Evaluation status does not follow observations')
                rebuilt = None if status == 'evaluator_failure' else _score(plan, result, observations)
                if score != rebuilt:
                    raise EvaluationIntegrityError('Stored score does not follow observations')
    except EvaluationIntegrityError:
        raise
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        raise EvaluationIntegrityError('Malformed evaluation envelope') from exc
    return {**record, 'envelope_sha256': digest}


def _directory(session_dir):
    folder = Path(session_dir).absolute()
    if folder.is_symlink() or not folder.is_dir():
        raise EvaluationIntegrityError('Evaluation requires a real terminal session directory')
    return folder.resolve()


def verify_evaluation(plan, session_dir, adapter, *, verify_session):
    """Verify terminal and saved evaluation evidence without running source."""
    folder = _directory(session_dir)
    identity, result, binding, _ = _session_context(plan, folder, adapter, verify_session)
    return _verify_record(folder / EVIDENCE_NAME, plan, identity, result, binding)


def evaluate_completed(plan, session_dir, adapter, *, verify_session):
    """Freshly evaluate each completed final once, including unchanged source."""
    folder = _directory(session_dir)
    identity, result, binding, source = _session_context(plan, folder, adapter, verify_session)
    destination = folder / EVIDENCE_NAME
    if destination.exists() or destination.is_symlink():
        return _verify_record(destination, plan, identity, result, binding)

    intent = folder / INTENT_NAME
    try:
        intent.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise EvaluationIntegrityError('Previous evaluation intent needs reconciliation') from exc
    _sync_directory(folder)
    # The durable intent remains after an unexpected interruption. A restart
    # can use committed evidence or halt, but cannot silently evaluate again.
    record = {
        'schema_version': 1,
        'identity': identity,
        'binding': binding,
        'terminal_status': result['status'],
        **_run_fresh(plan, identity, result, source),
    }
    if _session_context(plan, folder, adapter, verify_session)[2] != binding:
        raise EvaluationIntegrityError('Terminal session changed during evaluation')
    payload = {**record, 'envelope_sha256': _hash(_encode(record))}
    _write_once(destination, payload)
    checked = _verify_record(destination, plan, identity, result, binding)
    intent.rmdir()
    _sync_directory(folder)
    return checked
