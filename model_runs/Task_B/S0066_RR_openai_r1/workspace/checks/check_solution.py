import importlib.util
from decimal import Decimal
from fractions import Fraction
from itertools import product
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py'
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({'cpu': 5}, [{'cpu': 4}], True),
    ({'cpu': 5}, [{'cpu': 5}], False),
    ({'cpu': 5}, [{'cpu': 6}], False),
    ({'cpu': 5}, [{'cpu': 2}, {'cpu': 3}], False),
    ({'cpu': 5}, [{'cpu': 2}, {'cpu': 2}], True),
    ({'cpu': 5, 'ram': 2}, [{'cpu': 5}], True),
    ({'cpu': 5, 'ram': 2}, [{'cpu': 6}], False),
    ({'cpu': 0}, [], False),
    ({'cpu': 1}, [], True),
    ({}, [], False),
    ({}, [{}], False),
    ({}, [{'cpu': 1}], False),
    ({'cpu': 1}, [{'ram': 1}], False),
    ({'cpu': 1}, [{'ram': 0}], True),
    ({1: 2}, [{1: 1}], True),
    ({'cpu': 10 ** 1000}, [{'cpu': 1}], True),
    ({'cpu': Decimal('1.5')}, [{'cpu': Decimal('1.25')}], True),
    ({'cpu': Fraction(1, 2)}, [{'cpu': Fraction(1, 3)}], True),
]
for resources, requests, expected in cases:
    original_resources = resources.copy()
    original_requests = [request.copy() for request in requests]
    assert feasible(resources, requests) is expected, (resources, requests)
    assert resources == original_resources
    assert requests == original_requests

for a, b, a1, b1, a2, b2 in product(range(4), repeat=6):
    expected = a1 + a2 <= a and b1 + b2 <= b and (a1 + a2 < a or b1 + b2 < b)
    assert feasible({'a': a, 'b': b}, [{'a': a1, 'b': b1}, {'a': a2, 'b': b2}]) is expected

print('All 18 targeted checks and 4096 exhaustive allocation checks passed.')
