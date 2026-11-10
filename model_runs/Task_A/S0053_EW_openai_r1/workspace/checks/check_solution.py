import copy
import random
import sys
sys.path.insert(0, '.')
from src.solution import suggest_slots


def minutes(value):
    h, m = map(int, value.split(':'))
    return h * 60 + m


def hhmm(value):
    return f'{value // 60:02d}:{value % 60:02d}'


assert suggest_slots([], 60, 'Fri') == [
    '09:00', '10:00', '11:00', '13:00', '14:00', '15:00', '16:00'
]
assert suggest_slots([], 30, '2026-04-03')[-3:] == ['15:30', '16:00', '16:30']
assert suggest_slots([], 45, 'Mon') == [
    '09:00', '09:45', '10:30', '11:15', '13:00', '13:45', '14:30', '15:15', '16:00'
]
assert suggest_slots([], 240, 'Tue') == ['13:00']
assert suggest_slots([], 241, 'Tue') == []
assert suggest_slots([], 480, 'Tue') == []
assert suggest_slots([], 481, 'Tue') == []
for day in ['Sat', 'Sunday', '2026-04-04', '2026-04-05', 'Holiday', 'public holiday']:
    assert suggest_slots([], 30, day) == []
for duration in [0, -1]:
    try:
        suggest_slots([], duration, 'Mon')
    except ValueError:
        pass
    else:
        raise AssertionError('nonpositive duration accepted')

busy = [{'start': '09:00', 'end': '09:10'}]
assert suggest_slots(busy, 60, 'Mon')[:2] == ['09:10', '10:10']
assert suggest_slots([{'start': '08:00', 'end': '18:00'}], 1, 'Mon') == []
assert suggest_slots([{'start': '10:00', 'end': '11:00'}], 60, 'Mon')[:2] == ['09:00', '11:00']
assert suggest_slots([{'start': '11:30', 'end': '13:30'}], 60, 'Mon') == [
    '09:00', '10:00', '13:30', '14:30', '15:30'
]
base = suggest_slots([], 30, '2026-04-03')
other_day = [
    {'start': '09:00', 'end': '17:00', 'day': 'Thu'},
    {'start': '09:00', 'end': '17:00', 'date': '2026-04-10'},
]
assert suggest_slots(other_day, 30, '2026-04-03') == base
assert suggest_slots([{'start': '09:00', 'end': '17:00', 'day': 'Friday'}], 30, '2026-04-03') == []
assert suggest_slots([{'start': '09:00', 'end': '17:00', 'date': '2026-04-03'}], 30, 'Fri') == []
malformed = [None, 'junk', {}, {'start': 'bad', 'end': '12:00'},
             {'start': '10:00', 'end': '09:00'}, {'start': None, 'end': '17:00'},
             {'start': '25:00', 'end': '17:00'}]
assert suggest_slots(malformed, 30, '2026-04-03') == base

random.seed(53)
for _ in range(300):
    duration = random.randint(1, 500)
    events = []
    intervals = [(720, 780)]
    for _ in range(random.randrange(12)):
        start, end = sorted(random.sample(range(0, 1440), 2))
        events.append({'start': hhmm(start), 'end': hhmm(end)})
        intervals.append((start, end))
    original = copy.deepcopy(events)
    expected = []
    candidate = 540
    while candidate + duration <= 1020:
        if all(candidate + duration <= s or candidate >= e for s, e in intervals):
            expected.append(hhmm(candidate))
            candidate += duration
        else:
            candidate += 1
    actual = suggest_slots(events, duration, 'Fri')
    assert actual == expected, (events, duration, actual, expected)
    assert events == original
print('All targeted and 300 randomized checks passed.')
