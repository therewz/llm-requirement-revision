import importlib.util
from decimal import Decimal
from fractions import Fraction

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
f = module.is_allocation_feasible

cases = [
    ({'CPU': 10}, [{'CPU': 10}], False),
    ({'CPU': 8}, [{'CPU': 10}], False),
    ({'CPU': 8, 'Memory': 30}, [{'CPU': 8, 'Memory': 32}], False),
    ({'CPU': 10}, [{'CPU': 4}, {'CPU': 5}], True),
    ({'CPU': 10, 'Memory': 30}, [{'CPU': 10}], True),
    ({'CPU': 10, 'Memory': 30}, [{'CPU': 10, 'Memory': 30}], False),
    ({'CPU': 10}, [{'Memory': 0}], False),
    ({'CPU': 10}, [], True),
    ({'CPU': 0}, [], False),
    ({}, [], False),
    ({}, [{}], False),
    ({}, [{'CPU': 1}], False),
    ({'': 2}, [{'': 1}], True),
    ({'CPU': 10 ** 1000}, [{'CPU': 1}], True),
    ({'CPU': float('inf')}, [{'CPU': 1}], True),
    ({'CPU': Decimal('2')}, [{'CPU': Decimal('1')}], True),
    ({'CPU': Fraction(3, 2)}, [{'CPU': Fraction(1, 2)}], True),
]
for resources, requests, expected in cases:
    before_resources = resources.copy()
    before_requests = [r.copy() for r in requests]
    assert f(resources, requests) is expected, (resources, requests, expected)
    assert resources == before_resources and requests == before_requests

for resources, requests, error in [
    ({'CPU': 1}, [[]], ValueError),
    ({'CPU': 1}, [{'missing': 1}, []], ValueError),
    ({'CPU': -1}, [], ValueError),
    ({'CPU': 1}, [{'CPU': -1}], ValueError),
    ({'CPU': '1'}, [], TypeError),
    ({'CPU': 1}, [{'CPU': '1'}], TypeError),
    ({'CPU': float('nan')}, [], ValueError),
]:
    try:
        f(resources, requests)
    except error:
        pass
    else:
        raise AssertionError((resources, requests, error))

print('All 24 checks passed.')
