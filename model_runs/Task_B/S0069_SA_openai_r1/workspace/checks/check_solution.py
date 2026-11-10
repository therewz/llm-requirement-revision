import copy
import itertools
import random
import runpy

is_feasible = runpy.run_path('src/solution.py')['is_allocation_feasible']

cases = [
    ({}, [], True),
    ({}, [{}], False),
    ({}, [{'missing': 0}], False),
    ({'a': 0}, [], True),
    ({'a': 0}, [{'a': 0}], True),
    ({'a': 1}, [{}], False),
    ({'a': 2}, [{'a': 2}], True),
    ({'a': 2}, [{'a': 1}, {'a': 2}], False),
    ({'a': 2, 'b': 2}, [{'a': 2, 'b': 2}] * 2, True),
    ({'a': 2, 'b': 2}, [{'a': 2, 'b': 2}] * 3, False),
    ({'a': 1}, [{'missing': 1, 'a': 1}], True),
    ({'a': 1}, [{'missing': 1}], False),
    ({'a': 1}, [{'a': -1}], False),
    ({'a': 1, 'b': 1}, [{'a': -1, 'b': 1}], True),
    ({'a': -1}, [], False),
    ({'a': 10**1000}, [{'a': 10**1000}], True),
    ({'a': float('inf')}, [{'a': float('inf')}] * 2, True),
    ({'a': 2500}, [{'a': 1}] * 2500, True),
]
for resources, requests, expected in cases:
    before = copy.deepcopy((resources, requests))
    actual = is_feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)
    assert (resources, requests) == before


def brute_force(resources, requests):
    if any(capacity < 0 for capacity in resources.values()):
        return False
    for selection in itertools.product(*(list(r.items()) for r in requests)):
        used = dict.fromkeys(resources, 0)
        for resource, amount in selection:
            if resource not in resources or amount < 0:
                break
            used[resource] += amount
        else:
            if all(used[r] <= resources[r] for r in resources):
                return True
    return False


rng = random.Random(69)
for _ in range(2000):
    resources = {r: rng.randrange(5) for r in 'abc'}
    requests = [
        {r: rng.randrange(-1, 6) for r in 'abcd' if rng.randrange(2)}
        for _ in range(rng.randrange(7))
    ]
    expected = brute_force(resources, requests)
    actual = is_feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)

print('Passed 18 edge cases and 2000 randomized brute-force comparisons.')
