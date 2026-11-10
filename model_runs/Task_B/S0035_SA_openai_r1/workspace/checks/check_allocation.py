import importlib.util
import itertools

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({'seats': 5}, [{'seats': 5}], True),
    ({'seats': 5}, [{'seats': 2}, {'seats': 3}], True),
    ({'seats': 5}, [{'seats': 3}, {'seats': 3}], False),
    ({'seats': 5}, [{'room': 1}], False),
    ({'seats': 5}, [{'room': 0}], False),
    ({}, [], True),
    ({}, [{}], True),
    ({}, [{'seats': 1}], False),
    ({'seats': 0}, [{'seats': 0}], True),
    ({'seats': 0}, [], True),
    ({'seats': 5, 'rooms': 1}, [{'seats': 5, 'rooms': 1}], True),
    ({'seats': 5, 'rooms': 1}, [{'seats': 2}, {'rooms': 2}], False),
    ({'cpu': 1.5}, [{'cpu': 0.5}, {'cpu': 1}], True),
    ({'seats': 10**500}, [{'seats': 10**500}], True),
]
for resources, requests, expected in cases:
    assert feasible(resources, requests) is expected, (resources, requests)

for capacity, first, second in itertools.product(range(6), repeat=3):
    assert feasible({'r': capacity}, [{'r': first}, {'r': second}]) is (first + second <= capacity)

resources = {'r': 4}
requests = [{'r': 2}, {'r': 2}]
assert feasible(resources, requests)
assert resources == {'r': 4} and requests == [{'r': 2}, {'r': 2}]
print('All allocation checks passed.')
