import copy
import importlib.util
import itertools
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({"cpu": 10}, [{"cpu": 3}, {"cpu": 4}], True),
    ({"cpu": 10}, [], True),
    ({"cpu": 10}, [{"cpu": 6}, {"cpu": 5}], False),
    ({"cpu": 10}, [{"cpu": 11}], False),
    ({"cpu": 10}, [{"cpu": 6}, {"cpu": 4}], True),
    ({"cpu": 10, "ram": 8}, [{"cpu": 10, "ram": 8}], True),
    ({"cpu": 10, "ram": 8}, [{"cpu": 2, "ram": 9}], False),
    ({"cpu": 0}, [], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({}, [], True),
    ({}, [{}], True),
    ({"cpu": 10**400}, [{"cpu": 10**400}], True),
]
for resources, requests, expected in cases:
    before = copy.deepcopy((resources, requests))
    assert feasible(resources, requests) is expected
    assert (resources, requests) == before
    for ordering in itertools.permutations(requests):
        assert feasible(resources, list(ordering)) is expected

for resources, requests in [
    ({"cpu": -1}, []),
    ({"cpu": float("inf")}, []),
    ({"cpu": 1}, [{"cpu": -1}]),
    ({"cpu": 1}, [{"cpu": float("nan")}]),
    ({"cpu": 1}, [{"ram": 1}]),
]:
    try:
        feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid input rejection")

print("All allocation checks passed.")
