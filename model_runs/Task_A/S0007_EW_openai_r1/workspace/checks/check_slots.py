import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

friday = '2026-06-12'
monday = '2026-06-15'
slots = suggest_slots([], 30, friday)
assert slots == suggest_slots([], 30, monday)
assert '15:00' in slots and '15:15' in slots and '16:30' in slots
assert '16:45' not in slots
assert '11:30' in slots and '11:45' not in slots
assert '12:00' not in slots and '12:45' not in slots and '13:00' in slots
assert slots[0] == '09:00'

assert suggest_slots([{'start': '09:00', 'end': '16:00'}], 30, friday) == ['16:00', '16:15', '16:30']
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 30, friday) == []
assert suggest_slots([], 481, friday) == []

busy = suggest_slots([{'start': '15:30', 'end': '16:00'}], 30, friday)
assert '15:00' in busy and '16:00' in busy
assert '15:15' not in busy and '15:30' not in busy and '15:45' not in busy
print('All checks passed.')
