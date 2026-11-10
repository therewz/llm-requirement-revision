from copy import deepcopy
from itertools import product
from runpy import run_path

feasible = run_path('src/solution.py')['is_allocation_feasible']

cases = [
    ({}, [], True),
    ({'cpu': 0}, [], True),
    ({'cpu': 3}, [], True),
    ({'cpu': 3}, [{'cpu': 3}], True),
    ({'cpu': 3, 'ram': 4}, [{'cpu': 1, 'ram': 4}, {'cpu': 2}], True),
    ({'cpu': 3}, [{'cpu': 2}, {'cpu': 2}], False),
    ({'cpu': 3, 'ram': 100}, [{'cpu': 4}], False),
    ({}, [{'cpu': 0}], False),
    ({'cpu': -1}, [], False),
    ({'cpu': 3}, [{'cpu': -1}], False),
    ({'cpu': 1.5}, [{'cpu': 0.5}, {'cpu': 1.0}], True),
    ({'cpu': 10 ** 500}, [{'cpu': 10 ** 500}], True),
]
for bad in (float('inf'), float('-inf'), float('nan')):
    cases.append(({'cpu': bad}, [], False))
    cases.append(({'cpu': 3}, [{'cpu': bad}], False))

for resources, requests, expected in cases:
    before = deepcopy((resources, requests))
    assert feasible(resources, requests) is expected, (resources, requests, expected)
    # NaNs are not equal to their copies; check mutation on the other cases.
    if all(value == value for value in resources.values()) and all(
        value == value for request in requests for value in request.values()
    ):
        assert (resources, requests) == before

for a, b, x, y in product(range(5), repeat=4):
    resources = {'a': a, 'b': b}
    requests = [{'a': x}, {'a': y, 'b': x}]
    assert feasible(resources, requests) is (x + y <= a and x <= b)

for resources, requests in [([], []), ({'a': '1'}, []), ({'a': 1}, [1]), ({'a': 1}, [{'a': '1'}])]:
    try:
        feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError('Expected ValueError')

print('All allocation checks passed, including 625 exhaustive small cases.')
