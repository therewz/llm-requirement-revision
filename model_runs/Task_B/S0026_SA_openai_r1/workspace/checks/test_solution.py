import importlib.util
from copy import deepcopy
from itertools import permutations
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py'
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({'cpu': 10}, [{'cpu': 3}, {'cpu': 4}], True),
    ({'cpu': 10}, [{'cpu': 11}], False),
    ({'cpu': 10}, [{'cpu': 6}, {'cpu': 5}], False),
    ({'cpu': 10}, [{'other': 20}], True),
    ({'cpu': 10}, [], True),
    ({'cpu': 10}, [{'cpu': 6}, {'cpu': 4}], True),
    ({'cpu': 10, 'ram': 8}, [{'cpu': 10, 'ram': 3}, {'ram': 5}], True),
    ({'cpu': 10, 'ram': 8}, [{'cpu': 9, 'ram': 9}], False),
    ({'cpu': 0}, [{}], True),
    ({}, [], True),
    ({}, [{'other': 1}], True),
    ({'cpu': 1}, [{'CPU': 100}, {'cpu': 1}], True),
    ({'cpu': 1}, [{'other': 1}, {'cpu': 2}], False),
    ({'cpu': 10 ** 1000}, [{'cpu': 10 ** 1000}], True),
]
for resources, requests, expected in cases:
    before = deepcopy((resources, requests))
    assert feasible(resources, requests) is expected
    assert (resources, requests) == before
    for reordered in permutations(requests):
        assert feasible(resources, list(reordered)) is expected
print(f'Passed {len(cases)} cases, including order and input preservation checks.')
