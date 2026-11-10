import importlib.util
from pathlib import Path
import random

spec = importlib.util.spec_from_file_location(
    'solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py'
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def clock(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def events_for(intervals):
    return [{'start': clock(start), 'end': clock(end)} for start, end in intervals]


assert suggest_slots([], 60, 'Monday') == [clock(t) for t in range(540, 961)]
assert suggest_slots([], 480, 'Monday') == ['09:00']
assert suggest_slots([], 481, 'Monday') == []
assert suggest_slots(events_for([(540, 720), (720, 1020)]), 30, 'Tuesday') == []
assert suggest_slots(events_for([(540, 720), (780, 1020)]), 120, 'Tuesday') == []
assert suggest_slots(events_for([(540, 600), (660, 900)]), 120, 'Tuesday') == ['15:00']
assert suggest_slots(events_for([(540, 600), (600, 617), (647, 1020)]), 30, 'Monday') == ['10:17']
assert '12:00' in suggest_slots([], 60, 'Monday')
assert '11:45' in suggest_slots([], 60, 'Monday')
assert suggest_slots(events_for([(0, 480), (1080, 1200)]), 60, 'Monday') == suggest_slots([], 60, 'Monday')
assert suggest_slots(events_for([(480, 570), (990, 1080)]), 420, 'Monday') == ['09:30']
for day in ['Friday', 'fri', 'FRIDAY', '2026-07-17']:
    assert suggest_slots([], 60, day) == [clock(t) for t in range(540, 901)]
    assert suggest_slots([], 120, day)[-1] == '15:00'
    assert suggest_slots([], 121, day)[-1] == '14:59'
    assert suggest_slots(events_for([(540, 901)]), 30, day) == []
assert suggest_slots([], 45, 'Monday')[-1] == '16:15'
assert suggest_slots([], 1, 'Monday')[-1] == '16:59'
for duration in [0, -1]:
    try:
        suggest_slots([], duration, 'Monday')
    except ValueError:
        pass
    else:
        raise AssertionError('Nonpositive duration was accepted')

rng = random.Random(17)
for _ in range(500):
    points = sorted(rng.sample(range(1440), rng.randrange(0, 12) * 2))
    intervals = list(zip(points[::2], points[1::2]))
    events = events_for(intervals)
    rng.shuffle(events)
    original = [dict(event) for event in events]
    duration = rng.randrange(1, 600)
    is_friday = rng.choice([False, True])
    expected = [
        clock(start)
        for start in range(540, 1020 - duration + 1)
        if (not is_friday or start <= 900)
        and all(start + duration <= a or start >= b for a, b in intervals)
    ]
    assert suggest_slots(events, duration, 'Friday' if is_friday else 'Monday') == expected
    assert events == original

print('All scheduling checks passed, including 500 randomized comparisons.')
