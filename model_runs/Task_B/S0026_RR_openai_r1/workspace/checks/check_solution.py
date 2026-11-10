import importlib.util
from copy import deepcopy
from itertools import product

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({'cpu': 5}, [{'cpu': 4}], True),
    ({'cpu': 5}, [{'cpu': 5}], False),
    ({'cpu': 5}, [{'cpu': 6}], False),
    ({'cpu': 5}, [{'cpu': 3}, {'cpu': 3}], False),
    ({'cpu': 5}, [{'missing': 100}], True),
    ({'cpu': 5}, [{'CPU': 100}], True),
    ({'cpu': 5}, [], True),
    ({'cpu': 5}, [{}], True),
    ({'cpu': 5, 'ram': 3}, [{'cpu': 5, 'ram': 2}], True),
    ({'cpu': 5, 'ram': 3}, [{'cpu': 5, 'ram': 3}], False),
    ({'cpu': 5, 'ram': 3}, [{'cpu': 6}], False),
    ({'cpu': 0}, [], False),
    ({}, [], False),
    ({}, [{'missing': 1}], False),
    ({'cpu': 10**1000}, [{'cpu': 1}], True),
]
for resources, requests, expected in cases:
    original = deepcopy((resources, requests))
    assert feasible(resources, requests) is expected, (resources, requests, expected)
    assert feasible(resources, requests[::-1]) is expected
    assert (resources, requests) == original

for cap_a, cap_b, a1, a2, b1, b2 in product(range(4), repeat=6):
    resources = {'a': cap_a, 'b': cap_b}
    requests = [{'a': a1, 'b': b1}, {'a': a2, 'b': b2, 'unknown': 10}]
    left_a = cap_a - a1 - a2
    left_b = cap_b - b1 - b2
    expected = left_a >= 0 and left_b >= 0 and (left_a > 0 or left_b > 0)
    assert feasible(resources, requests) is expected
print('All 15 targeted cases and 4096 exhaustive cases passed.')
