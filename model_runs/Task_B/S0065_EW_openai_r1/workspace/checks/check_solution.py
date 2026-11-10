import importlib.util
from copy import deepcopy
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({"cpu": 10}, [{"cpu": 10}], True),
    ({"cpu": 10}, [{"cpu": 2}, {"cpu": 8}], True),
    ({"cpu": 10, "mem": 18}, [{"cpu": 2}, {"mem": 8}, {"cpu": 8, "mem": 10}], True),
    ({"cpu": 10}, [{"cpu": 11}], False),
    ({"cpu": 10}, [{"cpu": 6}, {"cpu": 5}], False),
    ({"cpu": 10, "mem": 18}, [{"cpu": 11}], False),
    ({"cpu": 10}, [{"cpu": 2}], True),
    ({"cpu": 0}, [], True),
    ({}, [], True),
    ({}, [{}], True),
    ({"cpu": 10}, [], True),
    ({"cpu": 10 ** 400}, [{"cpu": 10 ** 400}], True),
]
for resources, requests, expected in cases:
    original = deepcopy((resources, requests))
    assert feasible(resources, requests) is expected
    assert (resources, requests) == original

invalid = [
    ([], [], TypeError),
    ({"cpu": 10}, {}, TypeError),
    ({"cpu": 10}, [1], TypeError),
    ({"cpu": 10}, [{"mem": 1}], ValueError),
    ({"cpu": 10}, [{1: 1}], TypeError),
    ({"cpu": 10}, [{"cpu": 0}], ValueError),
    ({"cpu": 10}, [{"cpu": -1}], ValueError),
    ({"cpu": 10}, [{"cpu": 1.0}], TypeError),
    ({"cpu": 10}, [{"cpu": True}], TypeError),
    ({"cpu": 10}, [{"cpu": "1"}], TypeError),
]
for resources, requests, exception in invalid:
    try:
        feasible(resources, requests)
    except exception:
        pass
    else:
        raise AssertionError(f"Expected {exception.__name__} for {resources}, {requests}")

print(f"Passed {len(cases)} allocation cases and {len(invalid)} validation checks.")
