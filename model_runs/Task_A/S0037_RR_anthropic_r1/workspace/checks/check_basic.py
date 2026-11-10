import sys
sys.path.insert(0, "src")
from solution import suggest_slots

r = suggest_slots([], 60, "2024-06-03")  # Monday
print(r)
assert r[0] == "09:00" and r[-1] == "16:00" and "12:00" not in r and "12:45" not in r and "13:00" in r
f = suggest_slots([], 60, "2024-06-07")  # Friday
print(f)
assert f[-1] == "15:00"
assert suggest_slots([], 30, "Fri")[-1] == "15:00"
e = suggest_slots([{"start": "09:00", "end": "10:00"}], 30, "Mon")
assert e[0] == "10:15", e
assert all(int(t[3:]) % 15 == 0 for t in suggest_slots([], 20, "Mon"))
print("ok")
