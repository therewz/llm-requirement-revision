import importlib.util
from collections import UserDict
from decimal import Decimal
from fractions import Fraction

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({'cpu': 4, 'ram': 8}, [{'cpu': 1, 'ram': 3}, {'cpu': 3, 'ram': 5}], True),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 3}], False),
    ({'cpu': 4}, [{'cpu': 2}], True),
    ({}, [], True),
    ({}, [{}], True),
    ({}, [{'cpu': 0}], False),
    ({'cpu': 0}, [{'cpu': 0}], True),
    ({'cpu': -1}, [], False),
    ({'cpu': '4'}, [], False),
    ({'cpu': 4}, [{'cpu': -1}], False),
    ({'cpu': 4}, [{'cpu': '1'}], False),
    ({'cpu': 4}, [{'gpu': 0}], False),
    ({'cpu': float('nan')}, [], False),
    ({'cpu': 4}, [{'cpu': float('nan')}], False),
    ({'cpu': 4}, [{'cpu': 1j}], False),
    ({'cpu': 1j}, [], False),
    ({'cpu': float('inf')}, [{'cpu': float('inf')}], True),
    ({1: 2}, [{1: 2}], True),
    (UserDict({'cpu': 2}), [{'cpu': 2}], True),
    ({'cpu': 10**1000}, [{'cpu': 10**1000}], True),
    ({'cpu': Decimal('1')}, [{'cpu': Decimal('0.4')}, {'cpu': Decimal('0.6')}], True),
    ({'cpu': Fraction(1)}, [{'cpu': Fraction(1, 3)}, {'cpu': Fraction(2, 3)}], True),
]
for resources, requests, expected in cases:
    assert feasible(resources, requests) is expected, (resources, requests)

for resources, requests in [({'cpu': 1}, [None]), ({'cpu': 1}, [{'cpu': 2}, []]), ({'cpu': -1}, [2])]:
    try:
        feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError('Non-dictionary request must raise ValueError')

resources = {'cpu': 2}
requests = [{'cpu': 1}, {'cpu': 1}]
assert feasible(resources, requests)
assert resources == {'cpu': 2}
assert requests == [{'cpu': 1}, {'cpu': 1}]
print(f'Passed {len(cases) + 4} allocation checks.')
