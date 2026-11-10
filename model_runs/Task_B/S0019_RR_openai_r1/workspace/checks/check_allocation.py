import importlib.util
from collections import UserDict
from pathlib import Path
from types import MappingProxyType

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({"cpu": 4}, [{"cpu": 3}], True),
    ({"cpu": 4}, [{"cpu": 4}], False),
    ({"cpu": 4}, [{"cpu": 5}], False),
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 2}], False),
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 3}], False),
    ({"cpu": 4, "memory": 8}, [{"cpu": 4}], True),
    ({"cpu": 4, "memory": 8}, [{"cpu": 5}], False),
    ({"cpu": 1.0}, [{"cpu": 0.75}], True),
    ({"cpu": 4}, [{"other": 1}], False),
    ({"cpu": 4}, [], True),
    ({"cpu": 0}, [], False),
    ({}, [], False),
    ({"cpu": 4}, [UserDict({"cpu": 3})], True),
    ({"cpu": 4}, [MappingProxyType({"cpu": 3})], True),
]
for resources, requests, expected in cases:
    assert feasible(resources, requests) is expected, (resources, requests, expected)

resources = {"cpu": 4}
requests = [{"cpu": 1}, {"cpu": 2}]
assert feasible(resources, requests)
assert resources == {"cpu": 4}
assert requests == [{"cpu": 1}, {"cpu": 2}]
print(f"Passed {len(cases)} allocation cases and input-preservation checks.")
