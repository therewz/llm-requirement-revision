import sys
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
from itertools import product

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import is_allocation_feasible as feasible

assert feasible({'cpu': 5, 'ram': 2}, [{'cpu': 5}]) is True
assert feasible({'cpu': 5}, [{'cpu': 5}]) is False
assert feasible({'cpu': 5, 'ram': 2}, [{'cpu': 6}]) is False
assert feasible({'cpu': 5}, [{'ram': 1}]) is False
assert feasible({'cpu': 1}, []) is True
assert feasible({}, []) is False
assert feasible({'cpu': 0}, []) is False
assert feasible({'cpu': -1}, []) is False
assert feasible({'cpu': 0.5}, [{'cpu': 0.25}]) is True
assert feasible({'cpu': 0.3, 'ram': 1}, [{'cpu': 0.1}, {'cpu': 0.2}]) is True
assert feasible({'cpu': 0.3}, [{'cpu': 0.1}, {'cpu': 0.2}]) is False
assert feasible({'cpu': 0.3}, [{'cpu': 0.30000000000000004}]) is False
assert feasible({'cpu': 5}, [{'cpu': 8}, {'cpu': -4}]) is True
assert feasible({'cpu': 5}, [{'cpu': -4}, {'cpu': 8}]) is True
assert feasible({'cpu': 5}, [{'cpu': -1}]) is True
assert feasible({'cpu': 1}, [{'cpu': 0}]) is True
assert feasible({'cpu': 1}, [{}]) is True
assert feasible({'gpu': 1}, []) is False
assert feasible({'cpu': Decimal('0.3'), 'ram': 1},
                [{'cpu': Decimal('0.1')}, {'cpu': 0.2}]) is True
assert feasible({'cpu': Fraction(1, 3)}, [{'cpu': Fraction(1, 4)}]) is True
for value in [float('nan'), float('inf'), -float('inf'), Decimal('NaN'), Decimal('sNaN'), Decimal('Infinity')]:
    assert feasible({'cpu': value}, []) is False
    assert feasible({'cpu': 2}, [{'cpu': value}]) is False

for resources, requests in [
    (None, []), ([], []), ({'cpu': 1}, None), ({'cpu': 1}, {}),
    ({'cpu': 1}, [1]), ({1: 1}, []), ({'cpu': '1'}, []),
    ({'cpu': 1}, [{1: 1}]), ({'cpu': 1}, [{'cpu': '1'}]),
    ({'cpu': 1}, [{'cpu': []}]),
]:
    try:
        feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError((resources, requests))

for cpu, ram, a, b, c in product(range(1, 4), range(1, 4), range(-3, 5), range(-3, 5), range(-3, 5)):
    expected = a + b <= cpu and c <= ram and (a + b < cpu or c < ram)
    assert feasible({'cpu': cpu, 'ram': ram}, [{'cpu': a}, {'cpu': b, 'ram': c}]) is expected

resources = {'cpu': 3}
requests = [{'cpu': 1}]
assert feasible(resources, requests) is True
assert resources == {'cpu': 3} and requests == [{'cpu': 1}]
print('All allocation checks passed (including 4,608 exhaustive signed cases).')
