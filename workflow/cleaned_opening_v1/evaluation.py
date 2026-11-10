"""Bind fresh separated grading and the cleaned scorer to terminal evidence."""

from datetime import datetime, timezone
import json
import time

from live_runner_v1 import evaluation as evidence
from separated_grader_v1 import evaluate as grader

SCHEMA = 'cleaned-opening-separated-evaluation-v1'
BOUNDARY = 'TRUSTED_PROXY_GRADER_PER_CALL_MACOS_SANDBOX_V1'


class Evaluation:
    def __init__(self, scorer, config_sha256):
        self.scorer = scorer
        self.config_sha256 = config_sha256

    def _context(self, plan, folder, adapter, verify_session):
        identity, result, binding, source = evidence._session_context(plan, folder, adapter, verify_session)
        if result['status'] != 'completed' or source is None:
            raise evidence.EvaluationIntegrityError('Only verified completed sessions can be graded')
        binding.update(launch_config_sha256=self.config_sha256, grader_boundary=BOUNDARY)
        return identity, result, binding, source

    def _derive(self, plan, result, identity, binding, observations):
        if (not isinstance(observations, dict)
                or any(observations.get(k) != v for k, v in identity.items())
                or observations.get('source_sha256') != binding['final_source_sha256']
                or observations.get('freeze_sha256') != grader.FREEZE_SHA256
                or observations.get('grader_boundary') != BOUNDARY
                or observations.get('effective_timezone') != 'UTC'
                or observations.get('no_feedback_to_agent') is not True
                or observations.get('evidence_class') != ('FRESH_LIVE_SEPARATED_EVALUATION'
                    if binding['live_session'] else 'FRESH_FIXTURE_SEPARATED_EVALUATION')):
            raise evidence.EvaluationIntegrityError('Observation provenance differs')
        first = evidence._timestamp(observations['started_at_utc'])
        last = evidence._timestamp(observations['finished_at_utc'])
        if last < first:
            raise evidence.EvaluationIntegrityError('Observation timestamps reversed')
        if observations['targets']['import_error'] is not None:
            if observations['evaluation_complete'] or observations['targets']['cases']:
                raise evidence.EvaluationIntegrityError('Invalid candidate import failure evidence')
            return 'code_failure', 'final_source_import_failed', self.scorer.score(plan, result, observations)
        if observations['evaluation_complete'] is not True:
            return 'evaluator_failure', 'trusted_grader_incomplete', None
        return 'evaluated', 'fresh_separated_observations_recorded', self.scorer.score(plan, result, observations)

    def _verify(self, path, plan, identity, result, binding):
        raw = grader.runtime._read_regular(path, evidence.MAX_RECORD_BYTES)
        try:
            value = json.loads(raw)
            stored_hash = value.pop('envelope_sha256')
            if (stored_hash != evidence._hash(evidence._encode(value))
                    or raw != evidence._encode({**value, 'envelope_sha256': stored_hash})):
                raise evidence.EvaluationIntegrityError('Evaluation envelope hash differs')
            if (value['schema'] != SCHEMA or value['identity'] != identity
                    or value['binding'] != binding or value['terminal_status'] != result['status']):
                raise evidence.EvaluationIntegrityError('Evaluation envelope does not match terminal evidence')
            timing = value['timing']
            first = evidence._timestamp(timing['started_at_utc'])
            last = evidence._timestamp(timing['finished_at_utc'])
            if (type(timing['elapsed_monotonic_ns']) is not int or timing['elapsed_monotonic_ns'] < 0
                    or timing['effective_timezone'] != 'UTC' or last < first):
                raise evidence.EvaluationIntegrityError('Invalid UTC timing')
            error = value['error']
            if error is None:
                expected = self._derive(plan, result, identity, binding, value['observations'])
            else:
                if (set(error) != {'stage', 'exception_type'}
                        or error['stage'] not in ('evaluate', 'score')
                        or not isinstance(error['exception_type'], str)
                        or not error['exception_type'].isidentifier()):
                    raise evidence.EvaluationIntegrityError('Invalid evaluator error evidence')
                expected = ('evaluator_failure', f"{error['stage']}_exception", None)
            if (value['status'], value['reason'], value['score']) != expected:
                raise evidence.EvaluationIntegrityError('Saved score differs from trusted evidence')
        except evidence.EvaluationIntegrityError:
            raise
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            raise evidence.EvaluationIntegrityError('Malformed separated evaluation envelope') from exc
        return {**value, 'envelope_sha256': stored_hash}

    def verify_evaluation(self, plan, session_dir, adapter, *, verify_session):
        folder = evidence._directory(session_dir)
        identity, result, binding, _ = self._context(plan, folder, adapter, verify_session)
        return self._verify(folder / evidence.EVIDENCE_NAME, plan, identity, result, binding)

    def evaluate_completed(self, plan, session_dir, adapter, *, verify_session):
        folder = evidence._directory(session_dir)
        identity, result, binding, source = self._context(plan, folder, adapter, verify_session)
        destination = folder / evidence.EVIDENCE_NAME
        if destination.exists() or destination.is_symlink():
            return self._verify(destination, plan, identity, result, binding)
        intent = folder / evidence.INTENT_NAME
        try:
            intent.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise evidence.EvaluationIntegrityError('Previous evaluation intent requires reconciliation') from exc
        evidence._sync_directory(folder)
        started = datetime.now(timezone.utc).isoformat()
        tick = time.monotonic_ns()
        observations = error = score = None
        stage = 'evaluate'
        try:
            observations = grader.evaluate_source_bytes(source, plan['task'], metadata=identity)
            observations['evidence_class'] = ('FRESH_LIVE_SEPARATED_EVALUATION' if binding['live_session']
                                               else 'FRESH_FIXTURE_SEPARATED_EVALUATION')
            stage = 'score'
            status, reason, score = self._derive(plan, result, identity, binding, observations)
        except Exception as exc:
            status, reason = 'evaluator_failure', f'{stage}_exception'
            error = {'stage': stage, 'exception_type': type(exc).__name__}
        record = {
            'schema': SCHEMA, 'identity': identity, 'binding': binding,
            'terminal_status': result['status'], 'status': status, 'reason': reason,
            'timing': {'started_at_utc': started,
                       'finished_at_utc': datetime.now(timezone.utc).isoformat(),
                       'elapsed_monotonic_ns': time.monotonic_ns() - tick, 'effective_timezone': 'UTC'},
            'observations': observations, 'score': score, 'error': error,
        }
        if self._context(plan, folder, adapter, verify_session)[2] != binding:
            raise evidence.EvaluationIntegrityError('Terminal source changed during evaluation')
        payload = {**record, 'envelope_sha256': evidence._hash(evidence._encode(record))}
        evidence._write_once(destination, payload)
        checked = self._verify(destination, plan, identity, result, binding)
        intent.rmdir()
        evidence._sync_directory(folder)
        return checked
