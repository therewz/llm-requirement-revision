import importlib.util
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)


class Clock(datetime):
    current = datetime(2030, 1, 7, 8)  # Monday

    @classmethod
    def now(cls):
        return cls.current


def minutes(value):
    return solution.time_to_minutes(value)


with patch.object(solution, "datetime", Clock):
    slots = solution.suggest_slots([], 30, "2030-01-07")
    assert slots == [solution.minutes_to_time(t) for t in range(540, 991, 15)]
    assert solution.suggest_slots([], 30, "Monday") == slots
    assert solution.suggest_slots([], 30, " monday ") == slots
    assert solution.suggest_slots([], 30, "2030-01-06") == []
    assert solution.suggest_slots([], 481, "2030-01-07") == []
    assert solution.suggest_slots([], 480, "2030-01-07") == ["09:00"]
    assert solution.suggest_slots([], 1, "2030-01-07")[-1] == "16:45"
    assert solution.suggest_slots([], 14, "2030-01-07")[-1] == "16:45"
    assert solution.suggest_slots([], 15, "2030-01-11")[-1] == "16:45"
    assert solution.suggest_slots([], 30, "Friday")[-1] == "16:30"

    events = [
        {"start": "12:00", "end": "13:00"},
        {"start": "09:30", "end": "10:30"},
        {"start": "10:00", "end": "11:00"},
        {"start": "07:30", "end": "08:00"},
        {"start": "18:00", "end": "19:00"},
    ]
    slots = solution.suggest_slots(events, 30, "2030-01-07")
    assert "09:00" in slots and "11:00" in slots and "11:30" in slots
    assert "13:00" in slots
    assert slots == sorted(set(slots))
    for slot in slots:
        start = minutes(slot)
        assert 540 <= start and start + 30 <= 1020
        for event in events:
            assert start + 30 <= minutes(event["start"]) or start >= minutes(event["end"])
    assert solution.suggest_slots(
        [{"start": "08:00", "end": "18:00"}], 30, "Monday"
    ) == []
    assert solution.suggest_slots(
        [{"start": "09:00", "end": "16:50"}], 10, "Monday"
    ) == ["16:50"]

    Clock.current = datetime(2030, 1, 7, 10, 15)
    assert solution.suggest_slots([], 30, "Monday")[0] == "10:15"
    Clock.current = datetime(2030, 1, 7, 10, 15, 0, 1)
    assert solution.suggest_slots([], 30, "Monday")[0] == "10:30"
    Clock.current = datetime(2030, 1, 7, 17)
    assert solution.suggest_slots([], 1, "Monday") == []
    assert solution.suggest_slots([], 30, "2030-01-08")[0] == "09:00"
    Clock.current = datetime(2030, 1, 8, 12)
    assert solution.suggest_slots([], 30, "Monday")[0] == "09:00"

    for duration in (0, -1):
        try:
            solution.suggest_slots([], duration, "Monday")
        except ValueError:
            pass
        else:
            raise AssertionError("Nonpositive duration accepted")
    try:
        solution.suggest_slots([], 30, "not a day")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid day accepted")

print("All meeting-slot checks passed.")
