import copy
import importlib.util
import itertools
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({"cpu": 10, "ram": 32}, [{"cpu": 4, "ram": 8}], True),
    ({"cpu": 10}, [{"cpu": 4}, {"cpu": 2}], True),
    ({"cpu": 10}, [{"cpu": 4}, {"cpu": 6}], True),
    ({"cpu": 10}, [{"cpu": 4}, {"cpu": 7}], False),
    ({"cpu": 10, "ram": 32}, [{"cpu": 11}], False),
    ({"cpu": 10, "ram": 32}, [{"ram": 33}], False),
    ({"cpu": 10}, [{"ram": 1}], False),
    ({"cpu": 10}, [{"cpu": -3}], False),
    ({"cpu": -5}, [], False),
    ({"cpu": 10, "ram": -1}, [{"cpu": 1}], False),
    ({}, [], True),
    ({}, [{}], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({"cpu": 0}, [{"cpu": 1}], False),
    (None, [], False),
    ({"cpu": 10}, None, False),
    ({"cpu": 10}, {"cpu": 1}, False),
    ({"cpu": 10}, [1], False),
    ({1: 10}, [], False),
    ({"cpu": 10}, [{1: 1}], False),
    ({"cpu": "10"}, [], False),
    ({"cpu": 10}, [{"cpu": "1"}], False),
    ({"cpu": True}, [], False),
    ({"cpu": 10}, [{"cpu": False}], False),
    ({"cpu": 1.5}, [], False),
    ({"cpu": 10}, [{"cpu": 1.5}], False),
]
for resources, requests, expected in cases:
    before = copy.deepcopy((resources, requests))
    actual = feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)
    assert (resources, requests) == before

for capacity in range(5):
    for amounts in itertools.product(range(4), repeat=3):
        requests = [{"cpu": amount} for amount in amounts]
        expected = sum(amounts) <= capacity
        assert feasible({"cpu": capacity}, requests) is expected
        assert feasible({"cpu": capacity}, requests[::-1]) is expected

print("All 26 focused cases and 320 aggregate/order checks passed.")
