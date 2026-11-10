import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
f = solution.is_allocation_feasible

assert f({"cpu": 4}, [{"cpu": 1}, {"cpu": 3}]) is True
assert f({"cpu": 4, "memory": 8}, [{"cpu": 4, "memory": 8}]) is True
assert f({"cpu": 4}, [{"cpu": 2}]) is True
assert f({"cpu": 4}, [{"cpu": 5}]) is False
assert f({"cpu": 4}, [{"memory": 1}]) is False
assert f({}, []) is True
assert f({}, [{}]) is True
assert f({"cpu": 0}, [{"cpu": 0}]) is True
assert f({"cpu": 0}, [{"cpu": None}]) is True
for resources, requests in [
    ({"cpu": -1}, []),
    ({"cpu": 4}, [{"cpu": -1}]),
    ({"cpu": float("inf")}, []),
    ({"cpu": 4}, [{"cpu": "invalid"}]),
]:
    try:
        f(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")
print("All allocation checks passed.")
