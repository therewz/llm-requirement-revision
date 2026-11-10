import copy
import importlib.util
import itertools
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({"cpu": 4, "mem": 8}, [{"cpu": 2, "mem": 3}, {"cpu": 2, "mem": 5}], True),
    ({"cpu": 4, "mem": 8}, [{"cpu": 3}, {"cpu": 2}], False),
    ({"cpu": 4, "mem": 8}, [{"mem": 9}], False),
    ({"cpu": 4, "mem": 8}, [{"cpu": 1}], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({}, [], True),
    ({}, [{}], True),
    ({"cpu": 4}, [], True),
    ({"cpu": 4}, [{"gpu": 1}], False),
    ({}, [{"cpu": 0}], True),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], True),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.25}], False),
    ({"cpu": 10 ** 400}, [{"cpu": 10 ** 400}], True),
]
for resources, requests, expected in cases:
    before = copy.deepcopy((resources, requests))
    result = feasible(resources, requests)
    assert type(result) is bool
    assert result is expected, (resources, requests, result)
    assert result is feasible(resources, requests)
    assert (resources, requests) == before

count = len(cases)
for cpu, mem, a, b, c, d in itertools.product(range(4), repeat=6):
    resources = {"cpu": cpu, "mem": mem}
    requests = [{"cpu": a, "mem": b}, {"cpu": c, "mem": d}]
    expected = a + c <= cpu and b + d <= mem
    assert feasible(resources, requests) is expected
    assert feasible(resources, list(reversed(requests))) is expected
    count += 1

print(f"Passed {count} cases, including exact capacity, empty inputs, and immutability.")
