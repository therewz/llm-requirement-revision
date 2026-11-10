from pathlib import Path
import runpy

is_allocation_feasible = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "src" / "solution.py")
)["is_allocation_feasible"]

cases = [
    ({"cpu": 4}, [{"cpu": 4}], True),
    ({"cpu": 4, "ram": 8}, [{"cpu": 1, "ram": 3}, {"cpu": 3, "ram": 5}], True),
    ({"cpu": 4}, [{"cpu": 3}], True),
    ({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}], False),
    ({"cpu": 4}, [{"ram": 1}], False),
    ({}, [], True),
    ({}, [{}], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({"cpu": 0}, [], True),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], True),
]
for resources, requests, expected in cases:
    assert is_allocation_feasible(resources, requests) is expected

for resources, requests in [
    ([], []),
    ({}, {}),
    ({"cpu": -1}, []),
    ({"cpu": "four"}, []),
    ({"cpu": 4}, [None]),
    ({"cpu": 4}, [{"cpu": -1}]),
    ({"cpu": 4}, [{"cpu": "one"}]),
]:
    try:
        is_allocation_feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError((resources, requests))

print("All 17 checks passed.")
