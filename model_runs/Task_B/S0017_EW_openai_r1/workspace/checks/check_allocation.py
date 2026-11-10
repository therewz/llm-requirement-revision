import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

assert feasible({"cpu": 4}, [{"cpu": 4}]) is True
assert feasible({"cpu": 4, "ram": 8}, [{"cpu": 1, "ram": 3}, {"cpu": 3, "ram": 5}]) is True
assert feasible({}, []) is True
assert feasible({"cpu": 0}, [{"cpu": 0}]) is True
assert feasible({"cpu": 4}, [{"cpu": 2}]) is True
assert feasible({"cpu": 4}, []) is True
assert feasible({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}]) is False
assert feasible({"cpu": 4}, [{"ram": 1}]) is False

for resources, requests in [([], []), ({}, [1]), ({"cpu": 4}, [{"cpu": -1}]), ({"cpu": 4}, [{"cpu": "invalid"}])]:
    try:
        feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected existing input validation to be preserved")

print("All allocation feasibility checks passed.")
