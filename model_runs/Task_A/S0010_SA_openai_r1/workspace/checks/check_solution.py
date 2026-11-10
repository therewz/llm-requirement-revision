import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def hhmm(t):
    return f'{t // 60:02d}:{t % 60:02d}'


slots = suggest_slots([], 30, 'Monday')
assert slots == [hhmm(t) for t in range(540, 991)]
assert '12:00' in slots and '12:30' in slots
assert suggest_slots([], 30, 'Friday') == slots
assert suggest_slots([], 30, '2026-10-09') == slots
assert suggest_slots([], 480, 'Friday') == ['09:00']
assert suggest_slots([], 481, 'Monday') == []
assert suggest_slots([], 0, 'Monday') == []
assert suggest_slots([], -10, 'Monday') == []
assert suggest_slots([{'start': '08:00', 'end': '18:00'}], 1, 'Monday') == []
assert suggest_slots([
    {'start': '09:00', 'end': '09:07'},
    {'start': '09:37', 'end': '17:00'},
], 30, 'Monday') == ['09:07']
assert suggest_slots([
    {'start': '10:00', 'end': '11:00'},
], 60, 'Monday')[0] == '09:00'
assert '11:00' in suggest_slots([{'start': '10:00', 'end': '11:00'}], 60, 'Monday')

rng = random.Random(0)
for _ in range(300):
    intervals = []
    for _ in range(rng.randrange(12)):
        start = rng.randrange(0, 1440)
        end = rng.randrange(start + 1, 1441)
        intervals.append((start, end))
    duration = rng.randrange(1, 520)
    events = [{'start': hhmm(s), 'end': hhmm(e)} for s, e in intervals]
    expected = [
        hhmm(t) for t in range(540, 1020 - duration + 1)
        if all(t + duration <= s or t >= e for s, e in intervals)
    ]
    assert suggest_slots(events, duration, 'Friday') == expected

print('All checks passed, including 300 randomized interval comparisons.')
