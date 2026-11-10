"""Task A withdrawal probes and pure classification, prepared before new runs.

The supplied suite is preserved as a historical benchmark. These probes use
selected slot membership to measure the withdrawal itself, so a failing compound
historical assertion is never automatically treated as successful withdrawal.
"""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATHS = {
    "supplied_five": "repositories/llm-requirement-revision/Data/test_suits/5_new_req_A_test.py",
    "pilot_probes": "repositories/followup-offline-local-v2/withdrawal_preparation/scripts/wcases.py",
    "printed_rule": "runs/author_manuals_review_v1/p2_TaskA_G1A_manual_prt2_v2.txt",
    "intended_rule": "handoff/correspondence/messages/20261102_elmira_reply_original_as_relayed.txt",
    "weekday_interface": "data/raw/history_complete_20261102/lab_templates/A/7743e36/src/solution.py",
    "public_baseline": "data/raw/history_complete_20261102/lab_templates/A/4b0dd67/tests/test_solution.py",
}
D30 = ["15:30", "15:45", "16:00", "16:15"]
D60 = ["15:30", "15:45"]
EARLY = ["09:00", "09:15"]


def _probe(case_id, events, duration, day, slots, role, profile, aliases):
    target = role == "target"
    return {
        "case_id": case_id,
        "function": "suggest_slots",
        "args": [deepcopy(events), duration, day],
        "kwargs": {},
        "role": role,
        "profile": profile,
        "source_case_ids": aliases,
        "target_slots": list(slots),
        "early_any": list(EARLY) if target else [],
        "expected": {
            "retained": {"present": [] if target else list(slots), "absent": list(slots) if target else []},
            "withdrawn": {"present": list(slots), "absent": []},
        },
        "control_ids": [],
        "source_ids": ["printed_rule", "intended_rule", "supplied_five", "pilot_probes", "public_baseline"],
    }


def _with_controls(case_id, events, duration, friday, controls, slots, profile, aliases):
    target = _probe(case_id, events, duration, friday, slots, "target", profile, aliases)
    cases = [target]
    for index, control_day in enumerate(controls, 1):
        control_id = f"{case_id}-C{index}"
        target["control_ids"].append(control_id)
        cases.append(_probe(control_id, events, duration, control_day, slots, "control", profile, aliases))
    return cases


def build_manifest():
    """Return runnable probes, expectations, mappings, and source fingerprints.

    ISO target entries identify seven distinct robust withdrawal scenarios.
    Three native profiles contain six each after collapsing the repeated Friday.
    Controls and boundary entries have separate roles and denominators.
    """
    definitions = [
        ("A-F1", [], 30, "2026-03-13", ["2026-03-11", "2026-03-12"], D30, ["supplied:TC9", "pilot:A-F1"]),
        ("A-F2", [], 60, "2026-03-13", ["2026-03-11", "2026-03-12"], D60, ["pilot:A-F2"]),
        ("A-F3", [{"start": "10:00", "end": "11:00"}], 30, "2026-03-13", ["2026-03-11", "2026-03-12"], D30, ["pilot:A-F3"]),
        ("A-F4", [], 30, "2026-03-20", ["2026-03-18", "2026-03-19"], D30, ["pilot:A-F4"]),
        ("A-TC10", [{"start": "14:00", "end": "15:00"}], 30, "2026-03-13", ["2026-03-11", "2026-03-12"], D30, ["supplied:TC10"]),
        ("A-TC22", [{"start": "14:00", "end": "15:30"}], 60, "2026-03-13", ["2026-03-11", "2026-03-12"], ["15:45"], ["supplied:TC22"]),
        ("A-TC24", [{"start": "14:30", "end": "16:00"}], 30, "2026-03-13", ["2026-03-11", "2026-03-12"], ["16:15"], ["supplied:TC24"]),
    ]
    cases = []
    for case_id, events, duration, friday, controls, slots, aliases in definitions:
        cases.extend(_with_controls(case_id, events, duration, friday, controls, slots, "iso_primary", aliases))
    diagnostic = _probe("A-TC11", [], 120, "2026-03-13", ["14:00", "14:15", "14:30"], "boundary_diagnostic", "iso_diagnostic", ["supplied:TC11"])
    diagnostic["expected"] = {
        "retained_intended_finish_by_15": {"present": [], "absent": diagnostic["target_slots"]},
        "retained_printed_start_by_15": {"present": diagnostic["target_slots"], "absent": []},
        "withdrawn": {"present": diagnostic["target_slots"], "absent": []},
    }
    diagnostic["reason"] = "A 120-minute meeting starting after 15:00 exceeds 17:00. Every affected feasible afternoon start depends on the finish-by versus start-by interpretation."
    cases.append(diagnostic)
    native_aliases = {}
    for profile, friday, controls in [
        ("weekday_abbrev", "Fri", ["Wed", "Thu"]),
        ("weekday_full", "Friday", ["Wednesday", "Thursday"]),
        ("weekday_lower", "friday", ["wednesday", "thursday"]),
    ]:
        native_aliases[profile] = {f"{profile}:A-F4": f"{profile}:A-F1"}
        for case_id, events, duration, _, _, slots, aliases in definitions:
            if case_id == "A-F4":
                continue
            aliases = list(aliases)
            if case_id == "A-F1":
                aliases.append("pilot:A-F4:date_collapsed")
            cases.extend(_with_controls(f"{profile}:{case_id}", events, duration, friday, controls, slots, profile, aliases))
    sources = {}
    for source_id, relative_path in SOURCE_PATHS.items():
        sources[source_id] = {"path": relative_path, "sha256": sha256((ROOT / relative_path).read_bytes()).hexdigest()}
    return {
        "schema_version": 1,
        "task": "A",
        "status": "prepared_answer_key_requires_lead_review",
        "generation_used": False,
        "primary_target_ids": [row[0] for row in definitions],
        "profile_priority": ["iso_primary", "weekday_abbrev", "weekday_full", "weekday_lower"],
        "native_aliases": native_aliases,
        "source_counts": {"supplied_scenarios": 5, "pilot_scenarios": 4, "unique_iso_scenarios": 8, "robust_iso_targets": 7, "boundary_only_scenarios": 1},
        "sources": sources,
        "cases": cases,
        "historical_mapping": {
            "TC9": {"probe_id": "A-F1", "original_assertion": "sorted list equals 16 specific starts ending at 14:30", "decision": "Retain historical full-list score separately. Use robust late-slot projection for withdrawal and deduplicate against pilot A-F1."},
            "TC10": {"probe_id": "A-TC10", "original_assertion": "every returned start <=14:00", "decision": "Original comment says 14:30 but code checks 14:00. Empty output passes vacuously. Use selected late slots and positive controls."},
            "TC11": {"probe_id": "A-TC11", "original_assertion": "every returned start <=15:00 and end <=17:00", "decision": "Cannot discriminate literal start-by rule from withdrawal for 120-minute meetings. Intended finish-by reading differs. Keep diagnostic only."},
            "TC22": {"probe_id": "A-TC22", "original_assertion": "every returned start <=14:00", "decision": "Use 15:45, after event end plus 15-minute buffer, finishing at 16:45. Empty output cannot establish eligibility."},
            "TC24": {"probe_id": "A-TC24", "original_assertion": "every returned start <=14:00", "decision": "Original comment says 14:30 but code checks 14:00. Use 16:15, after event end plus 15-minute buffer, finishing at 16:45."},
        },
        "scope": {
            "selection": "Slots start after 15:00 under both disputed rule readings, fit before 17:00, and clear relevant event plus a 15-minute buffer. Morning and matched Wednesday/Thursday controls distinguish a Friday restriction from total failure.",
            "baseline": "The working-hours/grid/buffer conventions are reconstructed benchmark expectations supported by supplied material and inherited pilot probes. Participant prompts are not asserted to state every convention.",
            "historical_oracles": "Full historical Phase-I return lists are not reconstructed here. Only the target membership predicates are fixed.",
            "interface": "ISO dates define the strict primary view. Abbreviated, full and lowercase weekday names define three fixed supplementary profiles. Select once per program using P2 qualified-target evidence, with priority ISO, abbreviation, full, lowercase; use the same profile on P1. Report strict ISO and interface-aware views separately. Native date2 aliases date1, counted once.",
        },
    }


