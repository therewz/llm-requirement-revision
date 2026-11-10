import importlib.util

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feasible = module.is_allocation_feasible

assert feasible({'cpu': 0.3}, [{'cpu': 0.1}, {'cpu': 0.2}]) is True
assert feasible({'cpu': 0.3}, [{'cpu': 0.3}, {'cpu': 1e-16}]) is False
assert feasible({'cpu': 0.3}, [{'cpu': 0.4}, {'cpu': -0.1}]) is True
assert feasible({'cpu': 0.3}, [{'cpu': -0.1}, {'cpu': 0.4}]) is True
assert feasible({'cpu': 0.3}, [{'cpu': 0.30000000000000004}]) is False
assert feasible({'cpu': 0.1}, [{'cpu': 10**18}, {'cpu': 0.2}, {'cpu': -10**18}]) is False
print('Passed 6 decimal precision and cancellation checks.')
