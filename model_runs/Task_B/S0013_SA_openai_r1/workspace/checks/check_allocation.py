import runpy

is_allocation_feasible = runpy.run_path('src/solution.py')['is_allocation_feasible']

cases = [
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 2}], True),
    ({'cpu': 4}, [{'cpu': 2}], True),
    ({'cpu': 4}, [{'cpu': 3}, {'cpu': 2}], False),
    ({'cpu': 4, 'memory': 8}, [{'cpu': 4, 'memory': 8}], True),
    ({'cpu': 4, 'memory': 8}, [{'cpu': 5}], False),
    ({}, [], True),
    ({'cpu': 0}, [], True),
    ({}, [{'cpu': 1}], False),
    ({}, [{'cpu': 0}], True),
    ({'cpu': 1.5}, [{'cpu': 0.5}, {'cpu': 1.0}], True),
    ({'cpu': 1.5}, [{'cpu': 1.0}, {'cpu': 1.0}], False),
]
for resources, requests, expected in cases:
    actual = is_allocation_feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)
print(f'Passed {len(cases)} checks.')
