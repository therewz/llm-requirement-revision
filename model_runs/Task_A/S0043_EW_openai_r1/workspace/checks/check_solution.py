import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import suggest_slots


def minutes(value):
    h, m = map(int, value.split(':'))
    return 60 * h + m


empty = suggest_slots([], 30, 'Mon')
assert empty[0] == '09:00'
assert empty[-1] == '16:30'
assert empty == sorted(empty)
assert all(minutes(s) % 15 == 0 for s in empty)
assert '11:30' in empty and '13:00' in empty
assert '11:45' not in empty and '12:00' not in empty
assert suggest_slots([], 30, 'Fri') == empty
assert suggest_slots([], 30, '2026-02-20') == empty
assert '15:15' in suggest_slots([], 30, 'Fri')
assert '16:45' in suggest_slots([], 15, 'Fri')

pairs = [('10:00', '11:00')]
dicts = [{'start': '10:00', 'end': '11:00'}]
slots = suggest_slots(pairs, 30, 'Mon')
assert slots == suggest_slots(dicts, 30, 'Mon')
assert '09:30' in slots and '11:00' in slots
assert '09:45' not in slots and '10:45' not in slots
assert suggest_slots([('07:00', '08:00'), ('17:00', '18:00')], 30, 'Mon') == empty
assert suggest_slots([('08:00', '09:30')], 30, 'Mon')[0] == '09:30'
assert suggest_slots([('09:00', '17:00')], 30, 'Fri') == []
assert suggest_slots([], 241, 'Mon') == []
assert suggest_slots([], 240, 'Fri') == ['13:00']
assert suggest_slots([('14:00', '15:00'), ('13:00', '14:30')], 30, 'Fri')[-1] == '16:30'
print('All scheduling checks passed.')
