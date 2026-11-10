import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

assert feasible({"cpu": 4}, [{"cpu": 2}, {"cpu": 2}]) is True
assert feasible({"cpu": 4}, [{"cpu": 3}]) is True
assert feasible({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}]) is False
assert feasible({"cpu": 4}, [{"memory": 1}]) is False
assert feasible({"cpu": 4, "memory": 8}, [{"cpu": 4, "memory": 8}]) is True
assert feasible({"cpu": 0.5}, [{"cpu": 0.5}]) is True
assert feasible({}, []) is True
assert feasible({"cpu": 0}, [{"cpu": 0}]) is True
assert feasible({"cpu": 4}, []) is True
print("All 9 allocation checks passed.")
