import sys
sys.path.insert(0, 'src')
from solution import suggest_slots, _to_minutes, WORK_START, WORK_END

# Fridays use exactly the same availability as every other day.
slots = suggest_slots([], 60, 'Monday')
assert '15:15' in slots and '16:00' in slots
for day in ('Friday', 'Fri', '2026-02-06', '', 'holiday'):
    assert suggest_slots([], 60, day) == slots
assert slots == sorted(set(slots))
assert all(_to_minutes(s) % 15 == 0 for s in slots)
assert all(WORK_START <= _to_minutes(s) and _to_minutes(s) + 60 <= WORK_END for s in slots)
assert all(not (_to_minutes(s) < 13 * 60 and _to_minutes(s) + 60 > 12 * 60) for s in slots)

# Unsorted/overlapping events, invalid intervals, and post-event cooldown.
events = [
    {'start': '14:00', 'end': '14:30'},
    {'start': '09:00', 'end': '10:00'},
    {'start': '09:30', 'end': '10:30'},
    {'start': '11:00', 'end': '10:00'},
    {'start': '19:00', 'end': '20:00'},
]
result = suggest_slots(events, 30, 'Friday')
assert result == suggest_slots(list(reversed(events)), 30, 'Monday')
assert '10:30' not in result and '10:45' in result
assert '14:30' not in result and '14:45' in result
assert suggest_slots([{'start': '00:00', 'end': '23:59'}], 30, 'Friday') == []
for duration in (0, -1, 1000):
    assert suggest_slots([], duration, 'Friday') == []
print('All scheduling checks passed.')
