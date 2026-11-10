import itertools
import math
import runpy

allocate = runpy.run_path('src/solution.py')['is_allocation_feasible']

cases = [
    ({'resourceA': 10}, [{'resourceA': 6}], True),
    ({'resourceA': 10}, [{'resourceA': 6}, {'resourceB': 8}], False),
    ({'resourceA': 10}, [{'resourceB': 5}], False),
    ({'resourceA': 10}, [{'resourceA': -1}], False),
    ({}, [{'resourceA': 0}], False),
    ({'resourceA': 10}, [{'resourceA': 10}], False),
    ({'resourceA': 10, 'resourceB': 2}, [{'resourceA': 10}], True),
    ({'resourceA': 10, 'resourceB': 0}, [{'resourceA': 10}], False),
    ({'resourceA': 10}, [{'resourceA': 6}, {'resourceA': 5}], False),
    ({'resourceA': 10, 'resourceB': 2}, [{'resourceA': 10, 'resourceB': 2}], False),
    ({'resourceA': 10}, [{'resourceA': 0}], True),
    ({'resourceA': 0}, [{'resourceA': 0}], False),
    ({'resourceA': 10}, [], True),
    ({}, [], False),
    ({'resourceA': 10}, [{}], True),
    ({'resourceA': 10}, [('resourceA', 1)], False),
    ({'resourceA': 10}, [{'resourceA': '1'}], False),
    ({'resourceA': 10}, [{'resourceA': math.nan}], False),
    ({'resourceA': math.nan}, [], False),
    (None, [], False),
    ({'resourceA': 10}, None, False),
    ({'resourceA': math.inf}, [{'resourceA': 10}], True),
    ({'resourceA': math.inf}, [{'resourceA': math.inf}], False),
    ({'resourceA': 10}, [{'resourceA': math.inf}], False),
    ({'resourceA': math.inf, 'resourceB': 1}, [{'resourceA': math.inf}], True),
    ({'resourceA': 10**1000}, [{'resourceA': 1.5}], True),
    ({'resourceA': 10**1000}, [{'resourceA': 10**1000}], False),
    ({'resourceA': math.inf}, [{'resourceA': 1e308}, {'resourceA': 1e308}], True),
]
for resources, requests, expected in cases:
    result = allocate(resources, requests)
    assert result is expected, (resources, requests, expected, result)

for requests in itertools.permutations([{'a': 1e16}, {'a': 1}, {'a': 1}]):
    assert allocate({'a': 1e16, 'b': 1}, list(requests)) is False
for requests in itertools.permutations([{'a': 0.1}, {'a': 0.2}, {'a': 0.3}]):
    assert allocate({'a': 1}, list(requests)) is True

print(f'{len(cases)} cases and 12 request-order checks passed')
