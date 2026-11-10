"""Regression checks for resource allocation feasibility."""

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
    ({"cpu": 3}, [{"cpu": 2}], True),
    ({"cpu": 3}, [{"cpu": 3}], False),
    ({"cpu": 3}, [{"cpu": 4}], False),
    ({"cpu": 3}, [{"cpu": 2}, {"cpu": 2}], False),
    ({"cpu": 3}, [{"cpu": 1}, {"cpu": 1}], True),
    ({"cpu": 3, "gpu": 1}, [{"cpu": 3}], True),
    ({"cpu": 3, "gpu": 1}, [{"cpu": 3, "gpu": 1}], False),
    ({"cpu": 3, "gpu": 1}, [{"cpu": 4}], False),
    ({"cpu": 1}, [], True),
    ({"cpu": 1}, [{"cpu": 0}], True),
    ({}, [], False),
    ({"cpu": 0}, [], False),
    ({"cpu": 0}, [{"cpu": 0}], False),
    ({"cpu": 1}, [{"gpu": 0}], False),
    ({"cpu": 1}, [{"cpu": -1}], False),
    ({"cpu": -1}, [], False),
    ({"cpu": 1.0}, [], False),
    ({"cpu": 1}, [{"cpu": 0.0}], False),
    ({"cpu": True}, [], False),
    ({"cpu": 2}, [{"cpu": True}], False),
    ({"cpu": "2"}, [], False),
    ({"cpu": 2}, [{"cpu": "1"}], False),
    ({"cpu": 70}, [{"cpu": 69}], True),
    ({"cpu": 71}, [], False),
    ({"cpu": 35, "gpu": 35}, [], True),
    ({"cpu": 36, "gpu": 35}, [], False),
]
for resources, requests, expected in cases:
    original_resources = dict(resources)
    original_requests = [dict(request) for request in requests]
    actual = feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)
    assert resources == original_resources
    assert requests == original_requests

# Exhaustively cover small capacities and two competing software units.
for cpu, gpu, a, b, c, d in product(range(4), repeat=6):
    expected = (
        a + c <= cpu
        and b + d <= gpu
        and a + b + c + d < cpu + gpu
    )
    assert feasible(
        {"cpu": cpu, "gpu": gpu},
        [{"cpu": a, "gpu": b}, {"cpu": c, "gpu": d}],
    ) is expected

print(f"Passed {len(cases)} regression cases and 4096 exhaustive cases.")
