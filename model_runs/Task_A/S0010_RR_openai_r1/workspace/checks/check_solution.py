import importlib.util
import random
from datetime import date, timedelta

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def hhmm(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


assert suggest_slots([], 480, 'Monday') == ['09:00']
assert suggest_slots([], 481, 'Monday') == []
assert suggest_slots([], 0, 'Monday') == []
assert suggest_slots([], -1, 'Friday') == []
assert suggest_slots([], 60, 'Monday') == [hhmm(t) for t in range(540, 961)]
assert suggest_slots([], 60, 'Friday') == [hhmm(t) for t in range(540, 901)]
assert '12:00' in suggest_slots([], 60, 'Monday')
assert '15:00' in suggest_slots([], 120, 'Friday')
assert '15:01' not in suggest_slots([], 30, 'Friday')
assert suggest_slots([], 121, 'Friday')[-1] == '14:59'
assert suggest_slots([], 60, '2026-08-14') == suggest_slots([], 60, 'fRiDaY')
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 1, 'Monday') == []
assert suggest_slots([{'start': '09:00', 'end': '15:01'}], 1, 'Friday') == []
assert suggest_slots([{'start': '09:00', 'end': '15:00'}], 120, 'Friday') == ['15:00']
assert suggest_slots([
    {'start': '08:00', 'end': '09:07'},
    {'start': '09:37', 'end': '18:00'},
], 30, 'Monday') == ['09:07']

# Compare merged-interval logic with a direct overlap oracle.
rng = random.Random(1)
for _ in range(300):
    intervals = []
    for _ in range(rng.randrange(12)):
        start = rng.randrange(420, 1140)
        end = start + rng.randrange(1, 180)
        intervals.append((start, end))
    events = [{'start': hhmm(s), 'end': hhmm(e)} for s, e in intervals]
    original = [dict(e) for e in events]
    duration = rng.randrange(1, 550)
    day = rng.choice(['Monday', 'Friday', 'FRIDAY', '2026-08-14', '2026-08-13'])
    friday = day.lower() == 'friday' or day == '2026-08-14'
    expected = [hhmm(t) for t in range(540, 1020 - duration + 1)
                if (not friday or t <= 900)
                and all(t + duration <= s or t >= e for s, e in intervals)]
    actual = suggest_slots(events, duration, day)
    assert actual == expected, (events, duration, day, actual, expected)
    assert events == original

print('All fixed cases and 300 randomized overlap checks passed.')
