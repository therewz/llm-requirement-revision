import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from solution import is_allocation_feasible as feasible


assert feasible({"CPU": 10}, [{"CPU": 5}]) is True
assert feasible({"RAM": 30}, [{"RAM": 10}, {"RAM": 15}, {"RAM": 10}]) is False
assert feasible({"disk": 5.0}, [{"disk": 2.5}, {"disk": 2.5}]) is False
assert feasible({"disk": 5.0, "CPU": 1}, [{"disk": 2.5}, {"disk": 2.5}]) is True
assert feasible({"CPU": 10}, [{"GPU": 1}]) is False
assert feasible({"CPU": 10}, [{"GPU": 0}]) is False
assert feasible({"CPU": 10}, [("CPU", 3), ("CPU", 2.0)]) is True
assert feasible({"CPU": 10}, [("CPU", 5), {"CPU": 5}]) is False
assert feasible({1: 10}, [{1: 5}]) is True
assert feasible({}, []) is False
assert feasible({}, [{"CPU": 1}]) is False
assert feasible({"CPU": 0}, []) is False
assert feasible({"CPU": 1}, []) is True
assert feasible({"CPU": 10}, [{}]) is True
assert feasible({"CPU": 2**53, "RAM": 1}, [{"CPU": 2**53}, {"CPU": 1.0}]) is False
assert feasible({"CPU": 10**400}, [{"CPU": 10**400 - 1}]) is True
assert feasible({"CPU": 10**400}, [{"CPU": 10**400}]) is False
assert feasible({"CPU": 10**400}, [{"CPU": 10**400 + 1}]) is False

for invalid in (-1, float("nan"), float("inf"), -float("inf"), "5", None, True):
    for resources, requests in (
        ({"CPU": invalid}, []),
        ({"CPU": 10}, [{"CPU": invalid}]),
        ({"CPU": 10}, [("CPU", invalid)]),
    ):
        try:
            feasible(resources, requests)
        except ValueError:
            pass
        else:
            raise AssertionError((resources, requests))

# Validation is not bypassed by an earlier infeasible request.
try:
    feasible({"CPU": 10}, [{"CPU": 20}, {"CPU": -1}])
except ValueError:
    pass
else:
    raise AssertionError("negative request was not rejected")

# Caller-owned inputs remain unchanged.
resources = {"CPU": 10}
requests = [{"CPU": 3}, {"CPU": 2}]
assert feasible(resources, requests)
assert resources == {"CPU": 10}
assert requests == [{"CPU": 3}, {"CPU": 2}]

print("All allocation checks passed.")
