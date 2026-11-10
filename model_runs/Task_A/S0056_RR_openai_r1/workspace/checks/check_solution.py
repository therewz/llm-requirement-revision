import copy
import random
import runpy

module = runpy.run_path('src/solution.py')
suggest = module['suggest_slots']
format_time = module['minutes_to_time']
parse_time = module['time_to_minutes']

# Friday cutoff is inclusive, including for the existing date input format.
friday = suggest([], 30, 'Friday')
assert '15:00' in friday
assert '15:01' not in friday
assert friday == suggest([], 30, '2024-01-05')
assert friday == suggest([], 30, 'fri')
assert '16:30' in suggest([], 30, 'Monday')
assert suggest([], 30, 'Monday') == suggest([], 30, '2024-01-01')

# No unstated duration, start-grid, or buffer restrictions.
events = [{'start': '09:17', 'end': '10:03'}]
slots = suggest(events, 17, 'Tuesday')
assert '09:00' in slots  # ends exactly at the event start
assert '10:03' in slots  # starts exactly at the event end
assert '10:04' in slots
assert '11:43' in slots  # ends exactly at lunch
assert '11:44' not in slots
assert '12:59' not in slots
assert '13:00' in slots
assert '16:43' in slots
assert '16:44' not in slots

# External events have no effect, while partial intersections still block.
external = [
    {'start': '00:00', 'end': '09:00'},
    {'start': '17:00', 'end': '23:59'},
]
assert suggest(external, 1, 'Wednesday') == suggest([], 1, 'Wednesday')
partial = [{'start': '08:00', 'end': '09:05'},
           {'start': '16:50', 'end': '18:00'}]
assert '09:04' not in suggest(partial, 1, 'Wednesday')
assert '09:05' in suggest(partial, 1, 'Wednesday')
assert '16:49' in suggest(partial, 1, 'Wednesday')
assert '16:50' not in suggest(partial, 1, 'Wednesday')
assert suggest([{'start': '09:00', 'end': '17:00'}], 1, 'Friday') == []
assert suggest([], 241, 'Monday') == []
for duration in (0, -1, 1.5):
    try:
        suggest([], duration, 'Monday')
    except ValueError:
        pass
    else:
        raise AssertionError('Expected invalid duration to be rejected')

# Compare with an independent direct-overlap oracle over varied intervals.
rng = random.Random(56)
for _ in range(200):
    events = []
    for _ in range(rng.randrange(12)):
        start, end = sorted(rng.sample(range(1440), 2))
        events.append({'start': format_time(start), 'end': format_time(end)})
    original = copy.deepcopy(events)
    duration = rng.randrange(1, 501)
    is_friday = rng.choice([True, False])
    day = 'Friday' if is_friday else 'Thursday'
    expected = []
    intervals = [(parse_time(e['start']), parse_time(e['end'])) for e in events]
    intervals.append((720, 780))
    for start in range(540, 1020 - duration + 1):
        if is_friday and start > 900:
            continue
        end = start + duration
        if not any(start < busy_end and end > busy_start
                   for busy_start, busy_end in intervals):
            expected.append(format_time(start))
    assert suggest(events, duration, day) == expected
    assert events == original
    rng.shuffle(events)
    assert suggest(events, duration, day) == expected

print('All scheduling checks passed (including 200 randomized comparisons).')
