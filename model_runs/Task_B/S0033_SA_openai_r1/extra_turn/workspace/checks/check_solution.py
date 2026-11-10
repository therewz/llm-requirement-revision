import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({'cpu': 4}, [{'cpu': 4}], True),
    ({'cpu': 4}, [{'cpu': 5}], False),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 2}], True),
    ({'cpu': 4}, [{'cpu': 3}, {'cpu': 2}], False),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 4, 'ram': 8}], True),
    ({'cpu': 4, 'ram': 8}, [{'cpu': 1, 'ram': 9}], False),
    ({'cpu': 4}, [{'mem': 1}], False),
    ({'cpu': 4}, [{'cpu': 6}, {'cpu': -2}], True),
    ({'cpu': 4}, [{'cpu': -2}, {'cpu': 6}], True),
    ({'cpu': 4}, [{'cpu': -6}], True),
    ({'cpu': 4}, [{'cpu': 0}], True),
    ({'cpu': 2.5}, [{'cpu': 1.25}, {'cpu': 1.25}], True),
    ({'cpu': 2.5}, [{'cpu': 1.25}], True),
    ({'cpu': 2.5}, [{'cpu': 2.75}], False),
    ({'cpu': 4}, [], True),
    ({}, [], True),
    ({}, [{}], True),
    ({}, [{'cpu': 1}], False),
    ({'cpu': 0}, [], False),
    ({'cpu': -1}, [], False),
    ({'cpu': float('nan')}, [], False),
    ({'cpu': float('inf')}, [], False),
    ({'cpu': 4}, [{'cpu': float('nan')}], False),
    ({'cpu': 4}, [{'cpu': float('-inf')}], False),
    ({'disk': 4}, [], False),
    ({'cpu': 4}, [{'disk': 0}], False),
]
for resources, requests, expected in cases:
    result = feasible(resources, requests)
    assert result is expected, (resources, requests, result, expected)

malformed = [
    (None, []), ([], []), ({'cpu': 4}, None), ({'cpu': 4}, {}),
    ({'cpu': 4}, ()), ({'cpu': 4}, [None]), ({'cpu': 4}, [[]]),
    ({1: 4}, []), ({'cpu': '4'}, []), ({'cpu': 4}, [{1: 2}]),
    ({'cpu': 4}, [{'cpu': '2'}]), ({'cpu': 4}, [{'cpu': []}]),
    ({'cpu': 4}, [{'mem': 1}, None]),
]
for resources, requests in malformed:
    try:
        feasible(resources, requests)
    except ValueError:
        pass
    else:
        raise AssertionError(('expected ValueError', resources, requests))

rng = random.Random(33)
for _ in range(1000):
    resources = {key: rng.randint(1, 20) for key in ('cpu', 'ram', 'mem')}
    requests = [
        {key: rng.randint(-10, 10) for key in resources if rng.choice((True, False))}
        for _ in range(rng.randint(0, 10))
    ]
    expected = all(sum(r.get(key, 0) for r in requests) <= cap
                   for key, cap in resources.items())
    assert feasible(resources, requests) is expected
    assert feasible(resources, list(reversed(requests))) is expected

print('Passed 26 allocation cases, 13 malformed-input cases, and 1000 randomized signed-allocation cases.')
