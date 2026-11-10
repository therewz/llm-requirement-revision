import importlib.util
import itertools
from copy import deepcopy

spec = importlib.util.spec_from_file_location("solution", "src/solution.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({"resourceA": 10}, [{"resourceA": 6}], True),
    ({"resourceA": 10}, [{"resourceA": 6}, {"resourceB": 8}], False),
    ({"resourceA": 10}, [{"resourceB": 5}], False),
    ({"resourceA": 10}, [{"resourceA": -1}], False),
    ({}, [{"resourceA": 0}], False),
    ({"resourceA": 10}, [{"resourceA": 10}], True),
    ({"a": 10, "b": 8}, [{"a": 4, "b": 8}, {"a": 6}], True),
    ({"a": 10}, [{"a": 6}, {"a": 5}], False),
    ({"a": 0}, [{"a": 0}], True),
    ({}, [], True),
    ({}, [{}], True),
    ({"a": 10}, [], True),
    ({"a": 1.5}, [{"a": 0.5}, {"a": 1.0}], True),
    ({"a": 10**400}, [{"a": 10**400}], True),
    ({"a": float("inf")}, [{"a": float("inf")}], True),
    ({"a": 10}, [{"a": float("inf")}], False),
    ({"a": 10}, [{"a": float("nan")}], False),
]
for resources, requests, expected in cases:
    assert feasible(resources, requests) is expected, (resources, requests, expected)

resources = {"a": 10, "b": 4}
requests = [{"a": 6}, {"a": 4, "b": 4}]
before = deepcopy((resources, requests))
assert feasible(resources, requests)
assert (resources, requests) == before

for values, capacity in [([0.1, 0.2, 0.3], 0.6), ([0.25, 0.5, 0.25], 1.0)]:
    results = {
        feasible({"a": capacity}, [{"a": value} for value in order])
        for order in itertools.permutations(values)
    }
    assert len(results) == 1

print("All allocation checks passed.")
