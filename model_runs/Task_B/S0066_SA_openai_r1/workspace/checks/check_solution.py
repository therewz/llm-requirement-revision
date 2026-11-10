import importlib.util
from copy import deepcopy
from itertools import product

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({'cpu': 5}, [{'cpu': 5}], True),
    ({'cpu': 5}, [{'cpu': 2}, {'cpu': 3}], True),
    ({'cpu': 5}, [{'cpu': 3}, {'cpu': 3}], False),
    ({'cpu': 5}, [{'cpu': 4}], True),
    ({'cpu': 0}, [], True),
    ({'cpu': 0}, [{'cpu': 0}], True),
    ({}, [], True),
    ({}, [{}], True),
    ({}, [{'cpu': 1}], False),
    ({}, [{'cpu': 0}], True),
    ({'cpu': 2, 'ram': 4}, [{'cpu': 2, 'ram': 4}], True),
    ({'cpu': 2, 'ram': 4}, [{'cpu': 3}], False),
    ({'cpu': 10**400}, [{'cpu': 10**400}], True),
    ({'cpu': 1.5}, [{'cpu': 0.5}, {'cpu': 1.0}], True),
]
for resources, requests, expected in cases:
    before = deepcopy((resources, requests))
    actual = feasible(resources, requests)
    assert actual is expected, (resources, requests, actual, expected)
    assert (resources, requests) == before

for capacity, first, second in product(range(5), repeat=3):
    assert feasible({'r': capacity}, [{'r': first}, {'r': second}]) is (
        first + second <= capacity
    )

print('All allocation checks passed.')
