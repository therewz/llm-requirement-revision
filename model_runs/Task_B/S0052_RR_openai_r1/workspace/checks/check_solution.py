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
    ({'cpu': 5}, [{'cpu': 2}, {'cpu': 2}], True),
    ({'cpu': 5}, [{'cpu': 2}, {'cpu': 3}], False),
    ({'cpu': 5}, [{'cpu': 3}, {'cpu': 3}], False),
    ({'cpu': 5, 'ram': 1}, [{'cpu': 5}], True),
    ({'cpu': 5, 'ram': 1}, [{'cpu': 6}], False),
    ({'cpu': 0}, [], False),
    ({'cpu': 1}, [], True),
    ({}, [], False),
    ({}, [{'unknown': 0}], False),
    ({'cpu': -1, 'ram': 10}, [], False),
    ({'cpu': 5}, [{'cpu': -1}], False),
    ({'cpu': float('inf')}, [], False),
    ({'cpu': float('nan')}, [], False),
    ({'cpu': 5}, [{'cpu': float('nan')}], False),
    ({'cpu': 5}, [{'cpu': float('inf')}], False),
    ({'cpu': 1.5}, [{'cpu': 1.25}], True),
    ({'cpu': 10**1000}, [{'cpu': 1}], True),
    ([], [], False),
    ([0], [0], False),
    ([1], [], False),
    ([1], [0], True),
    ([1], [1], False),
    ([1, 2], [2, 0], False),
    ([1, 2], [1, 1], True),
    ([-1, 2], [0, 0], False),
    ([1, 2], [-1, 0], False),
    ([float('inf')], [1], False),
]
for resources, requests, expected in cases:
    before = deepcopy((resources, requests))
    assert feasible(resources, requests) is expected, (resources, requests, expected)
    # NaNs do not compare equal, so compare representations for this check.
    assert repr((resources, requests)) == repr(before)

for capacities in product(range(4), repeat=2):
    for first in product(range(4), repeat=2):
        for second in product(range(4), repeat=2):
            demands = [a + b for a, b in zip(first, second)]
            expected = all(d <= c for c, d in zip(capacities, demands)) and any(
                d < c for c, d in zip(capacities, demands)
            )
            assert feasible(list(capacities), demands) is expected
            assert feasible(dict(enumerate(capacities)), [dict(enumerate(first)), dict(enumerate(second))]) is expected

for resources, requests in [({'cpu': '5'}, []), ({'cpu': 5}, [{'cpu': '1'}]), ([5], ['1'])]:
    try:
        feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError('Non-numeric amounts must be rejected')

print('All allocation checks passed (including exhaustive small allocations).')
