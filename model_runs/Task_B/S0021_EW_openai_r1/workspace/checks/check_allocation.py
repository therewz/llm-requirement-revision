from pathlib import Path
import runpy

is_allocation_feasible = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "src" / "solution.py")
)["is_allocation_feasible"]

cases = [
    ({"cpu": 4}, [{"cpu": 4}], True),
    ({"cpu": 4, "memory": 8}, [{"cpu": 1, "memory": 3}, {"cpu": 3, "memory": 5}], True),
    ({"cpu": 4}, [{"cpu": 3}], True),
    ({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}], False),
    ({"cpu": 4, "memory": 8}, [{"cpu": 5}], False),
    ({}, [], True),
    ({"cpu": 0}, [{"cpu": 0}], True),
    ({}, [{"cpu": 0}], True),
    ({}, [{"cpu": 1}], False),
    ({"cpu": 4}, [], True),
]
for resources, requests, expected in cases:
    assert is_allocation_feasible(resources, requests) is expected, (resources, requests)

for resources, requests in [([], []), ({"cpu": -1}, []), ({}, {}), ({}, [1]), ({}, [{"cpu": -1}])]:
    try:
        is_allocation_feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError((resources, requests))

print("All allocation checks passed.")
