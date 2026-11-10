import importlib.util

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

baseline = suggest_slots([], 30, 'Mon')
assert baseline == [
    f'{minute // 60:02d}:{minute % 60:02d}'
    for minute in range(540, 991, 15)
    if minute + 30 <= 720 or minute >= 780
]
assert '11:30' in baseline  # Ending at lunch is allowed.
assert '13:00' in baseline
assert '16:30' in baseline
assert suggest_slots([
    {'start': '00:00', 'end': '09:00'},
    {'start': '17:00', 'end': '23:59'},
], 30, 'Mon') == baseline
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 30, 'Mon') == []
assert suggest_slots([], 241, 'Mon') == []
assert suggest_slots([], 240, 'Mon') == ['13:00']

with_event = suggest_slots([{'start': '10:00', 'end': '11:00'}], 30, 'Mon')
assert '09:30' in with_event  # Ending at an event start is allowed.
assert '11:00' in with_event  # Starting at an event end is allowed.
assert not {'09:45', '10:00', '10:15', '10:30', '10:45'} & set(with_event)
assert suggest_slots([], 30, 'Fri') == [t for t in baseline if t <= '15:00']
assert '15:00' in suggest_slots([], 120, 'Fri')
assert '15:15' not in suggest_slots([], 1, 'Fri')
assert suggest_slots([], 181, 'Fri') == ['13:00', '13:15', '13:30', '13:45']
for day in ('Mon', 'Tue', 'Wed', 'Thu', 'Sat', 'Sun'):
    assert suggest_slots([], 30, day) == baseline

# Check arbitrary positive durations and off-grid, overlapping events against
# a per-minute occupancy reference.
events = [
    {'start': '08:35', 'end': '09:07'},
    {'start': '10:13', 'end': '10:49'},
    {'start': '10:40', 'end': '11:02'},
    {'start': '16:37', 'end': '18:00'},
]
busy_minutes = set(range(720, 780))
for event in events:
    start, end = [int(t[:2]) * 60 + int(t[3:]) for t in event.values()]
    busy_minutes.update(range(start, end))
for day in ('Mon', 'Fri'):
    for duration in (1, 7, 15, 16, 30, 60, 180, 240, 241, 480, 1000):
        expected = []
        for start in range(540, 1020 - duration + 1, 15):
            if day == 'Fri' and start > 900:
                continue
            if not any(m in busy_minutes for m in range(start, start + duration)):
                expected.append(f'{start // 60:02d}:{start % 60:02d}')
        assert suggest_slots(events, duration, day) == expected

print('All meeting-slot checks passed.')
