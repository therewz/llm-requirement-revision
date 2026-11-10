import copy
import importlib.util
from collections import UserDict
from decimal import Decimal
from fractions import Fraction
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
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 2}], True),
    ({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}], False),
    ({"cpu": 4, "ram": 8}, [{"cpu": 4, "ram": 8}], True),
    ({"cpu": 4}, [{"CPU": 1}], False),
    ({}, [{"cpu": 0}], False),
    ({"cpu": 4}, [{"other": 0}], False),
    ({"cpu": 4}, [], True),
    ({"cpu": 4}, [{}, {}], True),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], True),
    ({"cpu": -1}, [], False),
    ({"cpu": 4}, [{"cpu": -1}], False),
    ({"cpu": 10**500}, [{"cpu": 10**500}], True),
    ({"cpu": Decimal("0.3")}, [{"cpu": Decimal("0.1")}, {"cpu": Decimal("0.2")}], True),
    ({"cpu": Fraction(1)}, [{"cpu": Fraction(1, 3)}, {"cpu": Fraction(2, 3)}], True),
    (UserDict({"cpu": 4}), [UserDict({"cpu": 4})], True),
]
for resources, requests, expected in cases:
    original = copy.deepcopy((resources, requests))
    actual = feasible(resources, requests)
    assert actual is expected, (resources, requests, actual, expected)
    assert (resources, requests) == original
print(f"Passed {len(cases)} feasibility and immutability checks.")
