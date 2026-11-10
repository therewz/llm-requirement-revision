import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def time_str(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


empty_day = suggest_slots([], 30, 'Monday')
assert len(empty_day) == 451
assert empty_day[0] == '09:00' and empty_day[-1] == '16:30'
assert '09:01' in empty_day and '12:00' in empty_day
assert suggest_slots([], 30, 'Friday') == empty_day
assert suggest_slots([], 30, '2026-04-10') == empty_day
assert suggest_slots([], 480, 'Monday') == ['09:00']
for duration in (0, -1, 481):
    assert suggest_slots([], duration, 'Monday') == []
assert suggest_slots([{'start': '08:00', 'end': '18:00'}], 1, 'Monday') == []

# The meeting may touch event boundaries, but must not overlap them.
events = [{'start': '09:30', 'end': '10:07'}]
slots = suggest_slots(events, 30, 'Monday')
assert slots[0] == '09:00' and slots[1] == '10:07'
assert events == [{'start': '09:30', 'end': '10:07'}]

# Compare against a direct minute-by-minute oracle, including overlapping,
# unsorted, out-of-hours, and empty events.
rng = random.Random(0)
for _ in range(200):
    intervals = []
    for _ in range(rng.randrange(15)):
        start = rng.randrange(0, 1440)
        end = rng.randrange(start, 1440)
        intervals.append((start, end))
    rng.shuffle(intervals)
    events = [{'start': time_str(s), 'end': time_str(e)} for s, e in intervals]
    duration = rng.randrange(1, 501)
    expected = [
        time_str(start)
        for start in range(540, 1020 - duration + 1)
        if all(end <= start or begin >= start + duration
               for begin, end in intervals if begin < end)
    ]
    assert suggest_slots(events, duration, 'Friday') == expected

print('All checks passed.')
