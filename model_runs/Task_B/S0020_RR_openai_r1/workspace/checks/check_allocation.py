import sys
sys.path.insert(0, '.')

from src.solution import is_allocation_feasible

cases = [
    ({'cpu': 4}, [{'cpu': 3}], True),
    ({'cpu': 4}, [{'cpu': 4}], False),
    ({'cpu': 4}, [{'cpu': 5}], False),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 4, 'ram': 7}], True),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 4, 'ram': 8}], False),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 2}], False),
    ({'cpu': 4}, [{'cpu': 1}, {'cpu': 2}], True),
    ({'cpu': 4}, [{'gpu': 1}], False),
    ({'cpu': 4}, [], True),
    ({'cpu': 0}, [], False),
    ({}, [], False),
    ({'cpu': 1.5}, [{'cpu': 1.25}], True),
]

for resources, requests, expected in cases:
    actual = is_allocation_feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)

print(f'Passed {len(cases)} allocation checks.')
