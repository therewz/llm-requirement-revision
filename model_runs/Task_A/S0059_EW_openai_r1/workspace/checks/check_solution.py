import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def fmt(minute):
    return f'{minute // 60:02d}:{minute % 60:02d}'


assert suggest_slots([], 480, 'Friday') == ['09:00']
assert suggest_slots([], 481, 'Monday') == []
assert suggest_slots([], 30, '2026-02-13') == [fmt(m) for m in range(540, 991)]
assert suggest_slots([], 45, 'any day') == [fmt(m) for m in range(540, 976)]
assert '12:00' in suggest_slots([], 60, '')
assert '16:30' in suggest_slots([], 30, 'Friday')
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 1, 'Monday') == []
assert suggest_slots([
    {'start': '10:17', 'end': '17:00'},
    {'start': '09:00', 'end': '10:10'},
], 7, 'Friday') == ['10:10']
assert suggest_slots([
    {'start': '17:00', 'end': '20:00'},
    {'start': '07:00', 'end': '09:00'},
], 480, 'anything') == ['09:00']

rng = random.Random(59)
for _ in range(250):
    intervals = []
    for _ in range(rng.randrange(15)):
        start = rng.randrange(0, 1439)
        end = rng.randrange(start + 1, 1440)
        intervals.append((start, end))
    rng.shuffle(intervals)
    events = [{'start': fmt(s), 'end': fmt(e)} for s, e in intervals]
    original = [event.copy() for event in events]
    duration = rng.randrange(1, 600)
    expected = [fmt(s) for s in range(540, 1020 - duration + 1)
                if all(s + duration <= a or s >= b for a, b in intervals)]
    assert suggest_slots(events, duration, 'Friday') == expected
    assert suggest_slots(events, duration, 'arbitrary') == expected
    assert events == original

print('All scheduling checks passed.')
