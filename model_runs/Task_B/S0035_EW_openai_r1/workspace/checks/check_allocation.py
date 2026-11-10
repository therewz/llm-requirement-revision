import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({"chairs": 5}, [{"chairs": 5}], True),
    ({"chairs": 5}, [{"chairs": 2}, {"chairs": 3}], True),
    ({"chairs": 5}, [{"chairs": 3}, {"chairs": 3}], False),
    ({"chairs": 5, "rooms": 1}, [{"chairs": 5, "rooms": 1}], True),
    ({"chairs": 5}, [{"chairs": 4}], True),
    ({"chairs": 5}, [{"rooms": 1}], False),
    ({"chairs": 0}, [{"chairs": 0}], True),
    ({"chairs": 0}, [], True),
    ({}, [], True),
    ({}, [{}], True),
    ({}, [{"chairs": 0}], False),
    ({"chairs": 5}, [], True),
    ({"capacity": 1.5}, [{"capacity": 0.5}, {"capacity": 1}], True),
]
for resources, requests, expected in cases:
    original_resources = resources.copy()
    original_requests = [request.copy() for request in requests]
    assert feasible(resources, requests) is expected, (resources, requests, expected)
    assert resources == original_resources
    assert requests == original_requests

print(f"Passed {len(cases)} allocation checks.")
