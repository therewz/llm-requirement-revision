import copy
import runpy
from decimal import Decimal

is_feasible = runpy.run_path('src/solution.py')['is_allocation_feasible']

cases = [
    ({'cpu': 4, 'ram': 8}, [{'cpu': 2}, {'cpu': 2, 'ram': 8}], True),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 3}, {'cpu': 2}], False),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 5, 'ram': 1}], False),
    ({'cpu': 4}, [{'gpu': 0}], False),
    ({'cpu': 4}, [], True),
    ({'cpu': 0}, [{'cpu': 0}], True),
    ({}, [], True),
    ({}, [{}], True),
    ({}, [{'cpu': 1}], False),
    ({'cpu': 4}, [{'cpu': 5}, {'cpu': -1}], True),
    ({'cpu': 10**500}, [{'cpu': 10**500}], True),
    ({'cpu': Decimal('0.3')}, [{'cpu': Decimal('0.1')}, {'cpu': Decimal('0.2')}], True),
    ({'cpu': 1.5}, [{'cpu': 0.5}, {'cpu': 1.0}], True),
    ({1: 2}, [{1: 2}], True),
]
for resources, requests, expected in cases:
    original = copy.deepcopy((resources, requests))
    actual = is_feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)
    assert (resources, requests) == original

for malformed in (None, [], 1, 'cpu', ('cpu', 1)):
    for requests in ([malformed], [{'unknown': 1}, malformed], [{'cpu': 9}, malformed]):
        try:
            is_feasible({'cpu': 1}, requests)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Expected ValueError for {requests!r}')

print('Passed 14 feasibility cases and 15 malformed-request cases.')
