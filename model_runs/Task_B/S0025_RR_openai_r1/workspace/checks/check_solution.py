import importlib.util
from decimal import Decimal
from fractions import Fraction
from itertools import product

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({'cpu': 4, 'ram': 8}, [{'cpu': 2}, {'cpu': 2, 'ram': 7}], True),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 4, 'ram': 8}], False),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 5}], False),
    ({'cpu': 4}, [{'cpu': 3}, {'cpu': 2}], False),
    ({'cpu': 4}, [], True),
    ({}, [], False),
    ({'cpu': 0}, [], False),
    ({'cpu': 4}, [{'ram': 1}], False),
    ({'cpu': 4}, [{'ram': 0}], True),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 4}], True),
    ({'cpu': 10**1000}, [{'cpu': 10**999}], True),
    ({'cpu': Decimal('1.5')}, [{'cpu': Decimal('0.5')}], True),
    ({'cpu': Fraction(3, 2)}, [{'cpu': Fraction(3, 2)}], False),
]
for resources, requests, expected in cases:
    before = (resources.copy(), [request.copy() for request in requests])
    assert feasible(resources, requests) is expected
    assert (resources, requests) == before

for ca, cb, a1, b1, a2, b2 in product(range(4), repeat=6):
    resources = {'a': ca, 'b': cb}
    requests = [{'a': a1, 'b': b1}, {'a': a2, 'b': b2}]
    da, db = a1 + a2, b1 + b2
    expected = da <= ca and db <= cb and (da < ca or db < cb)
    assert feasible(resources, requests) is expected

print('All allocation checks passed (13 cases and 4096 exhaustive combinations).')
