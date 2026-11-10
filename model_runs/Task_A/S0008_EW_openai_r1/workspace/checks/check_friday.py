from pathlib import Path
import runpy

suggest_slots = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'src' / 'solution.py'))['suggest_slots']

friday = suggest_slots([], 30, 'Fri')
assert '15:15' in friday
assert '16:30' in friday
assert '16:45' not in friday
assert friday == suggest_slots([], 30, 'Mon')
assert friday == suggest_slots([], 30, '2026-07-17')
assert '11:30' in friday and '12:00' not in friday and '13:00' in friday

# A late Friday slot is available even when the rest of the day is occupied.
late = suggest_slots([{'start': '09:00', 'end': '15:00'}], 30, 'Fri')
assert late and late[0] == '15:15' and late[-1] == '16:30'
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 30, 'Fri') == []
assert suggest_slots([], 0, 'Fri') == []
assert suggest_slots([], 481, 'Fri') == []

# Event conflicts, working hours, and lunch are still enforced.
events = [{'start': '15:30', 'end': '16:00'}]
slots = suggest_slots(events, 30, 'Fri')
assert '15:00' in slots and '16:15' in slots
assert '15:15' not in slots and '15:30' not in slots and '15:45' not in slots
for slot in slots:
    h, m = map(int, slot.split(':'))
    start = h * 60 + m
    end = start + 30
    assert 540 <= start and end <= 1020
    assert end <= 720 or start >= 780
    assert end <= 930 or start >= 960

print('All checks passed.')
