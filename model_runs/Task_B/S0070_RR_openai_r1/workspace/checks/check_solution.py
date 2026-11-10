import importlib.util
from copy import deepcopy

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({'cpu': 4}, [{'cpu': 3}], True),
    ({'cpu': 4}, [{'cpu': 4}], False),
    ({'cpu': 4}, [{'cpu': 5}], False),
    ({'cpu': 4, 'memory': 8}, [{'cpu': 4}], True),
    ({'cpu': 4, 'memory': 8}, [{'cpu': 4, 'memory': 8}], False),
    ({'cpu': 4, 'memory': 8}, [{'cpu': 5}], False),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 2}], False),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 3}], False),
    ({'cpu': 4}, [], True),
    ({}, [], False),
    ({}, [{}], False),
    ({'cpu': 0}, [], False),
    ({'cpu': 0.75}, [{'cpu': 0.25}], True),
    ({'cpu': 10 ** 1000}, [{'cpu': 10 ** 1000 - 1}], True),
    ({'cpu': 10 ** 1000}, [{'cpu': 10 ** 1000}], False),
]
for resources, requests, expected in cases:
    original = deepcopy((resources, requests))
    result = feasible(resources, requests)
    assert result is expected
    assert (resources, requests) == original

for resources, requests, error in [
    ([], [], TypeError),
    ({'cpu': 1}, {}, TypeError),
    ({'cpu': 1}, [1], TypeError),
    ({'cpu': 1}, [{'other': 1}], ValueError),
    ({'cpu': -1}, [], ValueError),
    ({'cpu': 1}, [{'cpu': -1}], ValueError),
    ({'cpu': True}, [], TypeError),
    ({'cpu': float('nan')}, [], ValueError),
    ({'cpu': float('inf')}, [], ValueError),
]:
    try:
        feasible(resources, requests)
    except error:
        pass
    else:
        raise AssertionError('Expected validation error')

print('All 24 checks passed.')
