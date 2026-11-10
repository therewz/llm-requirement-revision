import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

expected_friday = [f'{minutes // 60:02d}:{minutes % 60:02d}' for minutes in range(540, 901, 15)]
for day in ('Fri', 'Friday', 'friday', 'FRIDAY', ' fri ', '2026-07-17'):
    assert suggest_slots([], 30, day) == expected_friday, day
    assert suggest_slots([], 120, day)[-1] == '15:00', day

for day in ('Mon', 'Monday', '2026-07-16'):
    slots = suggest_slots([], 30, day)
    assert slots[0] == '09:00'
    assert slots[-1] == '16:30'
    assert '15:15' in slots

assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 30, 'Friday') == []
assert suggest_slots([], 481, 'Friday') == []
assert suggest_slots([{'start': '09:00', 'end': '15:00'}], 120, 'Friday') == ['15:00']
assert suggest_slots([{'start': '09:00', 'end': '15:15'}], 30, 'Friday') == []
slots = suggest_slots([{'start': '10:00', 'end': '11:00'}], 30, 'Friday')
assert '09:30' in slots and '11:00' in slots
assert not {'09:45', '10:00', '10:15', '10:30', '10:45'}.intersection(slots)
assert solution.convert_time_to_mins('00:00') == 0
assert solution.convert_time_to_mins('24:00') is False
print('All checks passed.')
