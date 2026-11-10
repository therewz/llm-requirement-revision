import importlib.util
from pathlib import Path
import random

spec = importlib.util.spec_from_file_location(
    'solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py'
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def event(start, end):
    return {'event_id': 'test', 'start': solution.minutes_to_time(start),
            'end': solution.minutes_to_time(end)}


def reference(events, duration):
    busy = [(solution.time_to_minutes(e['start']),
             solution.time_to_minutes(e['end'])) for e in events]
    return [solution.minutes_to_time(start)
            for start in range(540, 1020 - duration + 1, 15)
            if not 720 <= start < 780
            and all(not (start < end and start + duration > begin)
                    for begin, end in busy)]


for duration in (1, 7, 15, 29, 30, 31, 45, 60, 240, 480, 481):
    slots = suggest_slots([], duration, '2022-02-01')
    assert slots == reference([], duration)
    assert suggest_slots([], duration, '2022-02-04') == slots

assert '11:45' in suggest_slots([], 60, '2022-02-01')
assert '12:00' not in suggest_slots([], 1, '2022-02-01')
assert '16:45' in suggest_slots([], 15, '2022-02-04')
assert '10:00' in suggest_slots([event(540, 600)], 15, '2022-02-01')
assert '09:00' in suggest_slots([event(570, 600)], 30, '2022-02-01')
assert suggest_slots([event(540, 1020)], 1, '2022-02-01') == []
assert suggest_slots([event(60, 540), event(1020, 1200)], 15, '2022-02-01') == reference([], 15)
assert suggest_slots([{'start': '2:00', 'end': '3:00'}], 15, '2022-02-01') == reference([], 15)

for duration in (0, -1, 1.5, 30.0, True, False, '30', None):
    try:
        suggest_slots([], duration, '2022-02-01')
    except ValueError:
        pass
    else:
        raise AssertionError(f'Accepted invalid duration {duration!r}')

rng = random.Random(62)
for _ in range(1000):
    events = []
    for _ in range(rng.randrange(10)):
        start = rng.randrange(1439)
        end = rng.randrange(start + 1, 1440)
        events.append(event(start, end))
    duration = rng.randrange(1, 550)
    assert suggest_slots(events, duration, '2022-02-04') == reference(events, duration)

print('All checks passed (including 1,000 randomized calendars).')
