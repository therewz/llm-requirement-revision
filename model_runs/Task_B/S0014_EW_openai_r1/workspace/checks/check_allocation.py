import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({"cpu": 4}, [{"cpu": 4}], True),
    ({"cpu": 4, "ram": 8}, [{"cpu": 1, "ram": 3}, {"cpu": 3, "ram": 5}], True),
    ({"cpu": 4}, [{"cpu": 3}], True),
    ({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}], False),
    ({"cpu": 4}, [{"gpu": 1}], False),
    ({}, [], True),
    ({}, [{}], True),
    ({}, [{"cpu": 1}], False),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({"cpu": 4}, [], True),
    ({"cpu": 4}, [None], False),
]
for resources, requests, expected in cases:
    actual = feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)

for resources, requests in [({"cpu": "4"}, []), ({"cpu": 4}, [{"cpu": "1"}])]:
    try:
        feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError("Input validation was not preserved")

print("All 13 checks passed.")
