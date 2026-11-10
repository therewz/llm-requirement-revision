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
    ({"seats": 5}, [{"seats": 2}, {"seats": 2}], True),
    ({"seats": 5}, [{"seats": 2}, {"seats": 3}], False),
    ({"seats": 5}, [{"seats": 3}, {"seats": 3}], False),
    ({"seats": 5}, [{"rooms": 1}], False),
    ({"seats": 5}, [{"rooms": 0}], False),
    ({}, [], False),
    ({}, [{}], False),
    ({}, [{"seats": 1}], False),
    ({"seats": 0}, [], False),
    ({"seats": 5}, [], True),
    ({"seats": 5, "rooms": 1}, [{"seats": 5}], True),
    ({"seats": 5, "rooms": 0}, [{"seats": 5}], False),
    ({"seats": 5, "rooms": 1}, [{"seats": 5, "rooms": 1}], False),
    ({"capacity": 1.5}, [{"capacity": 1.25}], True),
    ({"capacity": 10**400}, [{"capacity": 10**400 - 1}], True),
    ({"capacity": 10**400}, [{"capacity": 10**400}], False),
]
for resources, requests, expected in cases:
    before = (resources.copy(), [request.copy() for request in requests])
    assert feasible(resources, requests) is expected
    assert (resources, requests) == before

for ca, cb, a1, b1, a2, b2 in product(range(4), repeat=6):
    resources = {"a": ca, "b": cb}
    requests = [{"a": a1, "b": b1}, {"a": a2, "b": b2}]
    expected = (
        a1 + a2 <= ca
        and b1 + b2 <= cb
        and (a1 + a2 < ca or b1 + b2 < cb)
    )
    assert feasible(resources, requests) is expected

print("Passed 16 targeted cases and 4096 exhaustive allocation cases.")
