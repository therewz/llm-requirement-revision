import importlib.util
from copy import deepcopy
from itertools import permutations
from pathlib import Path

spec = importlib.util.spec_from_file_location('solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({'cpu': 5}, [{'cpu': 2}], True),
    ({'cpu': 5}, [{'cpu': 5}], True),
    ({'cpu': 5}, [{'cpu': 6}], False),
    ({'cpu': 5}, [{'cpu': 3}, {'cpu': 3}], False),
    ({'cpu': 5}, [{'gpu': 100}], True),
    ({'cpu': 5}, [{'CPU': 100}], True),
    ({'cpu': 5}, [], True),
    ({'cpu': 0}, [], True),
    ({}, [], True),
    ({}, [{}], True),
    ({}, [{'gpu': 100}], True),
    ({'cpu': 0}, [{'cpu': 0}], True),
    ({'cpu': 5, 'ram': 8}, [{'cpu': 2, 'ram': 3}, {'cpu': 3, 'ram': 5}], True),
    ({'cpu': 5, 'ram': 8}, [{'cpu': 2, 'ram': 3}, {'cpu': 3, 'ram': 6}], False),
    ({'cpu': 5}, [{'gpu': 100, 'cpu': 6}], False),
    ({'cpu': 10**1000}, [{'cpu': 10**1000}], True),
    ({'cpu': 10**1000}, [{'cpu': 10**1000 + 1}], False),
    ({'cpu': 5}, [{}, {'cpu': 2}, {}], True),
]
for resources, requests, expected in cases:
    original = deepcopy((resources, requests))
    assert feasible(resources, requests) is expected, (resources, requests, expected)
    assert (resources, requests) == original
    for reordered in permutations(requests):
        assert feasible(resources, list(reordered)) is expected
print(f'Passed {len(cases)} cases, including order independence and input preservation.')
