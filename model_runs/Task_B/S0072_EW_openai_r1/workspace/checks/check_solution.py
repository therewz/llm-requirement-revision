import copy
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)

cases = [
    ({"cpu": 4, "mem": 8}, [{"cpu": 2, "mem": 3}, {"cpu": 2, "mem": 5}], True),
    ({"cpu": 4}, [{"cpu": 3}], True),
    ({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}], False),
    ({"cpu": 4, "mem": 8}, [{"cpu": 5, "mem": 1}], False),
    ({"cpu": 4}, [], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({}, [], True),
    ({}, [{}], True),
    ({}, [{"cpu": 1}], False),
    ({"cpu": 1}, [{"mem": 1}], False),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], True),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.25}], False),
    ({"cpu": 10**400}, [{"cpu": 10**400}], True),
]
for resources, requests, expected in cases:
    original = copy.deepcopy((resources, requests))
    for _ in range(2):
        result = solution.is_allocation_feasible(resources, requests)
        assert type(result) is bool
        assert result is expected, (resources, requests, result, expected)
        assert (resources, requests) == original

print(f"Passed {len(cases)} feasibility cases, including non-mutation and determinism checks.")
