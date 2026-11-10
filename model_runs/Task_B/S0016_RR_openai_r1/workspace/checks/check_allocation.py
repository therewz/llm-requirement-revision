import runpy

is_allocation_feasible = runpy.run_path('src/solution.py')['is_allocation_feasible']

cases = [
    ({'cpu': 4, 'memory': 8}, [{'cpu': 2, 'memory': 8}], True),
    ({'cpu': 4, 'memory': 8}, [{'cpu': 2, 'memory': 4}, {'cpu': 2, 'memory': 4}], False),
    ({'cpu': 4}, [{'cpu': 5}], False),
    ({'cpu': 4}, [{'memory': 1}], False),
    ({'cpu': 1.5}, [{'cpu': 1.25}], True),
    ({'cpu': 1.5}, [{'cpu': 1.5}], False),
    ({'cpu': 4}, [], True),
    ({'cpu': 0}, [], False),
    ({}, [], False),
    ({'cpu': 4, 'memory': 1}, [{'cpu': 4}], True),
]

for resources, requests, expected in cases:
    original_resources = resources.copy()
    original_requests = [request.copy() for request in requests]
    result = is_allocation_feasible(resources, requests)
    assert result is expected, (resources, requests, expected, result)
    assert resources == original_resources
    assert requests == original_requests

print(f'Passed {len(cases)} allocation checks; inputs remain unchanged.')
