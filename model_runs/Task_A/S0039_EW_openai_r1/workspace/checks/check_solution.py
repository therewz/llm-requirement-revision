import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import suggest_slots, minutes_to_time


def expected(events, duration):
    if duration <= 0:
        return []
    blocked = [(720, 780)]
    for event in events:
        start, end = event['start'], event['end']
        sh, sm = map(int, start.split(':'))
        eh, em = map(int, end.split(':'))
        blocked.append((sh * 60 + sm, eh * 60 + em))
    return [minutes_to_time(start) for start in range(540, 1020, 15)
            if start + duration <= 1020
            and all(start + duration <= a or start >= b for a, b in blocked)]


assert suggest_slots([], 30, 'Fri') == expected([], 30)
assert '16:30' in suggest_slots([], 30, 'Fri')
assert '15:15' in suggest_slots([], 60, 'Fri')
for day in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'):
    for duration in (-30, 0, 1, 5, 14, 15, 30, 60, 180, 240, 241, 500):
        for events in (
            [],
            [{'start': '10:00', 'end': '11:00'}],
            [{'start': '06:00', 'end': '08:00'}, {'start': '18:00', 'end': '19:00'}],
            [{'start': '08:00', 'end': '09:17'}, {'start': '16:23', 'end': '18:00'}],
            [{'start': '09:00', 'end': '10:00'}, {'start': '10:00', 'end': '17:00'}],
            [{'start': '00:00', 'end': '23:59'}],
        ):
            original = [event.copy() for event in events]
            actual = suggest_slots(events, duration, day)
            assert actual == expected(events, duration), (events, duration, day, actual)
            assert events == original

rng = random.Random(39)
for _ in range(1000):
    events = []
    for _ in range(rng.randrange(10)):
        start, end = sorted(rng.sample(range(1440), 2))
        events.append({'start': minutes_to_time(start), 'end': minutes_to_time(end)})
    duration = rng.randrange(-5, 501)
    assert suggest_slots(events, duration, 'Fri') == expected(events, duration)

print('All fixed and 1,000 randomized slot checks passed.')
