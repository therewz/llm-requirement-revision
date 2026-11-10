import sys
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import suggest_slots


def fmt(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


mon = suggest_slots([], 30, 'Mon')
assert mon[0] == '09:00' and mon[-1] == '16:30'
assert mon == sorted(mon)
assert '11:30' in mon and '11:45' not in mon
assert '12:00' not in mon and '12:45' not in mon and '13:00' in mon
fri = suggest_slots([], 30, 'Fri')
assert fri[-1] == '15:00' and '15:15' not in fri
assert suggest_slots([], 120, 'fri')[-1] == '15:00'
assert suggest_slots([], 121, 'FRI')[-1] == '14:45'
assert suggest_slots([], 30, '2026-01-02') == fri
assert suggest_slots([], 30, '2026-01-05') == mon
slots = suggest_slots([('10:00', '11:00')], 30, 'Mon')
assert '09:30' in slots and '09:45' not in slots
assert '10:45' not in slots and '11:00' in slots
assert slots == suggest_slots([{'start': '10:00', 'end': '11:00'}], 30, 'Mon')
assert suggest_slots([('07:00', '08:00'), ('17:00', '18:00')], 30, 'Mon') == mon
assert suggest_slots([('08:00', '09:30')], 30, 'Mon')[0] == '09:30'
assert suggest_slots([('16:00', '18:00')], 30, 'Mon')[-1] == '15:30'
assert suggest_slots([('08:00', '18:00')], 30, 'Mon') == []
assert suggest_slots([], 241, 'Mon') == []
assert suggest_slots([], 30, 'Sat') == mon

# Compare a range of overlapping, unordered, and out-of-hours events against
# a minute-by-minute occupancy model independent of the interval checks.
rng = random.Random(43)
for _ in range(200):
    events = []
    busy = set(range(12 * 60, 13 * 60))
    for _ in range(rng.randrange(8)):
        start = rng.randrange(0, 1439)
        end = rng.randrange(start + 1, 1440)
        events.append((fmt(start), fmt(end)))
        busy.update(range(start, end))
    duration = rng.randrange(1, 500)
    day = rng.choice(['Mon', 'Fri'])
    expected = [fmt(start) for start in range(540, 1020 - duration + 1, 15)
                if (day != 'Fri' or start <= 900)
                and all(t not in busy for t in range(start, start + duration))]
    assert suggest_slots(events, duration, day) == expected

print('All meeting-slot checks passed.')
