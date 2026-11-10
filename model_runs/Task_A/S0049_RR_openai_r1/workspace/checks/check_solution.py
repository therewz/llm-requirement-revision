import sys
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import suggest_slots

assert suggest_slots([], 60, 'Monday')[-1] == '18:00'
assert suggest_slots([], 60, 'Friday')[-1] == '15:00'
assert suggest_slots([], 60, '2026-02-06')[-1] == '15:00'
assert suggest_slots([], 60, '2026-02-05')[-1] == '18:00'
assert suggest_slots([], 180, 'Fri')[-1] == '15:00'
assert '11:00' in suggest_slots([], 60, '')
assert '11:15' not in suggest_slots([], 60, '')
assert '12:00' not in suggest_slots([], 60, '')
assert '13:00' in suggest_slots([], 60, '')
for duration in (0, -1, 601, 61.5, '60', None, True):
    assert suggest_slots([], duration, 'Fri') == []
assert suggest_slots([{'start': '09:00', 'end': '19:00'}], 15, 'Mon') == []
assert suggest_slots([{'start': '10:00', 'end': '11:00'}], 15, 'Mon')[4] == '11:15'
ignored = [
    {'start': '08:00', 'end': '09:00'},
    {'start': '19:00', 'end': '20:00'},
    {'start': '10:00', 'end': '10:00'},
    {'start': '14:00', 'end': '13:00'},
]
assert suggest_slots(ignored, 70, 'Mon') == suggest_slots([], 70, 'Mon')
assert suggest_slots([{'start': '08:00', 'end': '09:30'}], 15, 'Mon')[0] == '09:45'

# Independent minute-level occupancy model, including overlapping/unsorted events.
rng = random.Random(49)
for _ in range(100):
    events = []
    blocked = set(range(12 * 60, 13 * 60))
    for _ in range(rng.randrange(12)):
        start, end = rng.randrange(1440), rng.randrange(1440)
        events.append({'start': f'{start // 60:02d}:{start % 60:02d}',
                       'end': f'{end // 60:02d}:{end % 60:02d}'})
        if end > start and end > 540 and start < 1140:
            blocked.update(range(max(start, 540), min(end + 15, 1140)))
    duration = rng.randrange(1, 601)
    for day in ('Mon', 'Fri', '2026-02-06'):
        expected = []
        for start in range(540, 1141 - duration, 15):
            if day != 'Mon' and start > 900:
                continue
            if not blocked.intersection(range(start, start + duration)):
                expected.append(f'{start // 60:02d}:{start % 60:02d}')
        assert suggest_slots(events, duration, day) == expected
        assert suggest_slots(events[::-1], duration, day) == expected
print('All checks passed.')
