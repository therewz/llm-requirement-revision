"""Verify and locally replay the accepted prefix of the capped session."""

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from cleaned_opening_v1 import authorization as records
from cleaned_opening_v1 import engine
from live_runner_v1 import runner as prior


SESSION_ID = 'S0033_SA_openai_r1'
REPLAYED_TURNS = 8
_TURN_EVENTS = (
    'dispatch_intent', 'http_attempt', 'response_saved', 'response_parsed',
    'usage', 'tool_intent', 'tool_result',
)


@dataclass(frozen=True)
class ToolReplay:
    call: dict = field(repr=False)
    result: dict = field(repr=False)
    workspace_files: dict
    result_sha256: str


@dataclass(frozen=True)
class History:
    origin: Path
    requests: tuple[dict, ...] = field(repr=False)
    responses: tuple[dict, ...] = field(repr=False)
    http_evidence: tuple[dict, ...] = field(repr=False)
    tools: tuple[ToolReplay, ...] = field(repr=False)
    initial_workspace: dict
    final_workspace: dict
    usage_usd: Decimal
    elapsed_seconds: float
    next_request: dict = field(repr=False)


def _require(condition, message):
    if not condition:
        raise engine.IntegrityError(message)


def _artifact(origin, event):
    _require(len(event['files']) == 1, 'Replay event must bind a single artifact')
    ref = event['files'][0]
    path = records.canonical_path(origin / ref['path'])
    _require(path.is_relative_to(origin), 'Replay artifact escaped its source run')
    data = records.read_regular(path)
    _require(len(data) == ref['bytes'] and engine.digest(data) == ref['sha256'],
             'Replay artifact no longer matches its journal')
    return data


def load_history(origin, original_plan):
    """Reconstruct the exact requests and tool results without running a tool."""
    origin = records.canonical_path(Path(origin))
    _require(original_plan['session_id'] == SESSION_ID and original_plan['provider'] == 'openai',
             'This replay only admits the capped session')
    adapter = prior._adapter(original_plan)
    result = engine.verify_session(original_plan, origin, adapter)
    _require(result['status'] == 'session_limit' and result['reason'] == 'model_turn_limit'
             and result['mode'] == 'live_http' and result['usage_complete'] is True
             and not result['resumed_uncertain']
             and result['model_turns'] == result['tool_calls'] == result['transport_attempts'] == REPLAYED_TURNS,
             'Original session is not the accepted eight-turn capped run')
    elapsed = (datetime.fromisoformat(result['finished_at_utc'])
               - datetime.fromisoformat(result['started_at_utc'])).total_seconds()
    limits = engine._validate_plan(original_plan)
    _require(0 <= elapsed < limits['session_seconds'] and limits['max_model_turns'] == REPLAYED_TURNS,
             'Original session timing or limit differs')
    journal = engine.Journal(origin)
    events = journal.events
    _require([event['event'] for event in events] == ['initialized'] + list(_TURN_EVENTS) * REPLAYED_TURNS + ['terminal'],
             'Original replay journal has unexpected events')

    packet = Path(original_plan['packet_dir'])
    prompt = records.read_regular(packet / 'prompt_draft.md')
    source = records.read_regular(packet / 'workspace/src/solution.py')
    _require(engine.digest(prompt) == original_plan['prompt_sha256']
             and engine.digest(source) == original_plan['source_sha256'],
             'Frozen replay prompt or source changed')
    initial = {'src/solution.py': {'sha256': engine.digest(source), 'bytes': len(source)}}
    _require(events[0]['workspace_files'] == initial, 'Original starting workspace differs')
    messages = [
        {'role': 'system', 'content': original_plan['operational_instruction']},
        {'role': 'user', 'content': prompt.decode('utf-8')},
    ]

    def request():
        return adapter.encode(original_plan['model'], deepcopy(messages), deepcopy(original_plan['tools']),
                              limits['max_output_tokens'], deepcopy(original_plan['settings']))

    requests, responses, receipts, tools = [], [], [], []
    response_ids, tool_ids = set(), set()
    for turn in range(1, REPLAYED_TURNS + 1):
        offset = 1 + (turn - 1) * len(_TURN_EVENTS)
        dispatch, http, response, parsed, usage, call, output = events[offset:offset + len(_TURN_EVENTS)]
        _require(all(event['attempt'] == turn for event in (dispatch, http, response, parsed, usage))
                 and dispatch['turn'] == call['turn'] == call['tool_index'] == output['tool_index'] == turn
                 and http['outcome'] == 'received',
                 'Original replay attempt or tool order differs')
        request_data = _artifact(origin, dispatch)
        payload = request()
        _require(engine.encoded(payload) == request_data, 'Saved request differs from reconstructed replay context')
        raw = records.json_object(_artifact(origin, response))
        normalized = records.json_object(_artifact(origin, parsed))
        tool_call = call['tool_call']
        _require(normalized['status'] == 'tool_calls' and normalized['model'] == original_plan['model']
                 and normalized['tool_calls'] == [tool_call]
                 and normalized['response_id'] not in response_ids and tool_call['id'] not in tool_ids,
                 'Saved response or tool identity differs')
        response_ids.add(normalized['response_id'])
        tool_ids.add(tool_call['id'])
        output_data = _artifact(origin, output)
        output_value = records.json_object(output_data)
        _require(output_value['status'] == 'ok' and engine.encoded(output_value) == output_data,
                 'Saved tool result differs from canonical replay evidence')
        requests.append(payload)
        responses.append(raw)
        receipts.append(records.json_object(_artifact(origin, http)))
        tools.append(ToolReplay(tool_call, output_value, output['workspace_files'], engine.digest(output_data)))
        messages.append({'role': 'assistant', 'content': normalized['text'],
                         'continuation': normalized['continuation'], 'tool_calls': [tool_call]})
        messages.append({'role': 'tool', 'tool_call_id': tool_call['id'],
                         'name': tool_call['name'], 'content': output_data.decode('utf-8')})

    _require(tools[-1].workspace_files == result['workspace_files'], 'Final replay workspace differs')
    return History(origin, tuple(requests), tuple(responses), tuple(receipts), tuple(tools),
                   initial, result['workspace_files'], records.amount(result['reported_cost_usd']),
                   elapsed, request())


class ReplayTools:
    """Return saved tool evidence and recreate only the recorded file writes."""

    def __init__(self, workspace, limits, history):
        self.workspace = records.canonical_path(Path(workspace))
        _require(not self.workspace.is_relative_to(history.origin), 'Replay must use a new workspace')
        self.runtime = prior.runtime.WorkspaceTools(self.workspace, limits)
        self.history = history
        self.replayed = 0
        _require(engine._snapshot(self.workspace) == history.initial_workspace,
                 'Replay workspace does not match the original start')

    def execute(self, name, arguments):
        if self.replayed == len(self.history.tools):
            return self.runtime.execute(name, arguments)
        saved = self.history.tools[self.replayed]
        before = (self.history.initial_workspace if self.replayed == 0
                  else self.history.tools[self.replayed - 1].workspace_files)
        _require(name == saved.call['name'] and arguments == saved.call['arguments']
                 and engine._snapshot(self.workspace) == before,
                 'Replayed tool call or its input workspace differs')
        if name == 'write_file':
            _require(self.runtime.execute(name, arguments) == saved.result, 'Recorded write could not be recreated')
        _require(engine._snapshot(self.workspace) == saved.workspace_files,
                 'Replayed tool workspace differs from recorded evidence')
        self.replayed += 1
        return deepcopy(saved.result)
