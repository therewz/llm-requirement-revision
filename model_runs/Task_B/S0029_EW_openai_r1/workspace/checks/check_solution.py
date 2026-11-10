import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'src' / 'solution.py'
spec = importlib.util.spec_from_file_location('solution', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

cases = [
    ({'CPU': 10, 'RAM': 30}, [{'CPU': 5, 'RAM': 10}, {'RAM': 15}], True),
    ({'CPU': 10}, [{'CPU': 5}], True),
    ({'RAM': 30}, [{'RAM': 10}, {'RAM': 15}, {'RAM': 10}], False),
    ({'disk': 5.0}, [{'disk': 2.5}, {'disk': 2.5}], True),
    ({'CPU': 10}, [{'GPU': 1}], False),
    ({'CPU': 10, 'RAM': 30}, [{'CPU': 10, 'RAM': 30}], True),
    ({}, [], True),
    ({}, [{'CPU': 1}], False),
    ({'CPU': 0}, [], True),
    ({'CPU': 0}, [{'CPU': 0}], True),
    ({'CPU': 0}, [{'GPU': 0}], False),
    ({'CPU': 2 ** 60}, [{'CPU': 2 ** 60 + 1}], False),
    ({'CPU': 10 ** 400}, [{'CPU': 10 ** 400}], True),
]
for resources, requests, expected in cases:
    original_resources = resources.copy()
    original_requests = [request.copy() for request in requests]
    assert feasible(resources, requests) is expected, (resources, requests, expected)
    assert resources == original_resources
    assert requests == original_requests

for bad in [-1, float('nan'), float('inf'), '10', True, None]:
    for resources, requests in [
        ({'CPU': bad}, []),
        ({'CPU': 10}, [{'CPU': bad}]),
        ({'CPU': 0}, [{'CPU': 1}, {'GPU': bad}]),
    ]:
        try:
            feasible(resources, requests)
        except ValueError:
            pass
        else:
            raise AssertionError(('expected ValueError', resources, requests))

print('All allocation checks passed.')
