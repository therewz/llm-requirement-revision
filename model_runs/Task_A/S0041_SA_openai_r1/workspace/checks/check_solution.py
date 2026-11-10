import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest = solution.suggest_slots

expected = ['09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
            '13:00', '13:30', '14:00', '14:30', '15:00', '15:30', '16:00', '16:30']
assert suggest([], 30, '2026-01-01') == expected
assert suggest([], 1, 'Monday') == expected
assert suggest([], 10, 'Monday') == expected
assert suggest([], 241, 'Monday') == []
assert suggest([{'start': '09:00', 'end': '17:00'}], 30, 'Monday') == []

slots = suggest([{'start': '10:00', 'end': '11:00'}], 30, 'Monday')
assert '09:30' in slots  # Ends exactly when the event begins.
assert '11:00' in slots  # Starts exactly when the event ends.
assert '10:00' not in slots and '10:30' not in slots
assert '11:30' not in suggest([], 60, 'Monday')
assert '11:00' in suggest([], 60, 'Monday')
assert '13:00' in suggest([], 60, 'Monday')

events = [{'start': '10:00', 'end': '11:30'},
          {'start': '09:30', 'end': '10:30'},
          {'start': '11:00', 'end': '13:30'}]
original = [dict(event) for event in events]
assert suggest(events, 30, 'Monday') == suggest(
    [{'start': '09:30', 'end': '13:30'}], 30, 'Monday')
assert events == original
assert suggest([{'start': '00:00', 'end': '09:00'},
                {'start': '17:00', 'end': '23:59'}], 30, 'Monday') == expected

# Compare against a minute-by-minute occupancy oracle on random calendars.
rng = random.Random(42)
for _ in range(300):
    events = []
    occupied = set(range(720, 780))
    for _ in range(rng.randrange(8)):
        start = rng.randrange(1439)
        end = rng.randrange(start + 1, 1440)
        events.append({'start': solution.to_time_str(start),
                       'end': solution.to_time_str(end)})
        occupied.update(range(start, end))
    duration = rng.randrange(1, 600)
    expected = [solution.to_time_str(start)
                for start in range(540, 1020 - duration + 1, 30)
                if not occupied.intersection(range(start, start + duration))]
    assert suggest(events, duration, 'Monday') == expected

for duration in [0, -1]:
    try:
        suggest([], duration, 'Monday')
    except ValueError:
        pass
    else:
        raise AssertionError('Nonpositive duration accepted')

print('All scheduling checks passed.')
