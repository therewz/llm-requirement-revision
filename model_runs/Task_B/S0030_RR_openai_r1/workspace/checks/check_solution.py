import importlib.util

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
f = module.is_allocation_feasible

cases = [
    ({'cpu': 10}, [{'cpu': 9}], True),
    ({'cpu': 10}, [{'cpu': 10}], False),
    ({'cpu': 10}, [{'cpu': 11}], False),
    ({'cpu': 10, 'ram': 8}, [{'cpu': 10, 'ram': 7}], True),
    ({'cpu': 10, 'ram': 8}, [{'cpu': 10, 'ram': 8}], False),
    ({'cpu': 10, 'ram': 8}, [{'cpu': 11, 'ram': 1}], False),
    ({'cpu': 10}, [{'cpu': 4}, {'cpu': 5}], True),
    ({'cpu': 10}, [{'gpu': 1}], False),
    ({'cpu': 10}, [{'gpu': 0}], False),
    ({'cpu': 10}, [], True),
    ({}, [], False),
    ({}, [{'cpu': 1}], False),
    ({'cpu': 0}, [], False),
    ({'cpu': 0, 'ram': 1}, [], True),
    ({'cpu': 1e-12}, [], True),
    ({'cpu': 1, 'ram': 1}, [{'cpu': 1 + 1e-10}], False),
    ({'cpu': 10**400}, [{'cpu': 10**400 - 1}], True),
    ({'cpu': 10**400}, [{'cpu': 10**400}], False),
    ({'cpu': 10}, [{}], True),
]
for resources, requests, expected in cases:
    assert f(resources, requests) is expected, (resources, requests)

for resources, requests, error in [
    ({'cpu': -1}, [], ValueError),
    ({'cpu': 10}, [{'cpu': -1}], ValueError),
    ({'cpu': 10}, [{'gpu': -1}], ValueError),
    ({'cpu': 10}, [1], TypeError),
    ({'cpu': 10}, [{'gpu': 1}, 1], TypeError),
    ({'cpu': 10}, [{'cpu': 11}, {'cpu': -1}], ValueError),
    ({'cpu': 10}, [{'gpu': 1}, {'cpu': -1}], ValueError),
]:
    try:
        f(resources, requests)
    except error:
        pass
    else:
        raise AssertionError((resources, requests, error))

print('All 26 allocation checks passed.')
