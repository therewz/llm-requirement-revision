import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from solution import is_allocation_feasible

cases = [
    ({'cpu': 4, 'ram': 8}, [{'cpu': 1, 'ram': 3}, {'cpu': 3, 'ram': 5}], True),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 3}], False),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 2, 'ram': 9}], False),
    ({'cpu': 4}, [{'cpu': 1}], True),
    ({}, [], True),
    ({'cpu': 0}, [], True),
    ({'cpu': 0}, [{'cpu': 0}], True),
    ({}, [{'gpu': 1}], False),
    ({}, [{'gpu': 0}], True),
    ({'cpu': 2**60}, [{'cpu': 2**60}, {'cpu': 1}], False),
]
for resources, requests, expected in cases:
    actual = is_allocation_feasible(resources, requests)
    assert actual is expected, (resources, requests, actual, expected)
    assert is_allocation_feasible(resources, list(reversed(requests))) is expected

resources = {'cpu': 4}
requests = [{'cpu': 2}, {'cpu': 2}]
assert is_allocation_feasible(resources, requests)
assert resources == {'cpu': 4} and requests == [{'cpu': 2}, {'cpu': 2}]
print('All allocation checks passed.')
