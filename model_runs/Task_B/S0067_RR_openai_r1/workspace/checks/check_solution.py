import copy
import importlib.util

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({'a': 5, 'b': 2}, [{'a': 5, 'b': 1}], True),
    ({'a': 1}, [{'a': 0.75}], True),
    ({'a': 0.5}, [], True),
    ({'a': 5, 'b': 2}, [{'a': 5}, {'b': 2}], False),
    ({'a': 5, 'b': 2}, [{'a': 3}, {'a': 3}], False),
    ({'a': 0, 'b': 1}, [{'a': 0}], True),
    ({'a': 0}, [{'a': 0}], False),
    ({}, [], False),
    ({'a': 5}, [{'a': 2}, {'a': 2}], True),
    ({'a': 5}, [{'a': 2}, {'a': 3}], False),
]
for resources, requests, expected in cases:
    original = copy.deepcopy((resources, requests))
    assert feasible(resources, requests) is expected, (resources, requests)
    assert (resources, requests) == original

for resources, requests, error in [
    ({'a': -1}, [], ValueError),
    ({'a': 2}, [{'a': -1}], ValueError),
    ({'a': 2}, [{'b': 0}], ValueError),
    ({'a': '2'}, [], TypeError),
    ({'a': 2}, [{'a': '1'}], TypeError),
]:
    try:
        feasible(resources, requests)
    except error:
        pass
    else:
        raise AssertionError((resources, requests, error))

print('All allocation checks passed.')
