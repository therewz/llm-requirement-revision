import random
import runpy

module = runpy.run_path('src/solution.py')
suggest_slots = module['suggest_slots']
format_time = module['minutes_to_time']


def expected_slots(events, duration, day):
    if duration <= 0:
        return []
    blocked = [(720, 780)]
    for event in events:
        start = module['time_to_minutes'](event['start'])
        end = module['time_to_minutes'](event['end'])
        if start < end:
            blocked.append((start, end))
    return [
        format_time(start)
        for start in range(540, 1020, 15)
        if start + duration <= 1020
        and (day != 'Fri' or start <= 900)
        and all(start + duration <= a or start >= b for a, b in blocked)
    ]


for day in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'):
    for duration in (-10, 0, 1, 5, 14, 15, 30, 60, 120, 180, 240, 241, 600):
        assert suggest_slots([], duration, day) == expected_slots([], duration, day)

assert '15:00' in suggest_slots([], 120, 'Fri')
assert '15:15' not in suggest_slots([], 15, 'Fri')
assert '15:15' in suggest_slots([], 15, 'Thu')
assert '15:00' not in suggest_slots([], 121, 'Fri')
assert '11:30' in suggest_slots([], 30, 'Mon')
assert '11:45' not in suggest_slots([], 30, 'Mon')
assert '13:00' in suggest_slots([], 30, 'Mon')

cases = [
    [{'start': '10:00', 'end': '11:00'}],
    [{'start': '00:00', 'end': '08:59'}, {'start': '17:01', 'end': '23:59'}],
    [{'start': '08:30', 'end': '09:20'}, {'start': '16:40', 'end': '18:00'}],
    [{'start': '09:00', 'end': '10:00'}, {'start': '10:00', 'end': '12:00'},
     {'start': '13:00', 'end': '17:00'}],
    [{'start': '10:07', 'end': '10:08'}, {'start': '14:22', 'end': '14:49'}],
    [{'start': '00:00', 'end': '23:59'}],
    [{'start': '10:00', 'end': '10:00'}],
    [{'start': '10:00', 'end': '14:00'}, {'start': '09:30', 'end': '11:30'}],
]
for events in cases:
    original = [event.copy() for event in events]
    for day in ('Mon', 'Fri'):
        for duration in (1, 14, 15, 30, 60, 180, 240):
            assert suggest_slots(events, duration, day) == expected_slots(events, duration, day)
    assert events == original

rng = random.Random(39)
for _ in range(500):
    events = []
    for _ in range(rng.randrange(12)):
        start = rng.randrange(1440)
        end = rng.randrange(start, 1440)
        events.append({'start': format_time(start), 'end': format_time(end)})
    day = rng.choice(('Mon', 'Fri', 'Sun'))
    duration = rng.randrange(-5, 301)
    assert suggest_slots(events, duration, day) == expected_slots(events, duration, day)

print('All slot checks passed, including 500 randomized cases.')
