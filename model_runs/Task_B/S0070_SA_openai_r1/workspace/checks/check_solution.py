import importlib.util
from itertools import product
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
    ({"cpu": 4}, [{"cpu": 4}], True),
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 2}], True),
    ({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}], False),
    ({"cpu": 2, "memory": 100}, [{"cpu": 3}], False),
    ({"cpu": 2, "memory": 4}, [{"cpu": 2, "memory": 4}], True),
    ({"cpu": 2.5}, [{"cpu": 1.25}, {"cpu": 1.25}], True),
    ({"cpu": 10**400}, [{"cpu": 10**400}], True),
]
for resources, requests, expected in cases:
    before_resources = resources.copy()
    before_requests = [req.copy() for req in requests]
    result = feasible(resources, requests)
    assert type(result) is bool
    assert result is expected, (resources, requests, expected)
    assert resources == before_resources
    assert requests == before_requests

for cpu, memory, a, b, c, d in product(range(4), repeat=6):
    assert feasible(
        {"cpu": cpu, "memory": memory},
        [{"cpu": a, "memory": b}, {"cpu": c, "memory": d}],
    ) is (a + c <= cpu and b + d <= memory)

for resources, requests, exception in [
    ([], [], TypeError),
    ({"cpu": 1}, {}, TypeError),
    ({"cpu": 1}, [1], TypeError),
    ({"cpu": -1}, [], ValueError),
    ({"cpu": 1}, [{"cpu": -1}], ValueError),
    ({"cpu": 1}, [{"memory": 1}], ValueError),
]:
    try:
        feasible(resources, requests)
    except exception:
        pass
    else:
        raise AssertionError((resources, requests, exception))

print("All checks passed (including 4096 exhaustive allocation cases).")
