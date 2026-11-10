import copy
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import is_allocation_feasible

cases = [
    ({'cpu': 10}, [{'cpu': 3}, {'cpu': 4}], True),
    ({'cpu': 10}, [], True),
    ({'cpu': 10}, [{'cpu': 6}, {'cpu': 5}], False),
    ({'cpu': 10}, [{'cpu': 11}], False),
    ({'cpu': 10}, [{'cpu': 10}], False),
    ({'cpu': 10, 'memory': 20}, [{'cpu': 11, 'memory': 1}], False),
    ({'cpu': 10, 'memory': 20}, [{'cpu': 10, 'memory': 19}], True),
    ({'cpu': 10, 'memory': 20}, [{'cpu': 10, 'memory': 20}], False),
    ({'cpu': 10, 'memory': 20}, [{'cpu': 10}], True),
    ({'cpu': 0}, [], False),
    ({'cpu': 0}, [{'cpu': 0}], False),
    ({}, [], False),
    ({}, [{}], False),
    ({'cpu': 10**1000}, [{'cpu': 10**1000 - 1}], True),
    ({'cpu': 10**1000}, [{'cpu': 10**1000}], False),
    ({'cpu': 10**1000}, [{'cpu': 10**1000 + 1}], False),
    ({'cpu': 1.5}, [{'cpu': 0.5}], True),
]
for resources, requests, expected in cases:
    before = copy.deepcopy((resources, requests))
    assert is_allocation_feasible(resources, requests) is expected
    assert (resources, requests) == before
    for order in itertools.permutations(requests):
        assert is_allocation_feasible(resources, list(order)) is expected

# Exhaustively check small two-resource integer allocations.
for cpu, memory in itertools.product(range(4), repeat=2):
    resources = {'cpu': cpu, 'memory': memory}
    for values in itertools.product(range(4), repeat=4):
        a, b, c, d = values
        requests = [{'cpu': a, 'memory': b}, {'cpu': c, 'memory': d}]
        expected = a + c <= cpu and b + d <= memory and (a + c < cpu or b + d < memory)
        assert is_allocation_feasible(resources, requests) is expected

print('All allocation checks passed.')
