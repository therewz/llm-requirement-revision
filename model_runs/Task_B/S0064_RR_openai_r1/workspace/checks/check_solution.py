import importlib.util
from collections import UserDict
from decimal import Decimal
from fractions import Fraction
from itertools import product

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
f = module.is_allocation_feasible

assert f({'cpu': 10}, [{'cpu': 3}, {'cpu': 6}]) is True
assert f({'cpu': 10}, [{'cpu': 5}, {'cpu': 5}]) is False
assert f({'cpu': 10}, [{'cpu': 5}, {'cpu': 6}]) is False
assert f({'cpu': 10, 'ram': 5}, [{'cpu': 10}]) is True
assert f({'cpu': 10, 'ram': 0}, [{'cpu': 10}]) is False
assert f({'cpu': 10}, [{'missing': 0}]) is False
assert f({}, []) is False
assert f({}, [{}]) is False
assert f({'cpu': 0}, []) is False
assert f({'cpu': 1}, []) is True
assert f(UserDict({1: 3}), [{1: 1}]) is True
assert f({True: True}, [{True: False}]) is True
assert f({'cpu': 10**1000}, [{'cpu': 1}]) is True
assert f({'cpu': float('inf')}, [{'cpu': 1}]) is True
assert f({'cpu': float('inf')}, [{'cpu': float('inf')}]) is False
assert f({'cpu': Decimal('3')}, [{'cpu': Decimal('2.5')}]) is True
assert f({'cpu': Fraction(3, 2)}, [{'cpu': Fraction(1, 2)}]) is True
for invalid in [-1, '1', None, [], {}, 1j, float('nan'), Decimal('NaN')]:
    assert f({'cpu': invalid}, []) is False, invalid
    assert f({'cpu': 3}, [{'cpu': invalid}]) is False, invalid
for requests in [[None], [1], [[], {}], [{'cpu': 10}, 'bad']]:
    try:
        f({'cpu': 1}, requests)
    except ValueError:
        pass
    else:
        raise AssertionError(requests)

# Exhaustive small allocations, including exact exhaustion and unused resources.
for a, b, x, y, z, w in product(range(4), repeat=6):
    expected = x + z <= a and y + w <= b and (x + z < a or y + w < b)
    assert f({'a': a, 'b': b}, [{'a': x, 'b': y}, {'a': z, 'b': w}]) is expected
print('All checks passed (including 4096 exhaustive allocations).')
