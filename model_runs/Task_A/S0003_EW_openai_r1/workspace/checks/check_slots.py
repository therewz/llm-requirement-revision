import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import suggest_slots

for day in ('Friday', 'friday', 'FRIDAY', '2026-02-13'):
    slots = suggest_slots([], 30, day)
    assert slots == suggest_slots([], 30, 'Monday')
    assert '15:15' in slots
    assert '16:30' in slots
    assert '16:45' not in slots
    assert all(not ('12:00' <= t < '13:00') for t in slots)
    assert slots[0] == '09:00'
    assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 30, day) == []
    late_slots = suggest_slots([{'start': '09:00', 'end': '15:15'}], 30, day)
    assert late_slots == ['15:15', '15:30', '15:45', '16:00', '16:15', '16:30']
    assert suggest_slots([], 0, day) == []
    assert suggest_slots([], 481, day) == []

print('All checks passed.')
