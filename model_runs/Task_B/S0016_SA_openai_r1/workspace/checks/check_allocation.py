import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

assert feasible({"cpu": 4, "memory": 8}, [{"cpu": 1, "memory": 3}, {"cpu": 3, "memory": 5}])
assert feasible({"cpu": 4}, [{"cpu": 2}])
assert not feasible({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}])
assert not feasible({"cpu": 4}, [{"memory": 1}])
assert feasible({}, [])
assert feasible({"cpu": 0}, [])
assert feasible({"cpu": 0}, [{"cpu": 0}])
assert feasible({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}])
resources = {"cpu": 4}
requests = [{"cpu": 4}]
assert feasible(resources, requests)
assert resources == {"cpu": 4}
assert requests == [{"cpu": 4}]
print("All allocation checks passed.")
