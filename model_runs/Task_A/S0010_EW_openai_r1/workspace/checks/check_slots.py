from pathlib import Path
import importlib.util

path = Path(__file__).resolve().parents[1] / 'src' / 'solution.py'
spec = importlib.util.spec_from_file_location('solution', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suggest_slots = module.suggest_slots

for day in ('Friday', 'friday', 'FRIDAY', '2026-02-06'):
    slots = suggest_slots([], 30, day)
    assert slots == suggest_slots([], 30, 'Monday')
    assert '15:00' in slots
    assert '15:15' in slots
    assert '16:30' in slots
    assert '16:45' not in slots
    assert '11:30' in slots and '11:45' not in slots
    assert '12:00' not in slots and '13:00' in slots

assert suggest_slots([{'start': '09:00', 'end': '16:00'}], 30, 'Friday') == [
    '16:00', '16:15', '16:30'
]
assert suggest_slots([{'start': '08:00', 'end': '18:00'}], 30, 'Friday') == []
assert suggest_slots([], 0, 'Friday') == []
assert suggest_slots([], -15, 'Friday') == []
assert suggest_slots([], 481, 'Friday') == []

# Independently check conflict handling, clipping, alignment and day independence.
events = [
    {'start': '08:00', 'end': '09:10'},
    {'start': '10:30', 'end': '11:15'},
    {'start': '10:45', 'end': '11:45'},
    {'start': '14:10', 'end': '15:20'},
    {'start': '16:45', 'end': '18:00'},
]
busy = [(480, 550), (630, 675), (645, 705), (850, 920), (1005, 1080), (720, 780)]
for duration in (1, 15, 30, 45, 60, 90, 180, 240, 480):
    expected = [
        f'{t // 60:02d}:{t % 60:02d}'
        for t in range(540, 1020 - duration + 1, 15)
        if all(t + duration <= start or t >= end for start, end in busy)
    ]
    for day in ('Monday', 'Friday', '2026-02-06'):
        assert suggest_slots(events, duration, day) == expected

print('All slot checks passed.')
