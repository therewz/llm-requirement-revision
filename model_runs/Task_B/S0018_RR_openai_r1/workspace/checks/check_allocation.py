import importlib.util
import itertools
from pathlib import Path

spec = importlib.util.spec_from_file_location('solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

cases = [
    ({'cpu': 4}, [{'cpu': 3}], True),
    ({'cpu': 4}, [{'cpu': 4}], False),
    ({'cpu': 4}, [{'cpu': 5}], False),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 4, 'ram': 7}], True),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 4, 'ram': 8}], False),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 5}], False),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 2}], False),
    ({'cpu': 4}, [{'cpu': 1}, {'cpu': 2}], True),
    ({'cpu': 4}, [{'cpu': None}, {}], True),
    ({'cpu': 4}, [{'unknown': 1}], False),
    ({}, [], False),
    ({'cpu': 0}, [], False),
    ({'cpu': 1}, [], True),
    ({'cpu': 0, 'ram': 1}, [], True),
    ({'cpu': 1.5}, [{'cpu': 0.5}, {'cpu': 0.5}], True),
    ({'cpu': 1.5}, [{'cpu': 0.5}, {'cpu': 1}], False),
    ({'cpu': 2**53 + 1}, [{'cpu': 2**53}], True),
    ({'cpu': 2**53}, [{'cpu': 2**53 + 1}], False),
    ({'cpu': 10**400}, [{'cpu': 10**400 - 1}], True),
    ({'cpu': 10**400}, [{'cpu': 10**400}], False),
    ({'cpu': 10**400}, [{'cpu': 10**400 + 1}], False),
]
for resources, requests, expected in cases:
    actual = feasible(resources, requests)
    assert actual is expected, (resources, requests, expected, actual)

for cap_a, cap_b, a1, b1, a2, b2 in itertools.product(range(4), repeat=6):
    expected = (a1 + a2 <= cap_a and b1 + b2 <= cap_b
                and (a1 + a2 < cap_a or b1 + b2 < cap_b))
    assert feasible({'a': cap_a, 'b': cap_b}, [{'a': a1, 'b': b1}, {'a': a2, 'b': b2}]) is expected

for resources, requests in [
    ({'cpu': -1}, []),
    ({'cpu': float('inf')}, []),
    ({'cpu': float('nan')}, []),
    ({'cpu': True}, []),
    ({'cpu': 3}, [{'cpu': -1}]),
    ({'cpu': 3}, [{'cpu': float('inf')}]),
    ({'cpu': 3}, [{'cpu': float('nan')}]),
]:
    try:
        feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError('Expected ValueError')

print('All allocation checks passed (21 cases, 4096 exhaustive cases, 7 validation cases).')
