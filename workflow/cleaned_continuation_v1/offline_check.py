"""Rehearse the full continuation with inert replies and representative grading."""

from collections import Counter
import json
from pathlib import Path
from unittest.mock import patch

from cleaned_opening_v1.offline_check import fixture_wire

from . import authority, runner


def check(output):
    launch, _, opening = runner.load_launch()
    plans = launch.config['sessions'][authority.OPENING:]
    selected = {}
    for plan in plans:
        key = (plan['task'], plan['group'], plan['provider'])
        size = (Path(plan['packet_dir']) / 'prompt_draft.md').stat().st_size
        if key not in selected or size > selected[key][0]:
            selected[key] = size, plan['session_id']
    grade_ids = {sid for _, sid in selected.values()}
    assert len(grade_ids) == 12
    refusal = AssertionError('Offline rehearsal cannot access the wire')
    with (patch('socket.socket.connect', side_effect=refusal),
          patch('socket.create_connection', side_effect=refusal),
          patch.object(runner.transport, '_wire_child', side_effect=refusal)):
        summary = runner.run_fixture(output, fixture_wire, grade_ids=grade_ids)
    assert summary['status'] == 'completed' and summary['mode'] == 'http_fixture'
    assert summary['continuation_terminal_sessions'] == 420
    assert summary['continuation_unstarted'] == summary['reserved_without_terminal'] == 0
    assert summary['session_statuses'] == {'completed': 420}
    assert summary['evaluation_statuses'] == {'evaluated': 12, 'not_evaluated': 408}
    assert not launch.approval_path.exists() and not launch.run_directory.exists()
    ledger = runner._json(output / 'ledger.json')
    assert {sid: ledger[sid] for sid in opening} == opening
    assert len(list((output / 'checkpoints').glob('*.json'))) == 35
    requests = Counter()
    for plan in plans:
        sid = plan['session_id']
        folder = output / 'sessions' / sid
        result = runner._json(folder / 'result.json')
        assert result['final_source_sha256'] == plan['source_sha256']
        assert result['mode'] == 'http_fixture'
        assert result['transport_attempts'] == 2 and result['tool_calls'] == 1
        requests[plan['provider']] += result['transport_attempts']
        envelope_path = folder / 'evaluation.json'
        assert envelope_path.exists() == (sid in grade_ids)
        if sid in grade_ids:
            envelope = runner._json(envelope_path)
            assert envelope['observations']['evidence_class'] == 'FRESH_FIXTURE_SEPARATED_EVALUATION'
            score = envelope['score']
            targets = score['withdrawal']
            assert score['core_preservation']['complete'] and score['core_preservation']['loss_count'] == 0
            assert score['supplied_five']['complete']
            assert not targets['failed_control_case_ids']
            assert targets['met_count'] == (targets['eligible_case_count'] if plan['condition'] == 'RR' else 0)
    assert requests == {'openai': 420, 'anthropic': 420}
    return {'summary': summary, 'inert_requests_by_provider': dict(requests),
            'freshly_graded_fixture_ids': sorted(grade_ids)}


if __name__ == '__main__':
    print(json.dumps(check(authority.RUN_ROOT / 'offline_rehearsal_v1'), indent=2))
