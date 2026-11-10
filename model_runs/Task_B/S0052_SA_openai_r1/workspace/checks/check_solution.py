import copy
import importlib.util
import itertools
import math
import random

spec = importlib.util.spec_from_file_location("solution", "src/solution.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({}, [], True),
    ({"cpu": 3}, [], True),
    ({"cpu": 3}, [{}], True),
    ({"cpu": 3}, [{"cpu": 1}, {"cpu": 2}], True),
    ({"cpu": 3}, [{"cpu": 2}, {"cpu": 2}], False),
    ({"cpu": 3, "ram": 9}, [{"cpu": 4}], False),
    ({}, [{"missing": 0}], False),
    ({"cpu": 3}, [{"cpu": -1}], False),
    ({"unused": -1}, [], False),
    ({"unused": math.inf}, [], False),
    ({"unused": math.nan}, [], False),
    ({"cpu": 3}, [{"cpu": math.inf}], False),
    ({"cpu": 3}, [{"cpu": math.nan}], False),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], True),
    ({"cpu": 10**1000}, [{"cpu": 10**1000}], True),
    ([], [], True),
    ([1, 2], [1, 2], True),
    ([1, 2], [2, 1], False),
    ([1], [], False),
    ([], [0], False),
    ([-1], [0], False),
    ([1], [-1], False),
    ([math.inf], [0], False),
    ([1], [math.nan], False),
    ([1.5], [1.25], True),
]
for resources, requests, expected in cases:
    assert feasible(resources, requests) is expected, (resources, requests)

for n in range(4):
    for resources in itertools.product(range(3), repeat=n):
        for requests in itertools.product(range(3), repeat=n):
            expected = all(d <= c for c, d in zip(resources, requests))
            assert feasible(list(resources), list(requests)) is expected

rng = random.Random(52)
for _ in range(1000):
    resources = {key: rng.randrange(10) for key in ("cpu", "ram", "disk")}
    requests = [
        {key: rng.randrange(5) for key in resources if rng.randrange(2)}
        for _ in range(rng.randrange(5))
    ]
    before = copy.deepcopy((resources, requests))
    expected = all(
        sum(request.get(key, 0) for request in requests) <= capacity
        for key, capacity in resources.items()
    )
    assert feasible(resources, requests) is expected
    assert (resources, requests) == before

print("All allocation checks passed.")
