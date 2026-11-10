import itertools
import runpy

is_feasible = runpy.run_path('src/solution.py')['is_allocation_feasible']

cases = [
    ({'cpu': 10}, [{'cpu': 4}, {'cpu': 6}], True),
    ({'memory': 20, 'cpu': 8}, [{'memory': 21}], False),
    ({'cpu': 10}, [{'gpu': 0}], False),
    ({'cpu': 0}, [], True),
    ({'cpu': 10, 'memory': 20}, [{'cpu': 10, 'memory': 20}], True),
    ({'cpu': 10}, [0], False),
    ({}, [], True),
    ({}, [{}], True),
    ({}, [{'cpu': 0}], False),
    ({'cpu': 0}, [{'cpu': 0}], True),
    ({'cpu': 0.5}, [{'cpu': 0.25}, {'cpu': 0.25}], True),
    ({'cpu': 10}, [{'cpu': 6}, {'cpu': 5}], False),
    ({'cpu': 10 ** 1000}, [{'cpu': 10 ** 1000}], True),
    (None, [], False),
    ([], [], False),
    ({'cpu': 1}, None, False),
    ({'cpu': 1}, {}, False),
    ({1: 10}, [], False),
    ({'cpu': -1}, [], False),
    ({'cpu': '10'}, [], False),
    ({'cpu': True}, [], False),
    ({'cpu': float('nan')}, [], False),
    ({'cpu': float('inf')}, [], False),
    ({'cpu': 1}, [{'cpu': -1}], False),
    ({'cpu': 1}, [{'cpu': '1'}], False),
    ({'cpu': 1}, [{'cpu': True}], False),
    ({'cpu': 1}, [{'cpu': {}}], False),
    ({'cpu': 1}, [{'cpu': float('nan')}], False),
    ({'cpu': 1}, [{'cpu': float('inf')}], False),
    ({'cpu': 1}, [{1: 0}], False),
]

for resources, requests, expected in cases:
    before = repr((resources, requests))
    actual = is_feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)
    assert repr((resources, requests)) == before

for capacity in range(5):
    for values in itertools.product(range(4), repeat=3):
        requests = [{'cpu': value} for value in values]
        assert is_feasible({'cpu': capacity}, requests) is (sum(values) <= capacity)

print(f'Passed {len(cases)} edge cases and 320 aggregate-capacity checks.')
