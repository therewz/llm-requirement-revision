import importlib.util
from collections import UserDict
from copy import deepcopy
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
    ({'cpu': 5}, [{'cpu': 2}, {'cpu': 2}], True),
    ({'cpu': 5}, [{'cpu': 3}, {'cpu': 3}], False),
    ({'cpu': 5}, [{'cpu': 5}], False),
    ({'cpu': 5, 'ram': 1}, [{'cpu': 5}], True),
    ({'cpu': 5, 'ram': 0}, [{'cpu': 5}], False),
    ({'cpu': 5}, [], True),
    ({'cpu': 0}, [], False),
    ({}, [], False),
    ({}, [{}], False),
    ({}, [{'cpu': 0}], False),
    ({'cpu': 5}, [{'CPU': 1}], False),
    ({'cpu': 5}, [{'missing': 0}], False),
    ({'cpu': -1}, [], False),
    ({'cpu': 5}, [{'cpu': -1}], False),
    ({'cpu': None}, [], False),
    ({'cpu': float('nan')}, [], False),
    ({'cpu': 5}, [{'cpu': float('nan')}], False),
    ({'cpu': 1.5}, [{'cpu': 0.5}, {'cpu': 0.25}], True),
    ({'cpu': Decimal('1.5')}, [{'cpu': Decimal('0.2')}], True),
    ({'cpu': Fraction(3, 2)}, [{'cpu': Fraction(1, 2)}], True),
    ({'cpu': 10 ** 1000}, [{'cpu': 1}], True),
    ({'cpu': float('inf')}, [{'cpu': 1}], True),
    (UserDict({'cpu': 5}), [UserDict({'cpu': 1})], True),
]
for resources, requests, expected in cases:
    original = deepcopy((resources, requests))
    actual = feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)
    # NaN is not equal to itself; other cases can use equality for immutability.
    if not any(isinstance(v, float) and v != v for v in resources.values()) and not any(
        isinstance(v, float) and v != v for req in requests for v in req.values()
    ):
        assert (resources, requests) == original

count = 0
for a, b, x, y, z, w in product(range(4), repeat=6):
    resources = {'a': a, 'b': b}
    requests = [{'a': x, 'b': y}, {'a': z, 'b': w}]
    expected = x + z <= a and y + w <= b and (x + z < a or y + w < b)
    assert feasible(resources, requests) is expected
    assert feasible(resources, requests[::-1]) is expected
    count += 1
print(f'Passed {len(cases)} focused cases and {count} exhaustive cases.')
