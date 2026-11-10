import copy
import importlib.util
from itertools import permutations
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({"cpu": 10}, [{"cpu": 2}, {"cpu": 3}], True),
    ({"cpu": 10}, [], True),
    ({"cpu": 10}, [{"cpu": 6}, {"cpu": 5}], False),
    ({"cpu": 10}, [{"cpu": 11}], False),
    ({"cpu": 10}, [{"cpu": 4}, {"cpu": 6}], True),
    ({"cpu": 10, "ram": 8}, [{"cpu": 3, "ram": 5}, {"cpu": 2, "ram": 4}], False),
    ({"cpu": 10, "ram": 8}, [{"cpu": 3, "ram": 5}, {"cpu": 7, "ram": 3}], True),
    ({}, [], True),
    ({}, [{}], True),
    ({"cpu": 0}, [], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({"cpu": 10, "ram": 8}, [{"ram": 8}], True),
    ({"cpu": 10**1000}, [{"cpu": 10**1000}], True),
    ({"cpu": 10**1000}, [{"cpu": 10**1000 + 1}], False),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], True),
]

for resources, requests, expected in cases:
    before = copy.deepcopy((resources, requests))
    assert feasible(resources, requests) is expected
    assert (resources, requests) == before
    for ordering in permutations(requests):
        assert feasible(resources, list(ordering)) is expected

print(f"Passed {len(cases)} cases, including order independence and no mutation.")
