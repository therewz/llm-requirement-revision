import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from solution import is_allocation_feasible

cases = [
    ({"cpu": 4}, [{"cpu": 3}], True),
    ({"cpu": 4}, [{"cpu": 4}], False),
    ({"cpu": 4}, [{"cpu": 5}], False),
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 2}], False),
    ({"cpu": 4}, [{"cpu": 1}, {"cpu": 2}], True),
    ({"cpu": 4, "memory": 8}, [{"cpu": 4, "memory": 7}], True),
    ({"cpu": 4, "memory": 8}, [{"cpu": 4, "memory": 8}], False),
    ({"cpu": 4, "memory": 8}, [{"cpu": 4}], True),
    ({"cpu": 4}, [{"memory": 1}], False),
    ({"cpu": 4}, [], True),
    ({}, [], False),
    ({"cpu": 0}, [], False),
    ({"cpu": 0, "memory": 1}, [{"cpu": 0}], True),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 0.75}], True),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], False),
]

for resources, requests, expected in cases:
    actual = is_allocation_feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)

print(f"Passed {len(cases)} allocation feasibility checks.")
