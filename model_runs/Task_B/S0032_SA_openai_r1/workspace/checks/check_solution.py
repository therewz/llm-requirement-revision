import importlib.util
from fractions import Fraction
from itertools import permutations
import random

spec = importlib.util.spec_from_file_location("solution", "src/solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({"resourceA": 10}, [{"resourceA": 6}], True),
    ({"resourceA": 10}, [{"resourceA": 6}, {"resourceB": 8}], False),
    ({"resourceA": 10}, [{"resourceB": 5}], False),
    ({"resourceA": 10}, [{"resourceA": -1}], False),
    ({}, [{"resourceA": 0}], False),
    ({"resourceA": 10}, [{"resourceA": 10}], True),
    ({}, [], True),
    ({}, [{}], True),
    ({"a": 0}, [{"a": 0}], True),
    ({"a": 10}, [{"a": 6}, {"a": 5}], False),
    ({"a": 10, "b": 8}, [{"a": 6, "b": 8}, {"a": 4}], True),
    ({"a": 1.5}, [{"a": 0.5}, {"a": 1}], True),
    ({"a": 10}, ["a"], False),
    ({"a": 10}, [{"a": "1"}], False),
    ({"a": 10}, [{"a": float("nan")}], False),
    ({"a": -1}, [], False),
    ({"a": float("nan")}, [], False),
    (None, [], False),
    ({"a": 10}, None, False),
    ({1: 10}, [], False),
    ({"a": 10}, [{1: 0}], False),
    ({"a": float("inf")}, [{"a": float("inf")}], True),
    ({"a": 10}, [{"a": float("inf")}], False),
    ({"a": 10**1000}, [{"a": 10**1000}], True),
    ({"a": 10**1000}, [{"a": 10**1000}, {"a": 0.5}], False),
]
for resources, requests, expected in cases:
    actual = feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)

for amounts in ([0.1, 0.2, 0.3], [0.5, 0.5, 2**-54], [0.25, 0.5, 0.25]):
    expected = sum(map(Fraction, amounts)) <= Fraction(1 if amounts[0] != 0.1 else 0.6)
    capacity = 1 if amounts[0] != 0.1 else 0.6
    for order in permutations(amounts):
        assert feasible({"a": capacity}, [{"a": value} for value in order]) is expected

rng = random.Random(32)
for _ in range(500):
    resources = {key: rng.randrange(20) / 4 for key in ("a", "b")}
    requests = [
        {rng.choice(("a", "b")): rng.randrange(10) / 4}
        for _ in range(rng.randrange(8))
    ]
    expected = all(
        sum(Fraction(request.get(key, 0)) for request in requests) <= capacity
        for key, capacity in resources.items()
    )
    original_resources = dict(resources)
    original_requests = [dict(request) for request in requests]
    assert feasible(resources, requests) is expected
    assert resources == original_resources and requests == original_requests
    rng.shuffle(requests)
    assert feasible(resources, requests) is expected

print("All acceptance, validation, numeric, and order-independence checks passed.")
