import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

assert feasible({"cpu": 4, "ram": 8}, [{"cpu": 1, "ram": 3}, {"cpu": 3, "ram": 5}])
assert feasible({"cpu": 4}, [{"cpu": 3}])
assert not feasible({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}])
assert not feasible({"cpu": 4}, [{"ram": 1}])
assert feasible({}, [])
assert feasible({"cpu": 0}, [])
assert feasible({"cpu": 4}, [])
resources = {"cpu": 4}
requests = [{"cpu": 4}]
assert feasible(resources, requests)
assert resources == {"cpu": 4}
assert requests == [{"cpu": 4}]
try:
    feasible({"cpu": 4}, [None])
except ValueError:
    pass
else:
    raise AssertionError("Expected existing request validation")
print("All allocation checks passed.")
