import random
import runpy

solution = runpy.run_path('src/solution.py')
suggest_slots = solution['suggest_slots']
format_time = solution['minutes_to_time']

friday = '2026-07-17'
monday = '2026-07-20'

# Every minute is eligible; the start cutoff is exclusive.
expected = [format_time(m) for m in range(8 * 60, 11 * 60)]
assert suggest_slots([], 1, friday) == expected
assert suggest_slots([], 1, monday) == expected
assert expected[0] == '08:00' and expected[-1] == '10:59'

# Duration is in whole hours, and meetings may span lunch or end at 17:00.
assert suggest_slots([], 9, friday) == ['08:00']
assert suggest_slots([], 10, friday) == []
assert suggest_slots([], 7, friday)[-1] == '10:00'
assert suggest_slots([], 8, monday)[-1] == '09:00'

# Touching intervals do not conflict, and there is no post-event buffer.
assert suggest_slots([{'start': '08:00', 'end': '09:07'}], 1, friday)[0] == '09:07'
assert '08:00' in suggest_slots([{'start': '09:00', 'end': '10:00'}], 1, friday)
assert suggest_slots([{'start': '08:00', 'end': '17:00'}], 1, monday) == []

# Events outside working hours have no effect.
assert suggest_slots([
    {'start': '00:00', 'end': '08:00'},
    {'start': '17:00', 'end': '23:59'},
], 1, friday) == expected

for duration in (0, -1, 1.0, 1.5, True, '1'):
    try:
        suggest_slots([], duration, friday)
    except ValueError:
        pass
    else:
        raise AssertionError(('invalid duration accepted', duration))

try:
    suggest_slots((), 1, friday)
except ValueError:
    pass
else:
    raise AssertionError('non-list accepted')

# Compare merging/clipping against a direct overlap reference.
rng = random.Random(60)
for _ in range(400):
    intervals = []
    for _ in range(rng.randrange(8)):
        start, end = sorted(rng.sample(range(24 * 60), 2))
        intervals.append((start, end))
    duration = rng.randrange(1, 11)
    events = [{'start': format_time(s), 'end': format_time(e)} for s, e in intervals]
    expected_slots = [
        format_time(start)
        for start in range(8 * 60, 11 * 60)
        if start + duration * 60 <= 17 * 60
        and all(start >= end or start + duration * 60 <= begin for begin, end in intervals)
    ]
    assert suggest_slots(events, duration, friday) == expected_slots

print('All scheduling checks passed (including 400 randomized cases).')