def _slots(observation):
    if not isinstance(observation, dict) or observation.get("kind") != "ret" or observation.get("type") != "list_str":
        return None
    value = observation.get("value")
    if not isinstance(value, list):
        return None
    for slot in value:
        if not isinstance(slot, str) or len(slot) != 5 or slot[2] != ":":
            return None
        hour, minute = slot[:2], slot[3:]
        if not hour.isascii() or not minute.isascii() or not hour.isdigit() or not minute.isdigit():
            return None
        if int(hour) > 23 or int(minute) > 59:
            return None
    return set(value)


def classify(case, observations):
    """Classify a target from normalized runner observations, without executing code.

    observations[id] is {kind: 'ret', type: 'list_str', value: ['HH:MM', ...]}
    or a non-return/error record. A missing record remains MISSING. All-target
    restoration is reported even if unrelated controls fail, with their failures
    recorded separately. Retention needs positive controls and a morning slot.
    """
    if case["role"] != "target":
        raise ValueError("classify accepts target entries only")
    observation = observations.get(case["case_id"])
    base = {"case_id": case["case_id"], "profile": case["profile"], "primary_eligible": False, "profile_eligible": False}
    if observation is None:
        return {**base, "status": "MISSING", "reason": "target observation absent"}
    slots = _slots(observation)
    if slots is None:
        return {**base, "status": "OTHER_FAILURE", "reason": "target did not return a valid list of HH:MM strings"}
    targets = set(case["target_slots"])
    present = sorted(targets & slots)
    controls = {control_id: _slots(observations.get(control_id)) for control_id in case["control_ids"]}
    control_ok = bool(controls) and all(value is not None and targets <= value for value in controls.values())
    early_ok = bool(set(case["early_any"]) & slots)
    evidence = {**base, "target_present": present, "target_absent": sorted(targets - slots), "controls_ok": control_ok, "morning_ok": early_ok, "control_missing": [key for key in controls if observations.get(key) is None]}
    if targets <= slots:
        return {**evidence, "status": "RESTORED", "reason": "all target slots present"}
    if not control_ok or not early_ok:
        return {**evidence, "status": "INDETERMINATE", "reason": "restriction attribution requires both non-Friday controls and a Friday morning slot"}
    if not present:
        return {**evidence, "status": "RETAINED", "primary_eligible": case["profile"] == "iso_primary", "profile_eligible": True, "reason": "target slots absent with valid controls and a morning slot"}
    return {**evidence, "status": "PARTIAL", "reason": "some target slots present with valid controls and a morning slot"}
