import importlib.util

spec = importlib.util.spec_from_file_location("solution", "src/solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({"cpu": 4}, [{"cpu": 4}], True),
    ({"cpu": 4, "ram": 8}, [{"cpu": 1, "ram": 3}, {"cpu": 3, "ram": 5}], True),
    ({"cpu": 4}, [{"cpu": 2}], True),
    ({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}], False),
    ({"cpu": 4, "ram": 8}, [{"cpu": 5}], False),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({"cpu": 0}, [], True),
    ({"cpu": 4}, [], True),
    ({}, [], True),
    ({}, [{}], True),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1}], True),
]
for resources, requests, expected in cases:
    original_resources = resources.copy()
    original_requests = [request.copy() for request in requests]
    assert feasible(resources, requests) is expected, (resources, requests, expected)
    assert resources == original_resources
    assert requests == original_requests

print(f"Passed {len(cases)} allocation checks.")
