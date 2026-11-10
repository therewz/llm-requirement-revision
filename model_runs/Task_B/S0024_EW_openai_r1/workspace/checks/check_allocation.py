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
assert feasible({"cpu": 4}, [{"cpu": 2}]) is True
assert feasible({}, []) is True
assert feasible({"cpu": 0}, [{"cpu": 0}]) is True
assert feasible({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}]) is False
assert feasible({"cpu": 4}, [{"ram": 1}]) is False
resources = {"cpu": 4}
requests = [{"cpu": 4}]
assert feasible(resources, requests) is True
assert resources == {"cpu": 4}
assert requests == [{"cpu": 4}]
for invalid in [[[]], [{"cpu": -1}], [{"cpu": "1"}]]:
    try:
        feasible({"cpu": 4}, invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected existing validation to reject invalid input")
print("All checks passed.")
