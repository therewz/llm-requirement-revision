import importlib.util
import itertools
import random
from pathlib import Path

spec = importlib.util.spec_from_file_location('solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

assert suggest_slots([], 45, 'selected day')[0] == '09:00'
assert suggest_slots([], 30, '2026-07-17') == suggest_slots([], 30, '2026-07-16')
assert '16:30' in suggest_slots([], 30, 'Friday')
assert '16:45' not in suggest_slots([], 30, 'Friday')
assert '16:00' in suggest_slots([], 60, 'day')
assert '16:15' not in suggest_slots([], 60, 'day')
assert '09:00' in suggest_slots([], 1, 'day')
assert suggest_slots([], 241, 'day') == []
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 15, 'day') == []
assert all(not ('12:00' <= slot < '13:00') for slot in suggest_slots([], 15, 'day'))
events = [{'start': '14:00', 'end': '15:00'}, {'start': '10:00', 'end': '10:30'}, {'start': '10:15', 'end': '11:00'}]
slots = suggest_slots(events, 30, 'day')
assert '13:30' in slots and '15:00' in slots and '11:00' in slots
assert '13:45' not in slots and '14:00' not in slots and '14:45' not in slots
for order in itertools.permutations(events):
    assert suggest_slots(list(order), 30, 'day') == slots
for duration in (0, -1):
    try:
        suggest_slots([], duration, 'day')
    except ValueError:
        pass
    else:
        raise AssertionError('Nonpositive duration accepted')

# Compare against a direct interval-overlap oracle, including events outside work.
rng = random.Random(42)
for _ in range(500):
    events = []
    for _ in range(rng.randrange(10)):
        start = rng.randrange(1439)
        end = rng.randrange(start + 1, 1440)
        events.append({'start': solution.minutes_to_time(start), 'end': solution.minutes_to_time(end)})
    original = [dict(event) for event in events]
    duration = rng.randrange(1, 600)
    blocked = [(solution.time_to_minutes(e['start']), solution.time_to_minutes(e['end'])) for e in events] + [(720, 780)]
    expected = [solution.minutes_to_time(start) for start in range(540, 1020, 15)
                if start + duration <= 1020 and all(start + duration <= a or start >= b for a, b in blocked)]
    assert suggest_slots(events, duration, 'arbitrary day') == expected
    assert events == original
print('All checks passed (including 500 randomized cases).')
