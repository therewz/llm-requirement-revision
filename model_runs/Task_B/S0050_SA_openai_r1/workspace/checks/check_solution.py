"""Focused validation and allocation checks for S0050."""

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
    ({}, [], True),
    ({"gpu": 0}, [{"gpu": 0}], True),
    ({"gpu": 2}, [], True),
    ({"gpu": 2}, [{"gpu": 1}, {"gpu": 1}], True),
    ({"gpu": 2}, [{"gpu": 2}, {"gpu": 1}], False),
    ({"gpu": 2}, [{"cpu": 0}], False),
    ({"gpu": 2}, [{"gpu": -1}], False),
    ({"gpu": -1}, [], False),
    ({"gpu": 70}, [{"gpu": 70}], True),
    ({"gpu": 71}, [], False),
    ({"gpu": 2, "cpu": 3}, [{"gpu": 1, "cpu": 2}, {"cpu": 1}], True),
    ({"gpu": 2, "cpu": 3}, [{"gpu": 1, "cpu": 4}], False),
]
for invalid in (0.0, 1.0, 1.5, float("nan"), float("inf"), True, False, "1", None):
    cases.append(({"gpu": invalid}, [], False))
    cases.append(({"gpu": 2}, [{"gpu": invalid}], False))

for resources, requests, expected in cases:
    actual = feasible(resources, requests)
    assert type(actual) is bool and actual is expected, (resources, requests, actual)

for capacity, first, second in product(range(5), repeat=3):
    resources = {"gpu": capacity}
    requests = [{"gpu": first}, {"gpu": second}]
    before = deepcopy((resources, requests))
    assert feasible(resources, requests) is (first + second <= capacity)
    assert (resources, requests) == before

print(f"Passed {len(cases)} targeted cases and 125 allocation/immutability checks.")
