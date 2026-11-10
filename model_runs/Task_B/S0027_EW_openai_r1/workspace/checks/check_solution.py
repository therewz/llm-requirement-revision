import importlib.util
from copy import deepcopy
from itertools import permutations

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({'cpu': 10, 'ram': 32}, [{'cpu': 4, 'ram': 8}], True),
    ({'cpu': 10}, [{'cpu': 4}, {'cpu': 2}], True),
    ({'cpu': 10}, [{'cpu': 4}, {'cpu': 6}], True),
    ({'cpu': 10, 'ram': 32}, [{'cpu': 4, 'ram': 8}, {'cpu': 6, 'ram': 24}], True),
    ({'cpu': 10}, [{'cpu': 4}, {'cpu': 7}], False),
    ({'cpu': 16, 'ram': 16}, [{'cpu': 3, 'ram': 10}, {'cpu': 10, 'ram': 10}], False),
    ({'cpu': 10}, [{'cpu': -3}], False),
    ({'cpu': -5}, [], False),
    ({'cpu': 10, 'ram': -1}, [{'cpu': 4}], False),
    ({}, [], True),
    ({'cpu': 0}, [{'cpu': 0}], True),
    ({'cpu': 10}, [{'ram': 1}], False),
    ({'cpu': 10}, ['wrong format'], False),
    ({'cpu': 10}, {'cpu': 4}, False),
    (None, [], False),
    ({'cpu': 10}, None, False),
    ({'cpu': '10'}, [], False),
    ({'cpu': 10}, [{'cpu': '4'}], False),
    ({1: 10}, [], False),
    ({'cpu': 10}, [{1: 4}], False),
    ({'cpu': 1.5}, [{'cpu': 0.5}, {'cpu': 1.0}], True),
    ({'cpu': float('nan')}, [], False),
    ({'cpu': 10}, [{'cpu': float('nan')}], False),
    ({'cpu': 10**1000}, [{'cpu': 10**1000}], True),
]
for resources, requests, expected in cases:
    assert feasible(resources, requests) is expected, (resources, requests, expected)

resources = {'cpu': 10, 'ram': 32}
requests = [{'cpu': 4}, {'cpu': 6, 'ram': 8}, {'ram': 24}]
original = deepcopy((resources, requests))
for ordered in permutations(requests):
    assert feasible(resources, list(ordered)) is True
assert (resources, requests) == original
print(f'Passed {len(cases)} cases, request-order checks, and input immutability check.')
