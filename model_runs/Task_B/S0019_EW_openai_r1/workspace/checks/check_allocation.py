import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

assert feasible({"cpu": 4, "ram": 8}, [{"cpu": 1, "ram": 3}, {"cpu": 3, "ram": 5}])
assert feasible({"cpu": 4}, [{"cpu": 2}])
assert not feasible({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}])
assert not feasible({"cpu": 4}, [{"gpu": 1}])
assert feasible({}, [])
assert feasible({"cpu": 0}, [{"cpu": 0}])
assert feasible({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}])
assert feasible({"cpu": 4}, [])
try:
    feasible({"cpu": 4}, [None])
except ValueError:
    pass
else:
    raise AssertionError("Non-dictionary requests must still raise ValueError")

print("All allocation checks passed.")
