from src.solution import is_allocation_feasible

cases = [
    ({"cpu": 4}, [{"cpu": 3}], True),
    ({"cpu": 4}, [{"cpu": 4}], False),
    ({"cpu": 4}, [{"cpu": 5}], False),
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 2}], False),
    ({"cpu": 4}, [{"cpu": 1}, {"cpu": 2}], True),
    ({"cpu": 4, "memory": 8}, [{"cpu": 4, "memory": 7}], True),
    ({"cpu": 4, "memory": 8}, [{"cpu": 4, "memory": 8}], False),
    ({"cpu": 4, "memory": 8}, [{"cpu": 5}], False),
    ({"cpu": 4}, [{"gpu": 1}], False),
    ({"cpu": 4}, [], True),
    ({"cpu": 0}, [], False),
    ({}, [], False),
    ({"cpu": 1.5}, [{"cpu": 1.25}], True),
]

for resources, requests, expected in cases:
    original_resources = resources.copy()
    original_requests = [request.copy() for request in requests]
    actual = is_allocation_feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)
    assert resources == original_resources
    assert requests == original_requests

print(f"Passed {len(cases)} allocation checks; inputs were not mutated.")
