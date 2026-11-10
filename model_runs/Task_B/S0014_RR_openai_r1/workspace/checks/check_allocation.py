import importlib.util
from decimal import Decimal
from itertools import product

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({'cpu': 5}, [{'cpu': 4}], True),
    ({'cpu': 5}, [{'cpu': 5}], False),
    ({'cpu': 5}, [{'cpu': 6}], False),
    ({'cpu': 5}, [{'cpu': 3}, {'cpu': 3}], False),
    ({'cpu': 5}, [{'cpu': 2}, {'cpu': 2}], True),
    ({'cpu': 5}, [{'gpu': 1}], False),
    ({'cpu': 5}, [{'gpu': 0}], True),
    ({'cpu': 5, 'gpu': 1}, [{'cpu': 5}], True),
    ({'cpu': 5, 'gpu': 1}, [{'cpu': 5, 'gpu': 1}], False),
    ({}, [], False),
    ({}, [{'cpu': 1}], False),
    ({'cpu': 0}, [], False),
    ({'cpu': 1}, [], True),
    ({1: 2}, [{1: 1}], True),
    ({'cpu': Decimal('2.5')}, [{'cpu': Decimal('2')}], True),
]
for resources, requests, expected in cases:
    assert feasible(resources, requests) is expected, (resources, requests)

# Exhaustively compare small integer capacities and two aggregate requests.
count = 0
for a, b, a1, b1, a2, b2 in product(range(4), repeat=6):
    resources = {'a': a, 'b': b}
    requests = [{'a': a1, 'b': b1}, {'a': a2, 'b': b2}]
    expected = a1 + a2 <= a and b1 + b2 <= b and (a1 + a2 < a or b1 + b2 < b)
    assert feasible(resources, requests) is expected
    count += 1

assert solution.build_total_request([{'a': 2}, {'a': 3, 'b': 1}]) == {'a': 5, 'b': 1}
assert solution.confirm_type_of_key_and_value({'a': 1}, str, int)
print(f'Passed {len(cases)} edge cases and {count} exhaustive allocation cases.')
