from copy import deepcopy
from itertools import permutations
from src.solution import is_allocation_feasible

cases = [
    ({"cpu": 4, "memory": 8}, [{"cpu": 2}, {"cpu": 1, "memory": 4}], True),
    ({"cpu": 4, "memory": 8}, [{"cpu": 3}, {"cpu": 2}], False),
    ({"cpu": 4, "memory": 8}, [{"cpu": 4, "memory": 8}], False),
    ({"cpu": 4, "memory": 8}, [{"cpu": 4, "memory": 7}], True),
    ({"cpu": 4, "memory": 8}, [{"cpu": 4}], True),
    ({"cpu": 4}, [{"unknown": 0}], False),
    ({"cpu": 0, "memory": 8}, [{"cpu": 1}], False),
    ({"cpu": 0, "memory": 8}, [{"cpu": 0}], True),
    ({"cpu": 0}, [], False),
    ({"cpu": 1}, [], True),
    ({}, [], False),
    ({}, [{}], False),
    ({"cpu": 1.0, "memory": 1}, [{"cpu": 0.8}, {"cpu": 0.2}], True),
    ({"cpu": 10**100}, [{"cpu": 10**100 - 1}], True),
]

for resources, requests, expected in cases:
    before = deepcopy((resources, requests))
    actual = is_allocation_feasible(resources, requests)
    assert type(actual) is bool
    assert actual is expected, (resources, requests, actual, expected)
    assert (resources, requests) == before
    for order in permutations(requests):
        assert is_allocation_feasible(resources, list(order)) is expected

for amounts in ([0.1, 0.2, 0.7], [0.8, 0.2, 0], [2**53, float(2**53), 1]):
    resources = {"cpu": sum(sorted(amounts)), "memory": 1}
    results = {
        is_allocation_feasible(resources, [{"cpu": amount} for amount in order])
        for order in permutations(amounts)
    }
    assert len(results) == 1, (amounts, results)

print("All allocation checks passed.")
