import copy
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)

cases = [
    ({"cpu": 4}, [{"cpu": 4}], True),
    ({"cpu": 4, "ram": 8}, [{"cpu": 1, "ram": 3}, {"cpu": 3, "ram": 5}], True),
    ({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}], False),
    ({"cpu": 4}, [{"cpu": 1}], True),
    ({}, [], True),
    ({}, [{}], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({"cpu": 4}, [], True),
    ({}, [{"cpu": 1}], False),
    ({"cpu": 4}, [{"ram": 0}], False),
    ({"cpu": 4}, [{"CPU": 1}], False),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1}], True),
    ({"cpu": 1.5}, [{"cpu": 0.75}, {"cpu": 1}], False),
    ({"cpu": 10**1000}, [{"cpu": 10**1000}], True),
]
for resources, requests, expected in cases:
    before = copy.deepcopy((resources, requests))
    for _ in range(2):
        actual = solution.is_allocation_feasible(resources, requests)
        assert actual is expected, (resources, requests, actual, expected)
        assert (resources, requests) == before

for resources, requests in [({"cpu": -1}, []), ({"cpu": 1}, [{"cpu": -1}])]:
    try:
        solution.is_allocation_feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError("Negative values must be rejected")

print(f"Passed {len(cases)} feasibility cases, repeatability/immutability checks, and negative-value checks.")
