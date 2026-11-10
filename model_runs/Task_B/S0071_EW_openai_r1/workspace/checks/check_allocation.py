import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({"cpu": 4}, [{"cpu": 4}], True),
    ({"cpu": 4, "ram": 8}, [{"cpu": 1, "ram": 3}, {"cpu": 3, "ram": 5}], True),
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 3}], False),
    ({"cpu": 4, "ram": 100}, [{"cpu": 5}], False),
    ({"cpu": 4, "ram": 8}, [{"cpu": 1}, {"ram": 2}], True),
    ({"cpu": 4}, [{"gpu": 0}], False),
    ({"cpu": 4}, [], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({}, [], True),
    ({}, [{}], True),
    ({}, [{"cpu": 1}], False),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], True),
]
for resources, requests, expected in cases:
    original_resources = resources.copy()
    original_requests = [r.copy() for r in requests]
    assert feasible(resources, requests) is expected, (resources, requests)
    assert resources == original_resources
    assert requests == original_requests

for requests in ([None], [1], [[]], [{"cpu": 5}, None], [{"missing": 1}, "bad"]):
    try:
        feasible({"cpu": 4}, requests)
    except ValueError:
        pass
    else:
        raise AssertionError("Non-dictionary request must raise ValueError")

print("All 17 allocation checks passed.")
