"""One sandboxed candidate operation. The child has no grader or expected answers."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import sys

VERSION = 1
MAX_DEPTH = 16
MAX_ITEMS = 2048
MAX_TEXT = 8192
MAX_MESSAGE = 500
FUNCTIONS = frozenset({'suggest_slots', 'is_allocation_feasible'})


class WireValueError(ValueError):
    pass


def encode_value(value, depth=0):
    """Encode only exact, bounded Python data values and preserve their types."""
    if depth > MAX_DEPTH:
        raise WireValueError('Value exceeds the wire nesting limit')
    kind = type(value)
    if value is None or kind in (bool, int):
        return value
    if kind is str and len(value) <= MAX_TEXT:
        value.encode('utf-8')
        return value
    if kind is float:
        if math.isfinite(value):
            return value
        return ['float', repr(value)]
    if kind in (list, tuple) and len(value) <= MAX_ITEMS:
        return [kind.__name__, [encode_value(item, depth + 1) for item in value]]
    if kind is dict and len(value) <= MAX_ITEMS:
        return ['dict', [[encode_value(k, depth + 1), encode_value(v, depth + 1)] for k, v in value.items()]]
    raise WireValueError('Unsupported value type or size')


def decode_value(value, depth=0):
    if depth > MAX_DEPTH:
        raise WireValueError('Value exceeds the wire nesting limit')
    kind = type(value)
    if value is None or kind in (bool, int):
        return value
    if kind is str and len(value) <= MAX_TEXT:
        value.encode('utf-8')
        return value
    if kind is float and math.isfinite(value):
        return value
    if kind is not list or len(value) != 2 or type(value[0]) is not str:
        raise WireValueError('Invalid value tag')
    tag, items = value
    if tag == 'float' and type(items) is str and items in ('nan', 'inf', '-inf'):
        return float(items)
    if type(items) is not list or len(items) > MAX_ITEMS:
        raise WireValueError('Invalid sequence payload')
    if tag in ('list', 'tuple'):
        decoded = [decode_value(item, depth + 1) for item in items]
        return decoded if tag == 'list' else tuple(decoded)
    if tag == 'dict':
        decoded = {}
        for pair in items:
            if type(pair) is not list or len(pair) != 2:
                raise WireValueError('Invalid dictionary entry')
            key, item = (decode_value(part, depth + 1) for part in pair)
            try:
                if key in decoded:
                    raise WireValueError('Duplicate dictionary key')
                decoded[key] = item
            except TypeError as exc:
                raise WireValueError('Unhashable dictionary key') from exc
        return decoded
    raise WireValueError('Unknown value tag')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise WireValueError('Duplicate JSON field')
        result[key] = value
    return result


def reject_constant(value):
    raise WireValueError('Nonfinite JSON literal')


def parse_json(data):
    return json.loads(data, object_pairs_hook=unique_object, parse_constant=reject_constant)


class OperationTimeout(BaseException):
    pass


def alarm(*_):
    raise OperationTimeout()


def exception_record(error, stage):
    try:
        message = str(error)[:MAX_MESSAGE]
    except BaseException:
        message = ''
    # These are the only exception match types used in the supplied tests.
    matched = 'ValueError' if isinstance(error, ValueError) else 'TypeError' if isinstance(error, TypeError) else None
    return {'kind': 'exception', 'stage': stage, 'exception_type': type(error).__name__[:128],
            'message': message, 'match_as': matched}


def operation(request):
    if not isinstance(request, dict) or request.get('version') != VERSION:
        raise WireValueError('Invalid request version')
    kind = request.get('operation')
    if kind == 'import' and set(request) == {'version', 'operation'}:
        function, args, kwargs = None, (), {}
    elif kind == 'call' and set(request) == {'version', 'operation', 'function', 'args', 'kwargs'}:
        function = request['function']
        args, kwargs = decode_value(request['args']), decode_value(request['kwargs'])
        if function not in FUNCTIONS or type(args) is not tuple or type(kwargs) is not dict or any(type(k) is not str for k in kwargs):
            raise WireValueError('Invalid call request')
    else:
        raise WireValueError('Invalid operation')

    set_timer = signal.setitimer
    signal.signal(signal.SIGALRM, alarm)
    with open(os.devnull, 'w') as sink, redirect_stdout(sink), redirect_stderr(sink):
        stage = 'import'
        try:
            set_timer(signal.ITIMER_REAL, 5)
            spec = importlib.util.spec_from_file_location('solution', 'solution.py')
            module = importlib.util.module_from_spec(spec)
            sys.modules['solution'] = module
            spec.loader.exec_module(module)
            if function is None:
                return {'kind': 'return', 'value': None}
            stage = 'call'
            set_timer(signal.ITIMER_REAL, 2)
            value = getattr(module, function)(*args, **kwargs)
        except OperationTimeout:
            return {'kind': 'timeout', 'stage': stage}
        except BaseException as error:
            return exception_record(error, stage)
        finally:
            set_timer(signal.ITIMER_REAL, 0)
        try:
            return {'kind': 'return', 'value': encode_value(value)}
        except (WireValueError, UnicodeError, RecursionError, OverflowError):
            return {'kind': 'unsupported_return'}


def main():
    request = parse_json(Path('request.json').read_bytes())
    dumps = json.dumps
    stream = sys.stdout
    response = operation(request)
    stream.write(dumps({'version': VERSION, **response}, ensure_ascii=True, allow_nan=False, separators=(',', ':')) + '\n')
    stream.flush()


if __name__ == '__main__':
    main()
