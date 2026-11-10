import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.solution import is_allocation_feasible


cases = [
    ({"cpu": 10}, [{"cpu": 4}, {"cpu": 6}], True),
    ({"cpu": 10}, [{"cpu": 3}], True),
    ({"cpu": 10}, [{"cpu": 11}], False),
    ({"cpu": 10, "ram": 8}, [{"cpu": 10, "ram": 8}], True),
    ({"cpu": 10, "ram": 8}, [{"cpu": 1, "ram": 9}], False),
    ({"cpu": 10}, [{"gpu": 1}], False),
    ({"cpu": 10}, [{"gpu": 0}], False),
    ({"cpu": 10}, [], True),
    ({}, [], True),
    ({}, [{}], True),
    ({}, [{"cpu": 1}], False),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({"cpu": 0}, [], True),
    ({"cpu": 1.5}, [{"cpu": 0.25}, {"cpu": 1.25}], True),
    ({"cpu": 1.0}, [{"cpu": 1.0000000001}], False),
    ({"cpu": 2**60}, [{"cpu": 2**60}, {"cpu": 1}], False),
    ({"cpu": 10**400}, [{"cpu": 10**400}], True),
]
for resources, requests, expected in cases:
    assert is_allocation_feasible(resources, requests) is expected

errors = [
    ({"cpu": -1}, [], ValueError),
    ({"cpu": 10}, [1], TypeError),
    ({"cpu": 10}, [{"cpu": -1}], ValueError),
    ({"cpu": 10}, [{"cpu": 11}, {"cpu": -1}], ValueError),
    ({"cpu": 10}, [{"gpu": 1}, 1], TypeError),
    ({"cpu": 10}, [{"gpu": -1}], ValueError),
    ({"cpu": float("inf")}, [], ValueError),
    ({"cpu": 10}, [{"cpu": float("nan")}], ValueError),
]
for resources, requests, error in errors:
    try:
        is_allocation_feasible(resources, requests)
    except error:
        pass
    else:
        raise AssertionError(f"Expected {error.__name__}")

rng = random.Random(30)
for _ in range(1000):
    resources = {key: rng.randrange(15) for key in ("cpu", "ram", "disk")}
    requests = [
        {key: rng.randrange(6) for key in resources if rng.randrange(2)}
        for _ in range(rng.randrange(8))
    ]
    expected = all(
        sum(req.get(key, 0) for req in requests) <= cap
        for key, cap in resources.items()
    )
    assert is_allocation_feasible(resources, requests) is expected

print("All 1,025 checks passed.")
