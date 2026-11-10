import itertools
import runpy
from copy import deepcopy

is_allocation_feasible = runpy.run_path('src/solution.py')['is_allocation_feasible']

cases = [
    ({'cpu': 10, 'ram': 32}, [{'cpu': 4, 'ram': 8}], True),
    ({'cpu': 10}, [{'cpu': 4}, {'cpu': 2}], True),
    ({'cpu': 10}, [{'cpu': 4}, {'cpu': 6}], False),
    ({'cpu': 10, 'ram': 32}, [{'cpu': 10, 'ram': 32}], False),
    ({'cpu': 10, 'ram': 32}, [{'cpu': 10, 'ram': 31}], True),
    ({'cpu': 10, 'ram': 32}, [{'cpu': 11}], False),
    ({'cpu': 10, 'ram': 0}, [{'cpu': 10}], False),
    ({'cpu': 10}, [], True),
    ({'cpu': 0}, [], False),
    ({}, [], False),
    ({'cpu': 10}, {'cpu': 4}, True),
    ({'cpu': 10}, [{'gpu': 0}], False),
    ({'cpu': -5}, [], False),
    ({'cpu': 10, 'ram': -1}, [{'cpu': 1}], False),
    ({'cpu': 10}, [{'cpu': -3}], False),
    ({'cpu': 10}, [{'cpu': 1}, {'cpu': -1}], False),
    (None, [], False),
    ([], [], False),
    ({'cpu': 10}, None, False),
    ({'cpu': 10}, 'cpu:4', False),
    ({'cpu': 10}, [None], False),
    ({'cpu': 10}, [[('cpu', 4)]], False),
    ({1: 10}, [], False),
    ({'cpu': 10}, [{1: 4}], False),
]
for invalid in ('4', None, 1.5, True, float('inf'), float('nan'), [], {}):
    cases.append(({'cpu': invalid}, [], False))
    cases.append(({'cpu': 10}, [{'cpu': invalid}], False))

for resources, requests, expected in cases:
    before = deepcopy((resources, requests))
    result = is_allocation_feasible(resources, requests)
    assert result is expected, (resources, requests, expected, result)
    # NaN is intentionally not equal to itself, so skip its equality check.
    if 'nan' not in repr((resources, requests)):
        assert (resources, requests) == before

vectors = list(itertools.product(range(4), repeat=2))
for capacity, first, second in itertools.product(vectors, repeat=3):
    resources = dict(zip(('cpu', 'ram'), capacity))
    requests = [dict(zip(('cpu', 'ram'), demand)) for demand in (first, second)]
    remaining = [c - a - b for c, a, b in zip(capacity, first, second)]
    expected = min(remaining) >= 0 and max(remaining) > 0
    assert is_allocation_feasible(resources, requests) is expected
    assert is_allocation_feasible(resources, requests[::-1]) is expected

print(f'Passed {len(cases)} targeted cases and {len(vectors) ** 3} exhaustive cases (both request orders).')
