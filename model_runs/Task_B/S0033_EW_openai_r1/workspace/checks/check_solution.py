import runpy

is_allocation_feasible = runpy.run_path("src/solution.py")["is_allocation_feasible"]

cases = [
    ({"cpu": 4}, [{"cpu": 4}], True),
    ({"cpu": 4, "ram": 8, "mem": 2},
     [{"cpu": 1, "ram": 8}, {"cpu": 3, "mem": 2}], True),
    ({"cpu": 4}, [{"cpu": 2}, {"cpu": 3}], False),
    ({"cpu": 4, "ram": 8}, [{"cpu": 5}], False),
    ({"cpu": 4}, [{"ram": 1}], False),
    ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], True),
    ({"cpu": 4}, [{"cpu": 3}], True),
    ({"cpu": 4}, [], True),
    ({}, [], True),
    ({}, [{"cpu": 1}], False),
    ({"cpu": 4}, [{"cpu": -1}], True),
    ({"cpu": 4}, [{"cpu": 5}, {"cpu": -1}], True),
    ({"cpu": 4}, [{"cpu": -1}, {"cpu": 5}], True),
    ({"cpu": 0}, [], False),
    ({"cpu": -1}, [], False),
    ({"cpu": float("nan")}, [], False),
    ({"cpu": float("inf")}, [], False),
    ({"cpu": 4}, [{"cpu": float("nan")}], False),
    ({"cpu": 4}, [{"cpu": float("inf")}], False),
    ({"gpu": 4}, [], False),
]
for resources, requests, expected in cases:
    result = is_allocation_feasible(resources, requests)
    assert result is expected, (resources, requests, result, expected)

malformed = [
    (None, []),
    ([], []),
    ({"cpu": 4}, None),
    ({"cpu": 4}, {}),
    ({"cpu": 4}, [1]),
    ({1: 4}, []),
    ({"cpu": "4"}, []),
    ({"cpu": 4}, [{1: 1}]),
    ({"cpu": 4}, [{"cpu": "1"}]),
    ({"cpu": 4}, [{"cpu": [1]}]),
]
for resources, requests in malformed:
    try:
        is_allocation_feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError((resources, requests, "Expected ValueError"))

print(f"Passed {len(cases)} allocation checks and {len(malformed)} format checks.")
