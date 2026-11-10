import copy
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({"cpu": 5}, [{"cpu": 4}], True),
    ({"cpu": 5}, [{"cpu": 5}], False),
    ({"cpu": 5}, [{"cpu": 3}, {"cpu": 3}], False),
    ({"cpu": 5, "ram": 10}, [{"cpu": 5, "ram": 9}], True),
    ({"cpu": 5, "ram": 10}, [{"cpu": 6}], False),
    ({"cpu": 5}, [{"gpu": 0}], False),
    ({"cpu": 5}, [], True),
    ({"cpu": 0}, [], False),
    ({}, [], False),
    ({}, [{}], False),
    ({}, [{"cpu": 1}], False),
    ({"cpu": 0, "ram": 1}, [{"cpu": 0}], True),
    ({"cpu": 1.5}, [{"cpu": 1.25}], True),
    ({"cpu": 10 ** 400}, [{"cpu": 1}], True),
    ({1: 5}, [{1: 4}], True),
]
for resources, requests, expected in cases:
    before = copy.deepcopy((resources, requests))
    assert feasible(resources, requests) is expected, (resources, requests)
    assert (resources, requests) == before

for requests in ([None], [1], [[]], [{"missing": 1}, None], [{"cpu": 100}, "bad"]):
    try:
        feasible({"cpu": 5}, requests)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Expected ValueError for {requests!r}")

print("All allocation checks passed.")
