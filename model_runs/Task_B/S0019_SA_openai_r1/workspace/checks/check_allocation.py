import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 2}], True),
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 3}], False),
    ({"cpu": 4}, [{"cpu": 1}], True),
    ({"cpu": 4, "ram": 8}, [{"cpu": 4, "ram": 8}], True),
    ({"cpu": 4, "ram": 8}, [{"cpu": 5}], False),
    ({"cpu": 4}, [{"ram": 1}], False),
    ({}, [], True),
    ({"cpu": 0}, [], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], True),
]
for resources, requests, expected in cases:
    assert feasible(resources, requests) is expected, (resources, requests)
print(f"Passed {len(cases)} allocation checks.")
