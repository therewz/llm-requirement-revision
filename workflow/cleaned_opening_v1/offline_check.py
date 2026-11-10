"""Run the exact opening schedule with deterministic, entirely local replies."""

import json

from . import runner


def fixture_wire(plan):
    """A read-only tool turn and final message from each provider fixture."""
    provider = plan['provider']
    attempt = 0

    def respond(request):
        nonlocal attempt
        attempt += 1
        payload = json.loads(request.body)
        if payload['model'] != plan['model'] or attempt > 2:
            raise AssertionError('Fixture saw an unexpected request')
        identity = f"offline_{plan['session_id']}_{attempt}"
        common = {'id': identity, 'model': plan['model'],
                  'usage': {'input_tokens': 100, 'output_tokens': 50}}
        if provider == 'openai':
            if attempt == 1:
                output = [{'type': 'function_call', 'status': 'completed', 'call_id': identity,
                           'name': 'read_file', 'arguments': '{"path":"src/solution.py"}'}]
            else:
                if not any(item.get('type') == 'function_call_output' for item in payload['input']):
                    raise AssertionError('Fixture tool result absent from OpenAI continuation')
                output = [{'type': 'message', 'status': 'completed', 'role': 'assistant',
                           'content': [{'type': 'output_text', 'text': 'Offline fixture left the source unchanged.'}]}]
            response = {**common, 'status': 'completed', 'output': output}
        else:
            if attempt == 1:
                content = [{'type': 'tool_use', 'id': identity, 'name': 'read_file',
                            'input': {'path': 'src/solution.py'}}]
            else:
                if not any(isinstance(row['content'], list) and
                           any(block.get('type') == 'tool_result' for block in row['content'])
                           for row in payload['messages']):
                    raise AssertionError('Fixture tool result absent from Anthropic continuation')
                content = [{'type': 'text', 'text': 'Offline fixture left the source unchanged.'}]
            response = {**common, 'type': 'message', 'role': 'assistant',
                        'stop_reason': 'tool_use' if attempt == 1 else 'end_turn', 'content': content}
        return 200, {'request-id': 'http_' + identity}, json.dumps(response).encode()

    return respond


def verify(output, summary):
    if (summary['mode'] != 'http_fixture' or summary['status'] != 'opening_batch_paused'
            or summary['terminal_sessions'] != 12 or summary['later_sessions_out_of_scope'] != 420
            or summary['evaluation_statuses'] != {'evaluated': 12}
            or summary['opening_unstarted'] or summary['reserved_without_terminal']):
        raise ValueError('Unexpected opening fixture outcome')
    launch = runner.load_launch()
    entries = runner.prior._read(output / 'ledger.json')
    if set(entries) != {p['session_id'] for p in launch.config['sessions']}:
        raise ValueError('Fixture did not cover the exact approved opening shape')
    for plan in launch.config['sessions']:
        folder = output / 'sessions' / plan['session_id']
        result = runner.engine.verify_session(plan, folder, runner.prior._adapter(plan))
        envelope = runner.prior._read(folder / 'evaluation.json')
        score = envelope['score']
        withdrawal = score['withdrawal']
        expected = 7 if plan['condition'] == 'RR' else 0
        if (result['mode'] != 'http_fixture' or result['transport_attempts'] != 2
                or result['tool_calls'] != 1 or result['final_source_sha256'] != plan['source_sha256']
                or envelope['status'] != 'evaluated' or not withdrawal['complete']
                or withdrawal['eligible_case_count'] != 7 or withdrawal['met_count'] != expected
                or withdrawal['failed_control_case_ids']
                or score['core_preservation']['loss_count'] != 0
                or not score['core_preservation']['complete']):
            raise ValueError('Fixture evidence differs from the known unchanged cleaned start')
    if launch.approval_path.exists() or launch.claim_path.exists() or launch.run_directory.exists():
        raise ValueError('An actual approval or live output appeared during the fixture')


if __name__ == '__main__':
    destination = runner.RUN_ROOT / 'offline_fixture_v1'
    summary = runner.run_fixture(destination, fixture_wire)
    verify(destination, summary)
    print(json.dumps(summary, indent=2))
