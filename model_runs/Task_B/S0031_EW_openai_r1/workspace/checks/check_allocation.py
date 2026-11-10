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
assert feasible({"cpu": 0}, [{"cpu": 0}]) is True
assert feasible({"cpu": 0}, []) is True
assert feasible({"cpu": 4}, []) is True
assert feasible({"cpu": 4}, [{"cpu": 3}]) is True
assert feasible({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}]) is False
assert feasible({"cpu": 4, "ram": 100}, [{"cpu": 5}]) is False
assert feasible({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}]) is True

for resources, requests, expected_error in [
    ([], [], TypeError),
    ({"cpu": 1}, [{"unknown": 1}], ValueError),
    ({"cpu": 1}, [{"cpu": -1}], ValueError),
    ({"cpu": 1}, [{"cpu": "1"}], TypeError),
    ({"cpu": float("inf")}, [], ValueError),
]:
    try:
        feasible(resources, requests)
    except expected_error:
        pass
    else:
        raise AssertionError(f"Expected {expected_error.__name__}")

print("All allocation checks passed.")
