import random
import runpy

suggest_slots = runpy.run_path('src/solution.py')['suggest_slots']

slots = suggest_slots([], 30, 'Monday')
assert len(slots) == 451
assert slots[:2] == ['09:00', '09:01']
assert slots[-1] == '16:30'
assert '12:00' in slots
assert suggest_slots([], 30, 'Friday') == slots
assert suggest_slots([], 30, '2026-07-03') == slots
assert suggest_slots([], 480, 'Monday') == ['09:00']
for duration in (0, -1, 481, 30.5, None):
    assert suggest_slots([], duration, 'Monday') == []

busy = [{'start': '10:00', 'end': '11:00'}]
slots = suggest_slots(busy, 30, 'Monday')
assert '09:30' in slots
assert '09:31' not in slots
assert '10:59' not in slots
assert '11:00' in slots
assert suggest_slots([{'start': '08:00', 'end': '18:00'}], 1, 'Monday') == []
assert suggest_slots([
    {'start': '13:00', 'end': '17:00'},
    {'start': '09:00', 'end': '12:00'},
    {'start': '11:00', 'end': '13:00'},
], 1, 'Monday') == []
assert suggest_slots([
    {'start': '08:00', 'end': '09:00'},
    {'start': '17:00', 'end': '18:00'},
], 480, 'Monday') == ['09:00']

rng = random.Random(0)
for _ in range(100):
    intervals = []
    events = []
    for _ in range(rng.randrange(12)):
        start = rng.randrange(8 * 60, 18 * 60)
        end = start + rng.randrange(1, 121)
        intervals.append((start, end))
        events.append({'start': f'{start // 60:02d}:{start % 60:02d}',
                       'end': f'{end // 60:02d}:{end % 60:02d}'})
    duration = rng.randrange(1, 500)
    expected = [f'{t // 60:02d}:{t % 60:02d}'
                for t in range(540, 1020 - duration + 1)
                if all(t + duration <= s or t >= e for s, e in intervals)]
    assert suggest_slots(events, duration, 'Friday') == expected
print('All checks passed.')
