import importlib.util
from collections import UserDict
from decimal import Decimal
from fractions import Fraction

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({'cpu': 4}, [{'cpu': 2}], True),
    ({'cpu': 4}, [{'cpu': 4}], False),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 3}], False),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 4, 'ram': 7}], True),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 4, 'ram': 8}], False),
    ({'cpu': 4}, [{'gpu': 1}], False),
    ({'cpu': 4}, [{'gpu': 0}], True),
    ({}, [], False),
    ({'cpu': 0}, [], False),
    ({'cpu': 1}, [], True),
    ({'cpu': 0, 'ram': 1}, [{'cpu': 0, 'ram': 1}], False),
    ({'cpu': Fraction(1, 2)}, [{'cpu': Fraction(1, 4)}], True),
    ({'cpu': Decimal('0.3')}, [{'cpu': Decimal('0.1')}, {'cpu': Decimal('0.2')}], False),
    ({1: 3}, [{1: 2}], True),
    (UserDict({'cpu': 2}), (UserDict({'cpu': 1}),), True),
]
for resources, requests, expected in cases:
    actual = feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)
print(f'Passed {len(cases)} allocation checks.')
