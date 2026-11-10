import sys
sys.path.insert(0, 'src')
from solution import is_allocation_feasible

cases = [
    ({'cpu': 4, 'ram': 8}, [{'cpu': 4, 'ram': 7}], True),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 4, 'ram': 8}], False),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 5}], False),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 2}], False),
    ({'cpu': 4}, [{'cpu': 1}, {'cpu': 2}], True),
    ({'cpu': 4}, [], True),
    ({}, [], False),
    ({'cpu': 0}, [], False),
    ({'cpu': 4, 'ram': 1}, [{'cpu': 4}], True),
    ({'cpu': 4}, [{'gpu': 1}], False),
    ({'cpu': 1.5}, [{'cpu': 0.5}], True),
    ({'cpu': 1.5}, [{'cpu': 1.5}], False),
    ({'cpu': 2**53, 'ram': 1}, [{'cpu': 2**53 + 1}], False),
    ({'cpu': 2**53 + 1}, [{'cpu': 2**53}], True),
    ({'cpu': 10**400}, [{'cpu': 10**400 - 1}], True),
]
for resources, requests, expected in cases:
    actual = is_allocation_feasible(resources, requests)
    assert actual == expected, (resources, requests, expected, actual)
print(f'Passed {len(cases)} allocation checks.')
