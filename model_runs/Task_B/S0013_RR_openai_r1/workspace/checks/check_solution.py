import importlib.util
from collections import UserDict

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({'cpu': 4}, [{'cpu': 3}], True),
    ({'cpu': 4}, [{'cpu': 4}], False),
    ({'cpu': 4, 'ram': 10}, [{'cpu': 5}], False),
    ({'cpu': 4, 'ram': 10}, [{'cpu': 4}], True),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 2}], False),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 1}], True),
    ({'cpu': 1.5}, [{'cpu': 1.25}], True),
    ({'cpu': 1}, [{'ram': 1}], False),
    ({}, [], False),
    ({'cpu': 0}, [], False),
    ({'cpu': 1}, [], True),
    ({'cpu': 2}, [UserDict({'cpu': 1})], True),
]
for resources, requests, expected in cases:
    actual = feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)
print(f'Passed {len(cases)} checks.')
