import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 2}], True),
    ({"cpu": 4, "memory": 8}, [{"cpu": 4, "memory": 8}], True),
    ({}, [], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({"cpu": 4}, [{"cpu": 3}], True),
    ({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}], False),
    ({"cpu": 4}, [{"memory": 1}], False),
]
for resources, requests, expected in cases:
    assert feasible(resources, requests) is expected, (resources, requests)

for resources, requests in [
    ({"cpu": -1}, []),
    ({"cpu": 4}, [{"cpu": -1}]),
    ({"cpu": 4}, [{"cpu": "1"}]),
    ({"cpu": 4}, [1]),
]:
    try:
        feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError((resources, requests))

print("All allocation checks passed.")
