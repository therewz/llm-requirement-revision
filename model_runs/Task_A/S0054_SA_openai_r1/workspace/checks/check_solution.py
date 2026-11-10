import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest = solution.suggest_slots
to_time = solution.minutes_to_time
DAY = '2026-07-17'  # Friday must have the same hours as any other day.

assert suggest([], 480, DAY) == ['09:00']
assert suggest([], 481, DAY) == []
assert suggest([], 1441, DAY) == []
assert suggest([], 1, DAY) == [to_time(t) for t in range(540, 1020)]
assert suggest([], 7, DAY)[-1] == '16:53'
assert '12:00' in suggest([], 60, DAY)
assert '16:00' in suggest([], 60, DAY)
assert suggest([], 30, DAY) == suggest([], 30, '2026-07-16')

# Boundary touching and arbitrary-minute starts are allowed.
events = [{'start': '09:07', 'end': '16:53'}]
assert suggest(events, 7, DAY) == ['09:00', '16:53']
# Adjacent, overlapping, nested, out-of-order, and out-of-hours events.
events = [
    {'start': '12:00', 'end': '13:00'},
    {'start': '08:00', 'end': '10:00'},
    {'start': '09:15', 'end': '09:30'},
    {'start': '10:00', 'end': '12:15'},
    {'start': '16:00', 'end': '18:00'},
]
original = [event.copy() for event in events]
assert suggest(events, 180, DAY) == ['13:00']
assert events == original
assert suggest([{'start': '08:00', 'end': '18:00'}], 1, DAY) == []
assert suggest([{'start': '00:00', 'end': '08:59'},
                {'start': '17:00', 'end': '23:59'}], 480, DAY) == ['09:00']

for duration in (0, -1, 1.5, True, '30'):
    try:
        suggest([], duration, DAY)
    except ValueError:
        pass
    else:
        raise AssertionError(duration)
for event in ({'start': '10:00'}, {'start': '10:00', 'end': '10:00'},
              {'start': '11:00', 'end': '10:00'},
              {'start': '25:00', 'end': '26:00'}):
    try:
        suggest([event], 1, DAY)
    except ValueError:
        pass
    else:
        raise AssertionError(event)

rng = random.Random(54)
for _ in range(500):
    intervals = []
    for _ in range(rng.randrange(15)):
        start, end = sorted(rng.sample(range(1440), 2))
        intervals.append((start, end))
    duration = rng.randrange(1, 1500)
    events = [{'start': to_time(start), 'end': to_time(end)}
              for start, end in intervals]
    expected = [to_time(start) for start in range(540, 1020 - duration + 1)
                if all(start + duration <= left or start >= right
                       for left, right in intervals)]
    assert suggest(events, duration, DAY) == expected
print('All checks passed (including 500 randomized comparisons).')
