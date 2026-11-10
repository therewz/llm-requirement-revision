import importlib.util
from copy import deepcopy
from itertools import product
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({"cpu": 4}, [{"cpu": 4}], True),
    ({"cpu": 4}, [{"cpu": 1}, {"cpu": 3}], True),
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 3}], False),
    ({"cpu": 4}, [{"cpu": 1}], True),
    ({"cpu": 4}, [], True),
    ({}, [], True),
    ({}, [{}], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({"cpu": 0}, [{"cpu": 1}], False),
    ({"cpu": 4}, [{"memory": 1}], False),
    ({"cpu": 4, "memory": 8}, [{"cpu": 2, "memory": 8}, {"cpu": 2}], True),
    ({"cpu": 4, "memory": 8}, [{"cpu": 2, "memory": 9}], False),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], True),
]
for resources, requests, expected in cases:
    original = deepcopy((resources, requests))
    assert feasible(resources, requests) is expected, (resources, requests)
    assert (resources, requests) == original

for capacity_a, capacity_b, a1, b1, a2, b2 in product(range(4), repeat=6):
    resources = {"a": capacity_a, "b": capacity_b}
    requests = [{"a": a1, "b": b1}, {"a": a2, "b": b2}]
    expected = a1 + a2 <= capacity_a and b1 + b2 <= capacity_b
    assert feasible(resources, requests) is expected

print("Passed 13 targeted cases and 4096 exhaustive small-capacity cases.")
