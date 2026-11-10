import importlib.util
import itertools

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({}, [], True),
    ({}, [{}], True),
    ({'gpu': 0}, [{'gpu': 0}], True),
    ({'gpu': 4}, [{'gpu': 4}], True),
    ({'gpu': 4}, [{'gpu': 1}, {'gpu': 3}], True),
    ({'gpu': 4, 'cpu': 2}, [{'gpu': 4, 'cpu': 2}], True),
    ({'gpu': 4}, [{'gpu': 2}, {'gpu': 3}], False),
    ({'gpu': 4}, [{'cpu': 1}], False),
    ({'gpu': 4}, [{'cpu': 0}], False),
    ({'gpu': 4}, [{'gpu': -1}], False),
    ({'gpu': -1}, [], False),
    ({'gpu': 4.0}, [], False),
    ({'gpu': 4}, [{'gpu': 1.0}], False),
    ({'gpu': True}, [], False),
    ({'gpu': 4}, [{'gpu': False}], False),
    ({'gpu': '4'}, [], False),
    ({'gpu': 4}, [{'gpu': '1'}], False),
    ({str(i): 1 for i in range(70)}, [], True),
    ({str(i): 1 for i in range(71)}, [], False),
]
for resources, requests, expected in cases:
    original_resources = dict(resources)
    original_requests = [dict(request) for request in requests]
    result = feasible(resources, requests)
    assert result is expected, (resources, requests, result, expected)
    assert resources == original_resources
    assert requests == original_requests

for cap_a, cap_b, a1, b1, a2, b2 in itertools.product(range(4), repeat=6):
    resources = {'a': cap_a, 'b': cap_b}
    requests = [{'a': a1, 'b': b1}, {'a': a2, 'b': b2}]
    expected = a1 + a2 <= cap_a and b1 + b2 <= cap_b
    assert feasible(resources, requests) is expected

print('All 4,115 feasibility checks passed.')
