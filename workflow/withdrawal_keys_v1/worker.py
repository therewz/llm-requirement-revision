"""Trusted worker copied into the restricted scratch workspace; never imported by host."""
import contextlib
import copy
import importlib.util
import json
import os
import signal
import sys


class CallTimeout(Exception):
    pass


def alarm(*_):
    raise CallTimeout('per-call limit')


def canon(value, depth=0):
    if type(value) is bool:
        return {'type': 'bool', 'value': value}
    if type(value) is list and all(type(x) is str for x in value):
        return {'type': 'list_str', 'value': value}
    if type(value) is tuple and depth < 2:
        return {'type': 'tuple', 'items': [canon(x, depth+1) for x in value[:8]],
                'length': len(value), 'repr': repr(value)[:500]}
    return {'type': type(value).__name__, 'repr': repr(value)[:500]}


def main():
    cases = json.load(open('cases.json'))['cases']
    result = {'import_error': None, 'cases': {}}
    signal.signal(signal.SIGALRM, alarm)
    with open(os.devnull, 'w') as sink:
        try:
            signal.setitimer(signal.ITIMER_REAL, 5)
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                spec = importlib.util.spec_from_file_location('solution', 'solution.py')
                module = importlib.util.module_from_spec(spec)
                sys.modules['solution'] = module
                spec.loader.exec_module(module)
        except BaseException as exc:
            result['import_error'] = {'type': type(exc).__name__, 'message': str(exc)[:500]}
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
        if result['import_error'] is None:
            for case in cases:
                cid = case['case_id']
                try:
                    signal.setitimer(signal.ITIMER_REAL, 2)
                    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                        value = getattr(module, case['function'])(*copy.deepcopy(case['args']),
                                    **copy.deepcopy(case.get('kwargs', {})))
                        observation = {'kind': 'ret', **canon(value)}
                    result['cases'][cid] = observation
                except CallTimeout:
                    result['cases'][cid] = {'kind': 'timeout'}
                except BaseException as exc:
                    result['cases'][cid] = {'kind': 'exc', 'exc': type(exc).__name__, 'msg': str(exc)[:300]}
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
    with open('out.json', 'w') as f:
        json.dump(result, f, allow_nan=False)


if __name__ == '__main__':
    main()
