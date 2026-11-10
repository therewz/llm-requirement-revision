import sys
from copy import deepcopy
from fractions import Fraction
from itertools import product

sys.path.insert(0, ".")
from src.solution import is_allocation_feasible

cases = [
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 2}], True),
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 3}], False),
    ({"cpu": 4, "ram": 8}, [{"cpu": 4, "ram": 8}], True),
    ({"cpu": 4, "ram": 8}, [{"cpu": 3}, {"ram": 9}], False),
    ({"cpu": 4}, [], True),
    ({}, [], True),
    ({}, [{}], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({}, [{"cpu": 1}], False),
    ({"cpu": 4}, [{"ram": 1}], False),
    ({}, [{"cpu": 0}], True),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], True),
    ({"cpu": 10**1000}, [{"cpu": 10**1000}], True),
    ({"cpu": Fraction(1, 2)}, [{"cpu": Fraction(1, 4)}] * 2, True),
]
for resources, requests, expected in cases:
    before = deepcopy((resources, requests))
    result = is_allocation_feasible(resources, requests)
    assert result is expected, (resources, requests, result, expected)
    assert (resources, requests) == before

for cpu, ram, a, b, c, d in product(range(4), repeat=6):
    resources = {"cpu": cpu, "ram": ram}
    requests = [{"cpu": a, "ram": b}, {"cpu": c, "ram": d}]
    expected = a + c <= cpu and b + d <= ram
    assert is_allocation_feasible(resources, requests) is expected

print("All 4110 checks passed.")
