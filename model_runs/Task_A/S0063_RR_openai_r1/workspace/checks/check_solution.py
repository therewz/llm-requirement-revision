import sys
from pathlib import Path
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import suggest_slots


def hm(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


thursday = "2024-02-01"
friday = "2024-02-02"
slots = suggest_slots([], 30, thursday)
assert slots == [hm(t) for t in range(540, 991, 15)
                 if t + 30 <= 720 or t >= 780]
assert "11:30" in slots and "13:00" in slots and "16:30" in slots
assert suggest_slots([], 30, friday)[-1] == "15:00"
assert suggest_slots([], 30, friday, True) == suggest_slots([], 30, friday)
assert "15:00" in suggest_slots([], 120, friday)
assert "15:00" not in suggest_slots([], 121, friday)
assert "16:45" in suggest_slots([], 15, thursday)
assert "11:15" in suggest_slots([], 45, thursday)
assert "11:30" not in suggest_slots([], 45, thursday)
assert "09:00" in suggest_slots([{"start": "09:30", "end": "10:00"}], 30, thursday)
assert "10:00" in suggest_slots([{"start": "09:30", "end": "10:00"}], 30, thursday)
assert "09:00" in suggest_slots([{"start": "08:00", "end": "09:00"}], 30, thursday)
assert "16:30" in suggest_slots([{"start": "17:00", "end": "18:00"}], 30, thursday)
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 30, thursday) == []
assert suggest_slots([], 241, thursday) == []
assert suggest_slots([], 0, thursday) == []

rng = Random(63)
for _ in range(200):
    intervals = []
    for _ in range(rng.randrange(8)):
        start = rng.randrange(0, 1439)
        intervals.append((start, rng.randrange(start + 1, 1440)))
    duration = rng.randrange(1, 501)
    is_friday = rng.choice([False, True])
    events = [{"start": hm(a), "end": hm(b)} for a, b in intervals]
    expected = [hm(t) for t in range(540, 1020, 15)
                if t + duration <= 1020 and (not is_friday or t <= 900)
                and all(t + duration <= a or t >= b
                        for a, b in intervals + [(720, 780)])]
    assert suggest_slots(events, duration, friday if is_friday else thursday, True) == expected

print("All checks passed (including 200 randomized cases).")
