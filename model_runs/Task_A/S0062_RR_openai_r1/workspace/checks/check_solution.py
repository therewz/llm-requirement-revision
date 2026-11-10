import importlib.util
import random
from datetime import datetime

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest = solution.suggest_slots

monday = '2026-02-02'
friday = '2026-02-06'

for duration in (1, 15, 17, 29, 30, 31, 60, 120, 240, 480, 481):
    slots = suggest([], duration, monday)
    expected = [solution.minutes_to_time(t) for t in range(540, 1020, 15)
                if t + duration <= 1020 and not 720 <= t < 780]
    assert slots == expected, (duration, slots, expected)

for invalid in (0, -1, 1.5, 30.0, '30', None, True, False):
    try:
        suggest([], invalid, monday)
    except ValueError:
        pass
    else:
        raise AssertionError(('invalid duration accepted', invalid))

assert '11:45' in suggest([], 90, monday)
assert '12:00' not in suggest([], 30, monday)
assert '13:00' in suggest([], 30, monday)
assert '15:00' in suggest([], 120, friday)
assert all(t <= '15:00' for t in suggest([], 1, friday))
assert '15:15' in suggest([], 30, monday)
assert '10:00' in suggest([{'start': '09:00', 'end': '10:00'}], 30, monday)
assert '09:00' in suggest([{'start': '09:30', 'end': '10:00'}], 30, monday)
assert suggest([{'start': '02:00', 'end': '09:00'}, {'start': '17:00', 'end': '23:00'}], 30, monday) == suggest([], 30, monday)
assert suggest([{'start': '08:00', 'end': '18:00'}], 1, monday) == []
assert solution.time_to_minutes('2:00') == 120

rng = random.Random(62)
for _ in range(1000):
    intervals = []
    for _ in range(rng.randrange(12)):
        a = rng.randrange(1439)
        b = rng.randrange(a + 1, 1440)
        intervals.append((a, b))
    events = [{'start': solution.minutes_to_time(a), 'end': solution.minutes_to_time(b)} for a, b in intervals]
    day = rng.choice([monday, friday])
    duration = rng.randrange(1, 520)
    expected = []
    for start in range(540, 1020, 15):
        if start + duration > 1020 or 720 <= start < 780:
            continue
        if datetime.strptime(day, '%Y-%m-%d').weekday() == 4 and start > 900:
            continue
        if any(start < b and start + duration > a for a, b in intervals):
            continue
        expected.append(solution.minutes_to_time(start))
    assert suggest(events, duration, day) == expected, (events, duration, day)

print('All checks passed (including 1,000 randomized cases).')
