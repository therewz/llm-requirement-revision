import importlib.util
import itertools
import random
from copy import deepcopy

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({'a': 2}, [{'a': 1}], True),
    ({'a': 2}, [{'a': 2}], False),
    ({'a': 2, 'b': 1}, [{'a': 2}], True),
    ({'a': 2, 'b': 2}, [{'a': 2, 'b': 1}, {'a': 1}], True),
    ({'a': 2, 'b': 2}, [{'a': 2, 'b': 2}, {'a': 2, 'b': 2}], False),
    ({'a': 3, 'b': 2}, [{'a': 2, 'b': 2}, {'a': 2}], True),
    ({'a': 3}, [{'a': 2}, {'a': 2}], False),
    ({'a': 3}, [{'missing': 1}], False),
    ({'a': 3}, [{'missing': 1, 'a': 1}], True),
    ({'a': 3}, [{'a': -1}], False),
    ({'a': 3, 'b': 1}, [{'a': -1, 'b': 1}], True),
    ({'a': -1, 'b': 3}, [], False),
    ({}, [], False),
    ({}, [{}], False),
    ({'a': 0}, [], False),
    ({'a': 1}, [], True),
    ({'a': 1}, [{}], False),
    ({'a': 1}, [{'a': 0}], True),
    ({'a': 0, 'b': 1}, [{'a': 0}], True),
    ({'a': 0.5}, [{'a': 0.25}], True),
    ({'a': 0.5}, [{'a': 0.5}], False),
    ({1: 3}, [{1: 1}], True),
]
for resources, requests, expected in cases:
    original = deepcopy((resources, requests))
    actual = feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)
    assert (resources, requests) == original


def brute_force(resources, requests):
    if any(capacity < 0 for capacity in resources.values()):
        return False
    for choices in itertools.product(*(list(request.items()) for request in requests)):
        totals = dict.fromkeys(resources, 0)
        for resource, amount in choices:
            if resource not in resources or amount < 0:
                break
            totals[resource] += amount
        else:
            if (all(totals[r] <= capacity for r, capacity in resources.items())
                    and any(totals[r] < capacity for r, capacity in resources.items())):
                return True
    return False

rng = random.Random(69)
for _ in range(3000):
    resources = {r: rng.randrange(5) for r in ('a', 'b', 'c') if rng.random() < 0.8}
    requests = [
        {r: rng.randrange(-1, 6) for r in ('a', 'b', 'c', 'missing') if rng.random() < 0.5}
        for _ in range(rng.randrange(6))
    ]
    actual = feasible(resources, requests)
    expected = brute_force(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)

assert feasible({'a': 2501}, [{'a': 1}] * 2500) is True
assert feasible({'a': 2500}, [{'a': 1}] * 2500) is False
print('Passed 22 focused cases, 3000 exhaustive comparisons, and long-request checks.')
