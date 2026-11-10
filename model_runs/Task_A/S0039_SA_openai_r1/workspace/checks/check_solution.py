import importlib.util
from pathlib import Path
import random

path = Path(__file__).resolve().parents[1] / 'src' / 'solution.py'
spec = importlib.util.spec_from_file_location('solution', path)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)


def fmt(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def oracle(events, duration):
    if duration <= 0:
        return []
    blocked = [(720, 780)]
    for event in events:
        start = solution.time_to_minutes(event['start'])
        end = solution.time_to_minutes(event['end'])
        if start < end:
            blocked.append((start, end))
    return [fmt(start) for start in range(540, 1020 - duration + 1)
            if all(start + duration <= left or start >= right
                   for left, right in blocked)]


empty = solution.suggest_slots([], 30, 'Mon')
assert empty == oracle([], 30)
assert len(empty) == 362
assert '11:30' in empty and '11:31' not in empty
assert '12:00' not in empty and '13:00' in empty
assert empty[-1] == '16:30'
for day in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'):
    assert solution.suggest_slots([], 30, day) == empty
for duration in (-30, 0):
    assert solution.suggest_slots([], duration, 'Mon') == []
assert solution.suggest_slots([], 241, 'Mon') == []
assert '09:01' in solution.suggest_slots([], 1, 'Mon')

examples = [
    [{'start': '10:00', 'end': '11:00'}],
    [{'start': '00:00', 'end': '08:59'}, {'start': '17:01', 'end': '23:59'}],
    [{'start': '08:00', 'end': '09:07'}, {'start': '16:53', 'end': '19:00'}],
    [{'start': '09:00', 'end': '10:00'}, {'start': '10:00', 'end': '11:00'}],
    [{'start': '00:00', 'end': '23:59'}],
    [{'start': '09:03', 'end': '09:03'}],
    [{'start': '08:00', 'end': '15:00'}, {'start': '10:00', 'end': '11:00'}],
]
for events in examples:
    original = [dict(event) for event in events]
    for duration in (1, 5, 14, 15, 30, 60, 180, 240, 241, 600):
        assert solution.suggest_slots(events, duration, 'Tue') == oracle(events, duration)
    assert events == original

rng = random.Random(39)
for _ in range(300):
    events = []
    for _ in range(rng.randrange(10)):
        start, end = sorted((rng.randrange(1440), rng.randrange(1440)))
        events.append({'start': fmt(start), 'end': fmt(end)})
    duration = rng.randrange(-2, 500)
    assert solution.suggest_slots(events, duration, 'Fri') == oracle(events, duration)

print('All example checks and 300 randomized oracle comparisons passed.')
