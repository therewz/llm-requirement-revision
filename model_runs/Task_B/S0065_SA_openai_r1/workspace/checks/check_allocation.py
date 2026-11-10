import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import is_allocation_feasible


def raises(error, resources, requests):
    try:
        is_allocation_feasible(resources, requests)
    except error:
        return
    raise AssertionError(f"Expected {error.__name__}")


assert is_allocation_feasible({'cpu': 10}, [{'cpu': 10}]) is True
assert is_allocation_feasible({'cpu': 10}, [{'cpu': 2}, {'cpu': 8}]) is True
assert is_allocation_feasible({'cpu': 10}, [{'cpu': 6}, {'cpu': 5}]) is False
assert is_allocation_feasible({'cpu': 10}, [{'cpu': 11}]) is False
assert is_allocation_feasible({}, []) is True
assert is_allocation_feasible({}, [{}]) is True
assert is_allocation_feasible({'cpu': 0}, []) is True
assert is_allocation_feasible({'cpu': 0}, [{'cpu': 1}]) is False
assert is_allocation_feasible({'cpu': 10, 'mem': 8}, [{'cpu': 10, 'mem': 8}]) is True
assert is_allocation_feasible({'cpu': 10**400}, [{'cpu': 10**400}]) is True

raises(TypeError, [], [])
raises(TypeError, {}, {})
raises(TypeError, {}, [1])
raises(TypeError, {1: 10}, [])
raises(TypeError, {'cpu': 10}, [{1: 2}])
raises(ValueError, {'cpu': 10}, [{'mem': 1}])
raises(ValueError, {'cpu': 10}, [{'cpu': 0}])
raises(ValueError, {'cpu': 10}, [{'cpu': -1}])
raises(ValueError, {'cpu': -1}, [])
for amount in (1.0, 1.5, True, '2', None, float('inf'), float('nan')):
    raises(TypeError, {'cpu': 10}, [{'cpu': amount}])
    raises(TypeError, {'cpu': amount}, [])

resources = {'cpu': 10, 'mem': 20}
requests = [{'cpu': 2, 'mem': 5}, {'cpu': 3}]
before = deepcopy((resources, requests))
assert is_allocation_feasible(resources, requests) is True
assert (resources, requests) == before
print('All allocation checks passed.')
