import importlib.util
from copy import deepcopy
from itertools import permutations
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)

cases = [
    ({"cpu": 4, "memory": 8}, [{"cpu": 1, "memory": 3}, {"cpu": 3, "memory": 5}], True),
    ({"cpu": 4}, [{"cpu": 5}], False),
    ({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}], False),
    ({"cpu": 4, "memory": 8}, [{"cpu": 4}], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({"cpu": 0}, [{"cpu": 1}], False),
    ({"cpu": 0}, [], True),
    ({}, [], True),
    ({}, [{}], True),
    ({"cpu": 4}, [{"unknown": 0}], False),
    ({"cpu": 4}, [], True),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], True),
]
for resources, requests, expected in cases:
    original = deepcopy((resources, requests))
    for ordering in permutations(requests):
        result = solution.is_allocation_feasible(resources, list(ordering))
        assert result is expected, (resources, requests, result)
    assert (resources, requests) == original

print("All allocation feasibility checks passed.")
