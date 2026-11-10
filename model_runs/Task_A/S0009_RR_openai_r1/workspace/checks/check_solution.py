import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import suggest_slots

MONDAY = '2026-06-01'
FRIDAY = '2026-06-05'

monday = suggest_slots([], 30, MONDAY)
assert monday[0] == '09:00'
assert monday[-1] == '16:30'
assert len(monday) == 451
assert '12:00' in monday and '12:59' in monday
assert '09:01' in monday

friday = suggest_slots([], 30, FRIDAY)
assert friday[-1] == '15:00'
assert len(friday) == 361
assert suggest_slots([], 180, FRIDAY)[-1] == '14:00'
assert suggest_slots([], 120, FRIDAY)[-1] == '15:00'

# Event boundaries allow back-to-back meetings, including non-quarter-hour starts.
events = [
    {'start': '12:31', 'end': '17:30'},
    {'start': '08:00', 'end': '12:01'},
]
assert suggest_slots(events, 30, MONDAY) == ['12:01']
assert suggest_slots(events, 31, MONDAY) == []
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 30, FRIDAY) == []
assert suggest_slots([], 481, MONDAY) == []
assert suggest_slots([], 480, FRIDAY) == ['09:00']
assert suggest_slots([], 30, 'not-a-date') == []

# Compare against a direct overlap oracle with unsorted/overlapping/outside events.
events = [
    {'start': '14:50', 'end': '15:03'},
    {'start': '10:07', 'end': '11:11'},
    {'start': '10:30', 'end': '12:02'},
    {'start': '17:30', 'end': '18:00'},
    {'start': '07:00', 'end': '08:30'},
]
def minute(t):
    h, m = map(int, t.split(':'))
    return h * 60 + m

for day in (MONDAY, FRIDAY):
    for duration in (1, 17, 60, 121, 480, 481):
        expected = []
        for start in range(540, 1020 - duration + 1):
            if day == FRIDAY and start > 900:
                continue
            if all(start + duration <= minute(e['start']) or start >= minute(e['end']) for e in events):
                expected.append(f'{start // 60:02d}:{start % 60:02d}')
        assert suggest_slots(events, duration, day) == expected

print('All slot checks passed.')
