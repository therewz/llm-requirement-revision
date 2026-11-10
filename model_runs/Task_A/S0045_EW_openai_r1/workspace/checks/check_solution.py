import itertools
import runpy

solution = runpy.run_path('src/solution.py')
suggest_slots = solution['suggest_slots']
to_minutes = solution['time_to_minutes']
to_time = solution['minutes_to_time']

friday = '2026-02-06'
thursday = '2026-02-05'
assert suggest_slots([], 45, friday)[0] == '09:00'
assert suggest_slots([], 30, friday) == suggest_slots([], 30, thursday)
assert '15:15' in suggest_slots([], 30, friday)
assert '16:30' in suggest_slots([], 30, friday)
assert '16:00' in suggest_slots([], 60, friday)
assert '16:15' not in suggest_slots([], 60, friday)
assert '16:45' in suggest_slots([], 10, 'Friday')
assert suggest_slots([], 30, 'Friday') == suggest_slots([], 30, friday)
assert suggest_slots([], 500, friday) == []
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 15, friday) == []

lunch_slots = suggest_slots([], 15, friday)
assert all(not 720 <= to_minutes(t) < 780 for t in lunch_slots)
assert '11:45' in lunch_slots
assert '13:00' in lunch_slots
assert '11:30' not in suggest_slots([], 45, friday)

events = [
    {'start': '14:00', 'end': '15:00'},
    {'start': '10:00', 'end': '10:45'},
    {'start': '10:30', 'end': '11:00'},
    {'start': '07:00', 'end': '08:00'},
    {'start': '18:00', 'end': '19:00'},
]
slots = suggest_slots(events, 30, friday)
assert '13:30' in slots
assert '15:00' in slots
assert '11:00' in slots
assert all(not (to_minutes(t) < 900 and to_minutes(t) + 30 > 840) for t in slots)
for order in itertools.permutations(events):
    assert suggest_slots(list(order), 30, friday) == slots

# Compare to a direct half-open interval model across positive durations.
for duration in (1, 10, 15, 17, 30, 45, 60, 180, 240, 241, 480):
    expected = []
    blocked = [(to_minutes(e['start']), to_minutes(e['end'])) for e in events]
    blocked.append((720, 780))
    for start in range(540, 1020, 15):
        end = start + duration
        if end <= 1020 and all(end <= a or start >= b for a, b in blocked):
            expected.append(to_time(start))
    assert suggest_slots(events, duration, friday) == expected

for duration in (0, -15):
    try:
        suggest_slots([], duration, friday)
    except ValueError:
        pass
    else:
        raise AssertionError('Nonpositive duration accepted')

print('All slot checks passed.')
