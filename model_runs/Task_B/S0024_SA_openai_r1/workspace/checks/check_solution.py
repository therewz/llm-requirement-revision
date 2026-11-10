import importlib.util
from collections import UserDict
from decimal import Decimal

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible

assert feasible({'cpu': 4}, [{'cpu': 4}])
assert feasible({}, [])
assert feasible({'cpu': 0}, [])
assert feasible({'cpu': 0}, [{'cpu': 0}])
assert feasible({'cpu': 5, 'ram': 8}, [{'cpu': 2, 'ram': 3}, {'cpu': 3, 'ram': 5}])
assert not feasible({'cpu': 4}, [{'cpu': 3}, {'cpu': 2}])
assert not feasible({'cpu': 4}, [{'ram': 1}])
assert feasible({'cpu': 4}, [UserDict({'cpu': 2})])
assert feasible({'cpu': Decimal('1.5')}, [{'cpu': Decimal('1.5')}])
resources = {'cpu': 4}
requests = [{'cpu': 2}, {'cpu': 2}]
assert feasible(resources, requests)
assert resources == {'cpu': 4}
assert requests == [{'cpu': 2}, {'cpu': 2}]
print('All checks passed.')
