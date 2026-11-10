"""Focused checks for resource allocation feasibility."""

import importlib.util
from copy import deepcopy
from fractions import Fraction
from itertools import permutations, product
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({}, [], True),
    ({}, [{}], True),
    ({"cpu": 0}, [], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({"cpu": 0}, [{"cpu": 1}], False),
    ({"cpu": 4}, [{"cpu": 4}], True),
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 2}], True),
    ({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}], False),
    ({"cpu": 4}, [{"cpu": 5}], False),
    ({"cpu": 4}, [{"disk": 0}], False),
    ({}, [{"disk": 0}], False),
    ({"cpu": 4, "ram": 8}, [{"cpu": 4}, {"ram": 8}], True),
    ({"cpu": 4, "ram": 8}, [{"cpu": 4}], True),
    ({"cpu": 4, "ram": 8}, [{"cpu": 1}, {}, {"ram": 9}], False),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], True),
    ({"cpu": 1.5}, [{"cpu": 0.75}, {"cpu": 1.0}], False),
    ({"cpu": 10**400}, [{"cpu": 10**400}], True),
    ({"cpu": 10**400}, [{"cpu": 10**400}, {"cpu": 1}], False),
    ({"cpu": 1.0}, [{"cpu": float("inf")}], False),
]

for resources, requests, expected in cases:
    original = deepcopy((resources, requests))
    actual = feasible(resources, requests)
    assert actual is expected, (resources, requests, actual, expected)
    assert (resources, requests) == original

# Exhaustive small integer cases, including omitted resource requirements.
count = len(cases)
for cpu_cap, ram_cap in product(range(3), repeat=2):
    resources = {"cpu": cpu_cap, "ram": ram_cap}
    options = [{}, {"cpu": 0}, {"cpu": 1}, {"ram": 1}, {"cpu": 2, "ram": 2}]
    for requests in product(options, repeat=3):
        requests = list(requests)
        expected = all(
            sum(request.get(resource, 0) for request in requests) <= capacity
            for resource, capacity in resources.items()
        )
        assert feasible(resources, requests) is expected
        count += 1

# Float totals must not depend on request order or round away excess demand.
for capacity, amounts in [
    (1.0, [0.1, 0.2, 0.7]),
    (10**16, [1.0, 10**16, 1.0]),
    (2**53, [float(2**53), 1]),
    (1.5, [0.25, 0.5, 0.75]),
]:
    expected = sum(map(Fraction, amounts), Fraction(0)) <= capacity
    for ordering in permutations(amounts):
        assert feasible({"cpu": capacity}, [{"cpu": amount} for amount in ordering]) is expected
        count += 1

print(f"Passed {count} allocation checks.")
