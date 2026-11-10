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
    ({}, [], True),
    ({}, [{}], True),
    ({"cpu": 0}, [], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({"cpu": 0.5}, [{"cpu": 0.5}], True),
    ({"cpu": 5}, [{"cpu": 2}, {"cpu": 3}], True),
    ({"cpu": 5}, [{"cpu": 2}, {"cpu": 4}], False),
    ({"cpu": 5}, [{"cpu": 6}], False),
    ({"cpu": 5, "ram": 0}, [{"cpu": 5}], True),
    ({"cpu": 4, "ram": 3}, [{"cpu": 2, "ram": 1}, {"cpu": 2, "ram": 2}], True),
    ({"cpu": 4, "ram": 3}, [{"cpu": 2, "ram": 1}, {"cpu": 2, "ram": 3}], False),
    ({"cpu": 10**400}, [{"cpu": 10**400}], True),
    ({"cpu": float("inf")}, [{"cpu": float("inf")}, {"cpu": 1}], True),
    ({"cpu": 3}, [{"cpu": float("inf")}], False),
]
for resources, requests, expected in cases:
    before = copy.deepcopy((resources, requests))
    assert feasible(resources, requests) is expected, (resources, requests)
    assert (resources, requests) == before

invalid = [
    ({"cpu": -1}, [], ValueError),
    ({"cpu": 1}, [{"cpu": -1}], ValueError),
    ({}, [{"missing": 0}], ValueError),
    ({"cpu": 1}, [{"missing": 1}], ValueError),
    ({"cpu": "1"}, [], TypeError),
    ({"cpu": 1}, [{"cpu": "1"}], TypeError),
    ({"cpu": True}, [], TypeError),
    ({"cpu": float("nan")}, [], ValueError),
    ({"cpu": 1}, [{"cpu": float("nan")}], ValueError),
    ({"cpu": float("-inf")}, [], ValueError),
]
for resources, requests, exception in invalid:
    try:
        feasible(resources, requests)
    except exception:
        pass
    else:
        raise AssertionError((resources, requests, exception))

print(f"Passed {len(cases)} feasibility/immutability cases and {len(invalid)} validation cases.")
