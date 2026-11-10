from pathlib import Path
import importlib.util

path = Path(__file__).resolve().parents[1] / "src" / "solution.py"
spec = importlib.util.spec_from_file_location("solution", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

assert feasible({"cpu": 4, "memory": 8}, [{"cpu": 1, "memory": 3}, {"cpu": 3, "memory": 5}]) is True
assert feasible({"cpu": 4}, [{"cpu": 3}]) is True
assert feasible({"cpu": 4}, [{"cpu": 2}, {"cpu": 3}]) is False
assert feasible({"cpu": 4}, [{"memory": 1}]) is False
assert feasible({}, []) is True
assert feasible({"cpu": 0}, [{"cpu": 0}]) is True
assert feasible({"cpu": 4}, []) is True
for resources, requests in [(None, []), ({"cpu": 4}, [None]), ({"cpu": 4}, [{"cpu": "1"}])]:
    try:
        feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

print("All allocation checks passed.")
