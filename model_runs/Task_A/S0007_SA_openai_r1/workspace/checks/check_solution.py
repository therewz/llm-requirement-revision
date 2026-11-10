import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

friday = '2026-06-12'
slots = suggest_slots([], 30, friday)
assert len(slots) == 451
assert slots[0] == '09:00' and slots[-1] == '16:30'
assert '12:00' in slots and '15:01' in slots
assert suggest_slots([], 480, friday) == ['09:00']
assert suggest_slots([], 481, friday) == []
assert suggest_slots([{'start': '08:00', 'end': '18:00'}], 1, friday) == []
assert suggest_slots([
    {'start': '08:00', 'end': '09:07'},
    {'start': '09:37', 'end': '18:00'},
], 30, friday) == ['09:07']
assert suggest_slots([
    {'start': '10:00', 'end': '11:00'},
    {'start': '10:30', 'end': '12:00'},
], 60, friday) == suggest_slots([
    {'start': '10:00', 'end': '12:00'},
], 60, friday)
assert suggest_slots([], 60, '2026-06-13') == suggest_slots([], 60, friday)

# Compare to a per-minute occupancy model, including out-of-hours events.
rng = random.Random(7)
def fmt(m):
    return f'{m // 60:02d}:{m % 60:02d}'

for _ in range(100):
    intervals = []
    for _ in range(rng.randrange(8)):
        start = rng.randrange(420, 1140)
        end = rng.randrange(start + 1, 1201)
        intervals.append((start, end))
    events = [{'start': fmt(a), 'end': fmt(b)} for a, b in intervals]
    duration = rng.randrange(1, 501)
    busy = {m for a, b in intervals for m in range(a, b)}
    expected = [fmt(t) for t in range(540, 1020 - duration + 1)
                if all(m not in busy for m in range(t, t + duration))]
    assert suggest_slots(events, duration, friday) == expected

print('All checks passed.')
