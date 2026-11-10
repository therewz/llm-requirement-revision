import importlib.util
import itertools
import random
from copy import deepcopy

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({'cpu': 4}, [{'cpu': 4}], True),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 2}], True),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 3}], False),
    ({'a': 2, 'b': 2}, [{'a': 2, 'b': 2}] * 2, True),
    ({'a': 3, 'b': 3}, [{'a': 2, 'b': 2}] * 3, False),
    ({'a': 2}, [{'missing': 1}], False),
    ({'a': 2}, [{'missing': 1, 'a': 2}], True),
    ({'a': 0}, [{'a': 0}], True),
    ({'a': 2}, [{'a': -1}], False),
    ({'a': 2, 'b': 2}, [{'a': -1, 'b': 2}], True),
    ({}, [], True),
    ({'a': 0}, [], True),
    ({}, [{'a': 0}], False),
    ({'a': 2}, [{}], False),
    ({'a': 2000}, [{'a': 1}] * 2000, True),
    ({'a': 10**400}, [{'a': 10**400}], True),
]
for resources, requests, expected in cases:
    before = deepcopy((resources, requests))
    actual = feasible(resources, requests)
    assert actual is expected, (resources, requests, actual, expected)
    assert (resources, requests) == before


def brute_force(resources, requests):
    for allocation in itertools.product(*(list(req.items()) for req in requests)):
        used = dict.fromkeys(resources, 0)
        for resource, amount in allocation:
            if resource not in resources or amount < 0:
                break
            used[resource] += amount
        else:
            if all(used[key] <= resources[key] for key in resources):
                return True
    return False


rng = random.Random(69)
for _ in range(2000):
    resources = {key: rng.randrange(5) for key in 'abc' if rng.random() < .8}
    requests = [
        {key: rng.randrange(-1, 6) for key in 'abcd' if rng.random() < .5}
        for _ in range(rng.randrange(6))
    ]
    expected = brute_force(resources, requests)
    actual = feasible(resources, requests)
    assert actual is expected, (resources, requests, actual, expected)

print('All 16 targeted cases and 2000 exhaustive-comparison cases passed.')
