import runpy

is_allocation_feasible = runpy.run_path('src/solution.py')['is_allocation_feasible']

cases = [
    ({'cpu': 4}, [{'cpu': 4}], True),
    ({'cpu': 4, 'memory': 8}, [{'cpu': 1, 'memory': 3}, {'cpu': 3, 'memory': 5}], True),
    ({}, [], True),
    ({}, [{}], True),
    ({'cpu': 0}, [], True),
    ({'cpu': 4}, [{'cpu': 2}], True),
    ({'cpu': 4}, [{'cpu': 3}, {'cpu': 2}], False),
    ({'cpu': 4}, [{'memory': 1}], False),
    ({}, [{'cpu': 1}], False),
    ({'cpu': 4}, [{'cpu': 0}, {'cpu': -1}, {'cpu': 4}], True),
]

for resources, requests, expected in cases:
    actual = is_allocation_feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)

try:
    is_allocation_feasible({'cpu': 4}, [None])
except ValueError:
    pass
else:
    raise AssertionError('Non-dictionary requests must still raise ValueError')

print('All allocation checks passed.')
