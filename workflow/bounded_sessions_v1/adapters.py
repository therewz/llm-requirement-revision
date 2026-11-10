"""Pure provider request/response adapters. No network, SDK, keys or transport."""
import copy
import json


def integer(value):
    if type(value) is not int or value < 0:
        raise ValueError('Missing/invalid usage count')
    return value


def text(value):
    if not isinstance(value, str) or not value:
        raise ValueError('Missing/invalid identifier')
    return value


def validate_history(messages):
    pending, seen = set(), set()
    for m in messages:
        if m['role'] == 'tool':
            call = m['tool_call_id']
            if call not in pending:
                raise ValueError('Unmatched/duplicate tool result')
            pending.remove(call)
        else:
            if pending:
                raise ValueError('Missing tool results before next message')
            for c in m.get('tool_calls', []):
                if c['id'] in seen:
                    raise ValueError('Duplicate tool call id')
                seen.add(c['id']); pending.add(c['id'])
    if pending:
        raise ValueError('Unanswered tool calls')


class OpenAIAdapter:
    provider = 'openai'
    api_version = 'Responses v1; documentation checked 2026-11-05'

    def encode(self, model, messages, tools, max_output_tokens, settings):
        validate_history(messages)
        if set(settings) - {'reasoning', 'service_tier'}:
            raise ValueError('Unsupported OpenAI settings')
        inputs = []
        for m in messages:
            if m['role'] == 'assistant':
                items = m.get('continuation')
                if not isinstance(items, list):
                    raise ValueError('Missing replayable provider output')
                inputs.extend(copy.deepcopy(items))
            elif m['role'] == 'tool':
                inputs.append({'type': 'function_call_output', 'call_id': m['tool_call_id'], 'output': m['content']})
            else:
                inputs.append({'role': m['role'], 'content': m['content']})
        return {'model': model, 'input': inputs, 'store': False,
                'include': ['reasoning.encrypted_content'],
                'tools': [{'type': 'function', 'name': t['name'], 'description': t['description'],
                           'parameters': t.get('parameters', t.get('input_schema')), 'strict': True} for t in tools],
                'tool_choice': 'auto', 'parallel_tool_calls': False,
                'max_output_tokens': max_output_tokens, **copy.deepcopy(settings)}

    def parse(self, raw):
        rid, model = text(raw.get('id')), text(raw.get('model'))
        usage = raw.get('usage')
        if not isinstance(usage, dict):
            raise ValueError('Missing usage')
        inp, out = integer(usage.get('input_tokens')), integer(usage.get('output_tokens'))
        details = usage.get('input_tokens_details') or {}
        cached = integer(details.get('cached_tokens', 0))
        written = integer(details.get('cache_write_tokens', 0))
        if cached + written > inp:
            raise ValueError('Invalid cache totals')
        items = raw.get('output')
        if not isinstance(items, list):
            raise ValueError('Missing output array')
        calls, texts, refusal = [], [], False
        for item in items:
            if item['type'] == 'function_call':
                if item.get('status', 'completed') != 'completed':
                    raise ValueError('Incomplete tool call')
                args = json.loads(item['arguments'])
                if type(args) is not dict:
                    raise ValueError('Tool arguments must be an object')
                calls.append({'id': text(item.get('call_id')), 'name': text(item.get('name')), 'arguments': args})
            elif item['type'] == 'message':
                if item.get('status', 'completed') != 'completed':
                    raise ValueError('Incomplete output message')
                if item.get('role') != 'assistant':
                    raise ValueError('Unexpected output message role')
                for c in item['content']:
                    if c['type'] == 'refusal': refusal = True
                    elif c['type'] == 'output_text': texts.append(c['text'])
                    else: raise ValueError('Unsupported output content')
            elif item['type'] != 'reasoning':
                raise ValueError('Unexpected server tool/output item')
        status = 'malformed'
        if raw.get('status') == 'incomplete': status = 'truncated'
        elif raw.get('status') == 'completed':
            status = 'refusal' if refusal else 'tool_calls' if calls else 'completed' if texts else 'malformed'
        if len({c['id'] for c in calls}) != len(calls):
            raise ValueError('Duplicate call ids')
        return {'response_id': rid, 'model': model, 'status': status, 'tool_calls': calls,
                'text': '\n'.join(texts), 'continuation': copy.deepcopy(items),
                'usage': {'input_tokens': inp, 'output_tokens': out,
                          'cache_read_input_tokens': cached, 'cache_write_input_tokens': written}}


