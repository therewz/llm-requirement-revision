import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({"cpu": 4}, [{"cpu": 3}], True),
    ({"cpu": 4}, [{"cpu": 4}], False),
    ({"cpu": 4}, [{"cpu": 5}], False),
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 2}], False),
    ({"cpu": 4, "ram": 2}, [{"cpu": 4, "ram": 1}], True),
    ({"cpu": 4, "ram": 2}, [{"cpu": 4, "ram": 2}], False),
    ({"cpu": 4, "ram": 2}, [{"cpu": 5}], False),
    ({"cpu": 1.5}, [{"cpu": 1.25}], True),
    ({"cpu": 4}, [], True),
    ({"cpu": 0}, [], False),
    ({}, [], False),
    ({}, [{}], False),
    ({"cpu": 10 ** 400}, [{"cpu": 10 ** 400 - 1}], True),
    ({"cpu": 10 ** 400}, [{"cpu": 10 ** 400}], False),
]
for resources, requests, expected in cases:
    original_resources = resources.copy()
    original_requests = [request.copy() for request in requests]
    assert feasible(resources, requests) is expected
    assert resources == original_resources
    assert requests == original_requests

invalid_cases = [
    ([], [], TypeError),
    ({"cpu": 1}, {}, TypeError),
    ({"cpu": 1}, [1], TypeError),
    ({"cpu": "one"}, [], TypeError),
    ({"cpu": 1}, [{"cpu": "one"}], TypeError),
    ({"cpu": 1}, [{"gpu": 1}], ValueError),
    ({"cpu": -1}, [], ValueError),
    ({"cpu": float("nan")}, [], ValueError),
    ({"cpu": float("inf")}, [], ValueError),
    ({"cpu": 1}, [{"cpu": -1}], ValueError),
    ({"cpu": 1}, [{"cpu": float("nan")}], ValueError),
    ({"cpu": 1}, [{"cpu": float("inf")}], ValueError),
]
for resources, requests, error in invalid_cases:
    try:
        feasible(resources, requests)
    except error:
        pass
    else:
        raise AssertionError(f"Expected {error.__name__}")

print(f"Passed {len(cases) + len(invalid_cases)} checks")
