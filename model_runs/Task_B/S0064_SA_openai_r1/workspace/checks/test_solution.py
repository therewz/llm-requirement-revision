import runpy
from collections import UserDict
from decimal import Decimal
from fractions import Fraction

is_allocation_feasible = runpy.run_path('src/solution.py')['is_allocation_feasible']

cases = [
    ({'cpu': 5}, [{'cpu': 2}, {'cpu': 3}], True),
    ({'cpu': 5}, [{'cpu': 2}, {'cpu': 4}], False),
    ({'cpu': 5, 'ram': 8}, [{'cpu': 3, 'ram': 8}, {'cpu': 2}], True),
    ({}, [], True),
    ({}, [{}], True),
    ({}, [{'cpu': 0}], False),
    ({'cpu': 0}, [{'cpu': 0}], True),
    ({'cpu': 1}, [], True),
    ({'cpu': -1}, [], False),
    ({'cpu': '1'}, [], False),
    ({'cpu': None}, [], False),
    ({'cpu': float('nan')}, [], False),
    ({'cpu': 2 + 1j}, [], False),
    ({'cpu': 10}, [{'cpu': -1}], False),
    ({'cpu': 10}, [{'cpu': '1'}], False),
    ({'cpu': 10}, [{'cpu': None}], False),
    ({'cpu': 10}, [{'cpu': float('nan')}], False),
    ({'cpu': 10}, [{'cpu': 1j}], False),
    ({'cpu': 10}, [{'missing': 1}], False),
    ({1: 2}, [{1: 2}], True),
    (UserDict({'cpu': 2}), [{'cpu': 2}], True),
    ({'cpu': True}, [{'cpu': True}], True),
    ({'cpu': float('inf')}, [{'cpu': float('inf')}], True),
    ({'cpu': 10**1000}, [{'cpu': 10**1000}], True),
    ({'cpu': Decimal('0.3')}, [{'cpu': Decimal('0.1')}, {'cpu': Decimal('0.2')}], True),
    ({'cpu': Fraction(1)}, [{'cpu': Fraction(1, 3)}, {'cpu': Fraction(2, 3)}], True),
    ({'cpu': Decimal('NaN')}, [], False),
    ({'cpu': 10}, [{'cpu': Decimal('NaN')}], False),
]
for resources, requests, expected in cases:
    assert is_allocation_feasible(resources, requests) is expected, (resources, requests)

for requests in [[None], [1], [[]], [{'cpu': 2}, None]]:
    try:
        is_allocation_feasible({'cpu': 1}, requests)
    except ValueError:
        pass
    else:
        raise AssertionError('Non-dictionary request did not raise ValueError')

# Cross-check aggregation over a small exhaustive set of integer requests.
for capacity in range(5):
    for first in range(5):
        for second in range(5):
            assert is_allocation_feasible({'r': capacity}, [{'r': first}, {'r': second}]) == (first + second <= capacity)

print('All feasibility checks passed.')
