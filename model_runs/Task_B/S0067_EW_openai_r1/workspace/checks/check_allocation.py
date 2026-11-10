import importlib.util
from copy import deepcopy

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
f = solution.is_allocation_feasible

cases = [
    ({'cpu': 5, 'ram': 2}, [{'cpu': 2}, {'cpu': 3, 'ram': 2}], True),
    ({'cpu': 5}, [{'cpu': 3}, {'cpu': 3}], False),
    ({'cpu': 5}, [{'cpu': 6}], False),
    ({'cpu': 0}, [{'cpu': 0}], True),
    ({'cpu': 0.5}, [{'cpu': 0.25}], True),
    ({'cpu': 0.5}, [{'cpu': 0.5}], True),
    ({'cpu': 0}, [], True),
    ({}, [], True),
    ({}, [{}], True),
]
for resources, requests, expected in cases:
    before = deepcopy((resources, requests))
    assert f(resources, requests) is expected
    assert (resources, requests) == before

for resources, requests, error in [
    ({'cpu': -1}, [], ValueError),
    ({'cpu': 1}, [{'cpu': -1}], ValueError),
    ({'cpu': 1}, [{'unknown': 0}], ValueError),
    ({}, [{'unknown': 0}], ValueError),
    ({'cpu': '1'}, [], TypeError),
    ({'cpu': 1}, [{'cpu': '1'}], TypeError),
]:
    before = deepcopy((resources, requests))
    try:
        f(resources, requests)
    except error:
        pass
    else:
        raise AssertionError('Expected validation error')
    assert (resources, requests) == before

print('All allocation checks passed.')
