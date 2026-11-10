import runpy

is_allocation_feasible = runpy.run_path('src/solution.py')['is_allocation_feasible']

cases = [
    ({'cpu': 4}, [{'cpu': 3}], True),
    ({'cpu': 4}, [{'cpu': 4}], False),
    ({'cpu': 4}, [{'cpu': 5}], False),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 2}], False),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 1}], True),
    ({'cpu': 4, 'memory': 8}, [{'cpu': 4, 'memory': 7}], True),
    ({'cpu': 4, 'memory': 8}, [{'cpu': 4, 'memory': 8}], False),
    ({'cpu': 4, 'memory': 8}, [{'cpu': 5}], False),
    ({'cpu': 4, 'memory': 8}, [{'cpu': 4}], True),
    ({'cpu': 4}, [{'gpu': 1}], False),
    ({'cpu': 4}, [], True),
    ({'cpu': 0}, [], False),
    ({}, [], False),
    ({'cpu': 1.5}, [{'cpu': 0.5}, {'cpu': 0.5}], True),
]

for resources, requests, expected in cases:
    result = is_allocation_feasible(resources, requests)
    assert result is expected, (resources, requests, expected, result)

print(f'Passed {len(cases)} feasibility checks.')
