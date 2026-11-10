import importlib.util
import random
from pathlib import Path

spec = importlib.util.spec_from_file_location('solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest = solution.suggest_slots
fmt = solution.minutes_to_time

friday = '2026-02-06'
monday = '2026-02-09'
assert suggest([], 30, friday) == suggest([], 30, monday)
assert '16:30' in suggest([], 30, friday)
assert '16:45' in suggest([], 1, friday)
assert '11:45' in suggest([], 45, friday)
assert '12:00' not in suggest([], 15, friday)
assert '12:45' not in suggest([], 15, friday)
assert '13:00' in suggest([], 15, friday)
assert suggest([], 480, friday) == ['09:00']
assert suggest([], 481, friday) == []
assert suggest([{'start': '9:00', 'end': '17:00'}], 1, friday) == []
assert '10:00' in suggest([{'start': '09:00', 'end': '10:00'}], 15, friday)
assert '09:45' in suggest([{'start': '10:00', 'end': '11:00'}], 15, friday)
assert suggest([{'start': '02:00', 'end': '09:00'}, {'start': '17:00', 'end': '23:00'}], 17, friday) == suggest([], 17, friday)
for duration in (0, -1, 1.5, 30.0, '30', True, False, None):
    try:
        suggest([], duration, friday)
    except ValueError:
        pass
    else:
        raise AssertionError(f'Accepted invalid duration: {duration!r}')

# Compare interval-skipping implementation with exhaustive grid enumeration.
rng = random.Random(62)
for _ in range(1000):
    intervals = []
    for _ in range(rng.randrange(12)):
        start = rng.randrange(1439)
        end = rng.randrange(start + 1, 1440)
        intervals.append((start, end))
    events = [{'start': fmt(start), 'end': fmt(end)} for start, end in intervals]
    duration = rng.randrange(1, 550)
    expected = [
        fmt(start)
        for start in range(540, 1020, 15)
        if start + duration <= 1020
        and not 720 <= start < 780
        and not any(start < end and start + duration > begin for begin, end in intervals)
    ]
    assert suggest(events, duration, friday) == expected
print('All checks passed (including 1,000 randomized schedules).')
