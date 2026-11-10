import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

monday = '2026-06-01'
friday = '2026-06-05'
empty = suggest_slots([], 60, monday)
assert len(empty) == 29
assert empty[0] == '09:00' and empty[-1] == '16:00'
assert '12:00' in empty
assert suggest_slots([], 60, friday) == empty
assert suggest_slots([], 480, friday) == ['09:00']
assert suggest_slots([], 481, monday) == []
assert suggest_slots([], 0, monday) == []
assert suggest_slots([], -10, monday) == []
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 30, monday) == []

slots = suggest_slots([{'start': '10:00', 'end': '11:00'}], 60, monday)
assert '09:00' in slots and '11:00' in slots
assert '09:15' not in slots and '10:45' not in slots
assert suggest_slots([
    {'start': '07:00', 'end': '09:00'},
    {'start': '17:00', 'end': '18:00'},
], 60, monday) == empty

# Compare unsorted, overlapping, and out-of-hours events to a minute-based oracle.
def fmt(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'

rng = random.Random(42)
for _ in range(200):
    ranges = []
    for _ in range(rng.randrange(10)):
        start = rng.randrange(24 * 60 - 1)
        end = rng.randrange(start + 1, 24 * 60)
        ranges.append((start, end))
    duration = rng.randrange(1, 600)
    expected = [
        fmt(start) for start in range(9 * 60, 17 * 60 - duration + 1, 15)
        if not any(start < end and start + duration > begin for begin, end in ranges)
    ]
    events = [{'start': fmt(start), 'end': fmt(end)} for start, end in ranges]
    assert suggest_slots(events, duration, friday) == expected

print('All slot checks passed (including 200 randomized cases).')
