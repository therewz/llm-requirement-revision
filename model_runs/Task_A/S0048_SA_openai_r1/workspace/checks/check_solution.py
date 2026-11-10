import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from solution import suggest_slots, time_to_minutes, minutes_to_time


def expected(events, duration):
    busy = [(720, 780)] + [
        (time_to_minutes(e['start']) - 15, time_to_minutes(e['end']) + 15)
        for e in events
    ]
    return [
        minutes_to_time(t)
        for t in range(540, 1020, 15)
        if t + duration <= 1020
        and all(t + duration <= start or t >= end for start, end in busy)
    ]


for day in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'):
    for duration in (1, 15, 20, 30, 60, 180, 240, 241, 480, 481, 1000):
        assert suggest_slots([], duration, day) == expected([], duration)

slots = suggest_slots([], 30, 'Fri')
assert '16:30' in slots
assert '11:30' in slots and '11:45' not in slots
assert '12:00' not in slots and '12:45' not in slots and '13:00' in slots
assert suggest_slots([], 481, 'Mon') == []
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 15, 'Mon') == []

cases = [
    [{'start': '10:00', 'end': '11:00'}, {'start': '10:30', 'end': '11:30'}],
    [{'start': '18:00', 'end': '19:00'}],
    [{'start': '06:00', 'end': '07:00'}],
    [{'start': '08:30', 'end': '09:05'}, {'start': '16:55', 'end': '18:00'}],
    [{'start': '10:07', 'end': '10:23'}],
]
for events in cases:
    before = [dict(e) for e in events]
    for duration in (1, 17, 30, 90, 500):
        assert suggest_slots(events, duration, 'Wed') == expected(events, duration)
    assert events == before

slots = suggest_slots([{'start': '10:00', 'end': '11:00'}], 30, 'Mon')
assert '09:15' in slots and '09:30' not in slots
assert '11:00' not in slots and '11:15' in slots

for invalid in (0, -15, 1.5, '30', True, None):
    try:
        suggest_slots([], invalid, 'Mon')
    except ValueError:
        pass
    else:
        raise AssertionError(f'Accepted invalid duration {invalid!r}')

rng = random.Random(2025)
for _ in range(1000):
    events = []
    for _ in range(rng.randrange(10)):
        start = rng.randrange(1439)
        end = rng.randrange(start + 1, 1440)
        events.append({'start': minutes_to_time(start), 'end': minutes_to_time(end)})
    duration = rng.randrange(1, 600)
    assert suggest_slots(events, duration, 'Fri') == expected(events, duration)

print('All slot checks passed (including 1,000 randomized cases).')
