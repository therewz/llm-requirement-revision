import copy
import itertools
import runpy

is_allocation_feasible = runpy.run_path('src/solution.py')['is_allocation_feasible']

cases = [
    ({'cpu': 4, 'mem': 8}, [{'cpu': 2, 'mem': 4}], True),
    ({'cpu': 4, 'mem': 8}, [{'cpu': 4, 'mem': 8}], False),
    ({'cpu': 4, 'mem': 8}, [{'cpu': 4, 'mem': 7}], True),
    ({'cpu': 4, 'mem': 8}, [{'cpu': 5}], False),
    ({'cpu': 4}, [{'cpu': 2}, {'cpu': 3}], False),
    ({'cpu': 4}, [], True),
    ({}, [], False),
    ({}, [{}], False),
    ({'cpu': 0}, [], False),
    ({'cpu': 0, 'mem': 1}, [{'cpu': 0}], True),
    ({'cpu': 4}, [{'gpu': 1}], False),
    ({'cpu': 4}, [{'gpu': 0}], True),
    ({'cpu': 1.5}, [{'cpu': 0.5}, {'cpu': 0.5}], True),
    ({'cpu': 1.5}, [{'cpu': 0.5}, {'cpu': 1.0}], False),
    ({'cpu': 10 ** 500}, [{'cpu': 10 ** 500 - 1}], True),
]
for resources, requests, expected in cases:
    original = copy.deepcopy((resources, requests))
    result = is_allocation_feasible(resources, requests)
    assert type(result) is bool
    assert result is expected, (resources, requests, result, expected)
    assert (resources, requests) == original

# Exhaustive small nonnegative integer cases, including an unavailable resource.
count = 0
for cpu, mem, cpu1, cpu2, mem1, mem2, gpu in itertools.product(range(3), repeat=7):
    resources = {'cpu': cpu, 'mem': mem}
    requests = [{'cpu': cpu1, 'mem': mem1}, {'cpu': cpu2, 'mem': mem2, 'gpu': gpu}]
    expected = (gpu == 0 and cpu1 + cpu2 <= cpu and mem1 + mem2 <= mem
                and (cpu1 + cpu2 < cpu or mem1 + mem2 < mem))
    assert is_allocation_feasible(resources, requests) is expected
    assert is_allocation_feasible(resources, list(reversed(requests))) is expected
    count += 1

print(f'Passed {len(cases)} targeted cases and {count} exhaustive cases (both request orders).')
