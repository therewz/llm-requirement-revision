import importlib.util
import random
from pathlib import Path

spec = importlib.util.spec_from_file_location("solution", Path(__file__).resolve().parents[1] / "src" / "solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

slots = suggest_slots([], 30, "Monday")
assert len(slots) == 451
assert slots[0] == "09:00" and slots[-1] == "16:30"
assert "09:01" in slots and "12:00" in slots and "12:59" in slots
for friday in ("Friday", "FRIDAY", "friday", "2026-05-29"):
    slots = suggest_slots([], 30, friday)
    assert slots[-1] == "15:00"
    assert "15:01" not in slots
assert suggest_slots([], 180, "Friday")[-1] == "14:00"
assert suggest_slots([], 120, "Friday")[-1] == "15:00"
assert suggest_slots([], 480, "Monday") == ["09:00"]
for duration in (0, -1, 481, 30.5):
    assert suggest_slots([], duration, "Monday") == []
assert suggest_slots([{"start": "08:00", "end": "18:00"}], 30, "Monday") == []
slots = suggest_slots([{"start": "10:00", "end": "11:00"}], 30, "Monday")
assert "09:30" in slots and "11:00" in slots
assert "09:31" not in slots and "10:59" not in slots
assert suggest_slots([
    {"start": "08:00", "end": "09:07"},
    {"start": "09:37", "end": "18:00"},
], 30, "Monday") == ["09:07"]

rng = random.Random(42)
for _ in range(100):
    intervals = [sorted(rng.sample(range(480, 1081), 2)) for _ in range(rng.randrange(8))]
    events = [{"start": f"{s // 60:02d}:{s % 60:02d}", "end": f"{e // 60:02d}:{e % 60:02d}"} for s, e in intervals]
    duration = rng.randrange(1, 500)
    day = rng.choice(["Monday", "Friday"])
    expected = []
    for start in range(540, 1020 - duration + 1):
        if day == "Friday" and start > 900:
            continue
        if all(start + duration <= s or start >= e for s, e in intervals):
            expected.append(f"{start // 60:02d}:{start % 60:02d}")
    assert suggest_slots(events, duration, day) == expected
print("All checks passed.")
