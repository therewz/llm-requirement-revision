import importlib.util
import itertools

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

assert feasible({'cpu': 10}, [{'cpu': 2}, {'cpu': 3}]) is True
assert feasible({'cpu': 10}, [{'cpu': 10}]) is False
assert feasible({'cpu': 10}, [{'cpu': 6}, {'cpu': 5}]) is False
assert feasible({'cpu': 10, 'mem': 2}, [{'cpu': 10, 'mem': 1}]) is True
assert feasible({'cpu': 10, 'mem': 2}, [{'cpu': 10, 'mem': 2}]) is False
assert feasible({'cpu': 10, 'mem': 0}, [{'cpu': 10}]) is False
assert feasible({}, []) is False
assert feasible({'cpu': 0}, []) is False
assert feasible({'cpu': 1}, []) is True
assert feasible({'cpu': 10}, [{}]) is True
assert feasible({'cpu': 10 ** 1000}, [{'cpu': 1}]) is True


def raises(error, resources, requests):
    try:
        feasible(resources, requests)
    except error:
        return
    raise AssertionError(f'Expected {error.__name__}')

for amount in (0, -1):
    raises(ValueError, {'cpu': 10}, [{'cpu': amount}])
for amount in (1.0, 0.5, True, '2', None, [], {}):
    raises(TypeError, {'cpu': 10}, [{'cpu': amount}])
for amount in (1.0, True, '2'):
    raises(TypeError, {'cpu': amount}, [])
raises(ValueError, {'cpu': 10}, [{'mem': 1}])
raises(TypeError, [], [])
raises(TypeError, {'cpu': 10}, {})
raises(TypeError, {'cpu': 10}, [1])
raises(TypeError, {1: 10}, [])
raises(TypeError, {'cpu': 10}, [{1: 1}])

for a, b, x, y in itertools.product(range(4), repeat=4):
    inventory = {'a': a, 'b': b}
    requests = []
    if x:
        requests.append({'a': x})
    if y:
        requests.append({'b': y})
    original = inventory.copy()
    expected = x <= a and y <= b and (x < a or y < b)
    assert feasible(inventory, requests) is expected
    assert inventory == original

print('All allocation checks passed.')
