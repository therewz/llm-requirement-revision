import runpy

is_feasible = runpy.run_path('src/solution.py')['is_allocation_feasible']

cases = [
    ({'cpu': 10}, [{'cpu': 4}, {'cpu': 6}], True),
    ({'memory': 20, 'cpu': 8}, [{'memory': 21}], False),
    ({'cpu': 10}, [{'gpu': 0}], False),
    ({'cpu': 10}, [], True),
    ({'cpu': 10, 'memory': 20}, [{'cpu': 10, 'memory': 20}], True),
    ({'cpu': 10}, [0], False),
    ({'cpu': 10}, [{'cpu': 6}, {'cpu': 5}], False),
    ({'cpu': 0.5}, [{'cpu': 0.25}], True),
    ({'cpu': 0}, [{'cpu': 0}], True),
    ({'cpu': 0}, [], True),
    ({}, [], True),
    ({}, [{}], True),
    ({}, [{'cpu': 0}], False),
    ({'cpu': -1}, [], False),
    ({'cpu': 1}, [{'cpu': -1}], False),
    ({'cpu': float('nan')}, [], False),
    ({'cpu': 1}, [{'cpu': float('inf')}], False),
    ({'cpu': True}, [], False),
    ({'cpu': 1}, [{'cpu': True}], False),
    ({'cpu': '10'}, [], False),
    ({'cpu': 10}, [{'cpu': '1'}], False),
    ({'cpu': 10}, [{'cpu': {}}], False),
    ({1: 10}, [], False),
    ({'cpu': 10}, [{1: 1}], False),
    (None, [], False),
    ({'cpu': 10}, None, False),
    ({'cpu': 10}, {'cpu': 1}, False),
    ({'cpu': 10**1000}, [{'cpu': 10**1000}], True),
]
for resources, requests, expected in cases:
    assert is_feasible(resources, requests) is expected, (resources, requests, expected)

resources = {'cpu': 2}
requests = [{'cpu': 1}, {'cpu': 1}]
assert is_feasible(resources, requests)
assert resources == {'cpu': 2} and requests == [{'cpu': 1}, {'cpu': 1}]
print(f'Passed {len(cases) + 1} checks.')
