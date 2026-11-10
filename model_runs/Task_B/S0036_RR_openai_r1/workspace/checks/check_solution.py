import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py'
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({'cpu': 10}, [{'cpu': 4}, {'cpu': 6}], False),
    ({'cpu': 10, 'memory': 20}, [{'cpu': 4}, {'cpu': 6}], True),
    ({'cpu': 8, 'memory': 20}, [{'memory': 21}], False),
    ({'cpu': 10}, [{'gpu': 0}], False),
    ({'cpu': 10}, [], True),
    ({'cpu': 10}, [{'cpu': 10}], False),
    ({'cpu': 10, 'memory': 20}, [{'cpu': 10, 'memory': 20}], False),
    ({'cpu': 10, 'memory': 20}, [{'cpu': 10, 'memory': 19.75}], True),
    ({'cpu': 0.5}, [], True),
    ({'cpu': 0.5}, [{'cpu': 0.25}], True),
    ({'cpu': 0}, [], False),
    ({'cpu': 0}, [{'cpu': 0}], False),
    ({'cpu': 0, 'memory': 0.5}, [{'cpu': 0}], True),
    ({}, [], False),
    ({'cpu': 10}, [0], False),
    ({'cpu': 10}, [None], False),
    ({'cpu': 10}, [{'cpu': 6}, {'cpu': 5}], False),
    ({'cpu': 10}, [{}], True),
    ({'cpu': -1}, [], False),
    ({'cpu': 10}, [{'cpu': -1}], False),
    ({'cpu': 10}, [{'cpu': '1'}], False),
    ({'cpu': '10'}, [], False),
    ({'cpu': 10}, [{'cpu': {}}], False),
    ({1: 10}, [], False),
    ({'cpu': 10}, [{1: 1}], False),
    (None, [], False),
    ([], [], False),
    ({'cpu': 10}, None, False),
    ({'cpu': 10}, {}, False),
    ({'cpu': True}, [], False),
    ({'cpu': 10}, [{'cpu': True}], False),
    ({'cpu': float('nan')}, [], False),
    ({'cpu': float('inf')}, [], False),
    ({'cpu': 10}, [{'cpu': float('nan')}], False),
    ({'cpu': 10}, [{'cpu': float('inf')}], False),
    ({'cpu': 10**1000}, [{'cpu': 1}], True),
]
for resources, requests, expected in cases:
    result = feasible(resources, requests)
    assert result is expected, (resources, requests, expected, result)

resources = {'cpu': 10, 'memory': 20}
requests = [{'cpu': 10}]
assert feasible(resources, requests) is True
assert resources == {'cpu': 10, 'memory': 20}
assert requests == [{'cpu': 10}]
print(f'Passed {len(cases)} allocation checks and input immutability checks.')