class ClaudeAdapter:
    provider = 'anthropic'
    api_version = '2026-10-21'

    def encode(self, model, messages, tools, max_output_tokens, settings):
        validate_history(messages)
        if set(settings) - {'thinking', 'output_config'}:
            raise ValueError('Unsupported Claude settings')
        history, systems = [], []
        for m in messages:
            if m['role'] == 'system': systems.append(m['content'])
            elif m['role'] == 'assistant':
                if not isinstance(m.get('continuation'), list):
                    raise ValueError('Missing original assistant blocks')
                history.append({'role': 'assistant', 'content': copy.deepcopy(m['continuation'])})
            elif m['role'] == 'tool':
                content = {'type': 'tool_result', 'tool_use_id': m['tool_call_id'], 'content': m['content']}
                if history and history[-1]['role'] == 'user' and isinstance(history[-1]['content'], list):
                    history[-1]['content'].append(content)
                else: history.append({'role': 'user', 'content': [content]})
            else: history.append({'role': 'user', 'content': m['content']})
        return {'model': model, 'system': '\n\n'.join(systems), 'messages': history,
                'max_tokens': max_output_tokens, 'stream': False,
                'tool_choice': {'type': 'auto', 'disable_parallel_tool_use': True},
                'tools': [{'name': t['name'], 'description': t['description'],
                           'input_schema': t.get('parameters', t.get('input_schema'))} for t in tools],
                **copy.deepcopy(settings)}

    def parse(self, raw):
        rid, model = text(raw.get('id')), text(raw.get('model'))
        if raw.get('role') != 'assistant' or raw.get('type') != 'message':
            raise ValueError('Unexpected response type')
        u = raw.get('usage')
        if not isinstance(u, dict): raise ValueError('Missing usage')
        base, out = integer(u.get('input_tokens')), integer(u.get('output_tokens'))
        read, write = integer(u.get('cache_read_input_tokens', 0)), integer(u.get('cache_creation_input_tokens', 0))
        if (u.get('cache_creation') or {}).get('ephemeral_1h_input_tokens', 0):
            raise ValueError('Unconfigured 1-hour cache billing')
        if any(v for v in (u.get('server_tool_use') or {}).values()):
            raise ValueError('Unexpected server tool usage')
        items = raw.get('content')
        if not isinstance(items, list): raise ValueError('Missing content')
        calls, texts = [], []
        for item in items:
            if item['type'] == 'tool_use':
                if type(item.get('input')) is not dict: raise ValueError('Malformed tool input')
                calls.append({'id': text(item.get('id')), 'name': text(item.get('name')), 'arguments': item['input']})
            elif item['type'] == 'text': texts.append(item['text'])
            elif item['type'] not in ('thinking', 'redacted_thinking'):
                raise ValueError('Unexpected content/server tool')
        reason = raw.get('stop_reason')
        refusal = reason == 'refusal' or (raw.get('stop_details') or {}).get('type') == 'refusal'
        status = 'refusal' if refusal else 'truncated' if reason in ('max_tokens', 'model_context_window_exceeded') else 'malformed'
        if not refusal:
            if reason == 'tool_use' and calls: status = 'tool_calls'
            elif reason == 'end_turn' and not calls and texts: status = 'completed'
        if len({c['id'] for c in calls}) != len(calls): raise ValueError('Duplicate call ids')
        return {'response_id': rid, 'model': model, 'status': status, 'tool_calls': calls,
                'text': '\n'.join(texts), 'continuation': copy.deepcopy(items),
                'usage': {'input_tokens': base + read + write, 'output_tokens': out,
                          'cache_read_input_tokens': read, 'cache_write_input_tokens': write}}
