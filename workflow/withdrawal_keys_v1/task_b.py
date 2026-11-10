"""Task B answer key for offline baseline and later withdrawal scoring.

This module defines inputs and expected observations. It executes no participant
code. The four primary targets use positive integer capacities and consume every
resource exactly, so the two documented readings of the reserve rule agree.
"""

from copy import deepcopy


SOURCES = {
    "phase_i_task": {
        "path": "runs/author_manuals_review_v1/p1_TaskB_G1B_manual.txt",
        "line": 25,
        "basis": "Determine whether requests can be satisfied given limited capacity.",
    },
    "phase_ii_rule": {
        "path": "runs/author_manuals_review_v1/p2_TaskB_G1B_manual_prt2_v2.txt",
        "line": 24,
        "basis": "At least one resource must remain unallocated; consuming all available resources is invalid.",
    },
    "public_exact_use": {
        "path": "data/raw/history_complete_20261102/lab_templates/B/5f1ad5b/tests/test_solution.py",
        "line": 15,
        "basis": "The distributed example accepts demand 3+4+3 against capacity 10. Used as evaluator evidence only.",
    },
    "supplied_five": {
        "path": "repositories/llm-requirement-revision/Data/test_suits/5_new_req_B_test.py",
        "sha256": "0d75ec77772ecf520b655670999ec617887d0b6de77561c8402c48c1d0535710",
        "basis": "Five supplied retained-rule assertions. Withdrawal answers are documented study reconstructions.",
    },
    "pilot_cases": {
        "path": "repositories/followup-offline-local-v2/withdrawal_preparation/scripts/wcases.py",
        "sha256": "867c2c3b778827e3d74dbdd19c06d8cdfc58f3137e6f17bf2846f55cde78b0aa",
        "line": 33,
        "basis": "Previously specified B-X targets and spare/over-capacity controls, reused without reference to generated outcomes.",
    },
}


def _case(case_id, resources, requests, role, retained, withdrawn, aliases=(),
          controls=(), sources=("phase_i_task", "phase_ii_rule"), **details):
    return {
        "case_id": case_id,
        "function": "is_allocation_feasible",
        "args": [resources, requests],
        "kwargs": {},
        "role": role,
        "retained_expectation": retained,
        "withdrawn_expectation": withdrawn,
        "aliases": list(aliases),
        "linked_controls": list(controls),
        "source_ids": list(sources),
        **details,
    }


def build_manifest():
    """Return a fresh JSON-serializable manifest with one row per unique input."""
    target_sources = ("phase_i_task", "phase_ii_rule", "public_exact_use", "pilot_cases")
    cases = [
        _case("B-X1", {"cpu": 10}, [{"cpu": 10}], "primary_target", False, True,
              aliases=("TC30",), controls=("B-TC31", "B-O1"),
              sources=target_sources + ("supplied_five",)),
        _case("B-X2", {"cpu": 10}, [{"cpu": 4}, {"cpu": 6}], "primary_target", False, True,
              controls=("B-C3", "B-O2"), sources=target_sources),
        _case("B-X3", {"cpu": 10, "ram": 8}, [{"cpu": 10, "ram": 8}],
              "primary_target", False, True, aliases=("TC33",),
              controls=("B-C2", "B-O3"), sources=target_sources + ("supplied_five",)),
        _case("B-X4", {"cpu": 6, "ram": 4}, [{"cpu": 3, "ram": 2}, {"cpu": 3, "ram": 2}],
              "primary_target", False, True, controls=("B-C4", "B-O4"), sources=target_sources),
        _case("B-TC31", {"cpu": 10}, [{"cpu": 9}], "spare_control", True, True,
              aliases=("TC31",), sources=("phase_i_task", "phase_ii_rule", "supplied_five")),
        _case("B-C1", {"cpu": 10}, [{"cpu": 5}], "spare_control", True, True,
              sources=("phase_i_task", "phase_ii_rule", "pilot_cases")),
        _case("B-C2", {"cpu": 10, "ram": 8}, [{"cpu": 5, "ram": 3}],
              "spare_control", True, True, sources=("phase_i_task", "phase_ii_rule", "pilot_cases")),
        _case("B-C3", {"cpu": 10}, [{"cpu": 4}, {"cpu": 5}], "spare_control", True, True,
              sources=("phase_i_task", "phase_ii_rule", "pilot_cases")),
        _case("B-O1", {"cpu": 10}, [{"cpu": 11}], "over_control", False, False,
              sources=("phase_i_task", "pilot_cases")),
        _case("B-O2", {"cpu": 10}, [{"cpu": 6}, {"cpu": 5}], "over_control", False, False,
              sources=("phase_i_task", "pilot_cases")),
        _case("B-O3", {"cpu": 10, "ram": 8}, [{"cpu": 5, "ram": 9}],
              "over_control", False, False, sources=("phase_i_task", "pilot_cases")),
        _case("B-C4", {"cpu": 6, "ram": 4}, [{"cpu": 2, "ram": 1}, {"cpu": 3, "ram": 2}],
              "spare_control", True, True,
              construction="B-X4 companion with demand 5 CPU and 3 RAM, leaving one unit of each resource."),
        _case("B-O4", {"cpu": 6, "ram": 4}, [{"cpu": 4, "ram": 3}, {"cpu": 3, "ram": 2}],
              "over_control", False, False,
              construction="B-X4 companion with demand 7 CPU and 5 RAM, exceeding both capacities by one."),
        _case("B-TC32", {"cpu": 10, "ram": 8}, [{"cpu": 10, "ram": 5}],
              "interpretation_diagnostic", True, True, aliases=("TC32", "B-P1"),
              sources=("phase_i_task", "phase_ii_rule", "supplied_five", "pilot_cases"),
              retained_expectation_by_reading={"any_resource_spare": True, "every_resource_spare": False},
              retained_default_basis="Supplied TC32 expects True under the any-resource reading.",
              primary_exclusion_reason="Retained answer varies with the two documented reserve-rule readings.",
              linked_controls=("B-C2", "B-O3")),
        _case("B-TC22", {"cpu": 0}, [{"cpu": 0}], "zero_capacity_diagnostic", False, True,
              aliases=("TC22",), sources=("phase_i_task", "phase_ii_rule", "supplied_five"),
              withdrawn_assumption="Zero capacity and zero demand are valid nonnegative inputs after the reserve rule is removed.",
              primary_exclusion_reason="The brief task description does not settle the zero-capacity input domain. Report this reconstructed diagnostic separately."),
    ]
    return {
        "schema_version": 1,
        "task": "B",
        "status": "prepared_before_new_baseline_results",
        "answer_provenance": "Retained assertions link to supplied tests and handout. Withdrawal answers are new-study reconstructions from capacity feasibility after removal of the reserve condition.",
        "primary_target_ids": ["B-X1", "B-X2", "B-X3", "B-X4"],
        "supplied_five_mapping": {"TC22": "B-TC22", "TC30": "B-X1", "TC31": "B-TC31", "TC32": "B-TC32", "TC33": "B-X3"},
        "primary_output_policy": "Exact Python bool. Record exceptions, missing runs and invalid return types separately. Never use bool(value).",
        "primary_phase_ii_gate": "Target exactly False and all its linked controls exactly their expected bool. A failed or unavailable control leaves that target ineligible or unassessable as recorded by the caller.",
        "phase_i_flags": "Keep target matches and linked-control matches separately. A True target alone is the draft's affected-case pass, while passing controls additionally supports a historical transition.",
        "tuple_policy": "A two-element tuple with a Boolean first element and dictionary second element can produce a separately labelled native-interface diagnostic matching S0027's declared shape. It cannot satisfy the strict primary gate.",
        "numeric_scope": "Positive integer primary inputs with exact arithmetic. Zero capacity is a separate diagnostic. No fractional reserve assumptions or tolerance are introduced.",
        "sources": deepcopy(SOURCES),
        "cases": cases,
    }


def score_output(case, value):
    """Score a captured return value, without executing code or coercing types."""
    result = {"case_id": case["case_id"], "valid_primary_return": type(value) is bool,
              "retained_match": None, "withdrawn_match": None, "outcome": "invalid_return"}
    if type(value) is not bool:
        if type(value) is tuple and len(value) == 2 and type(value[0]) is bool and type(value[1]) is dict:
            result["tuple_first_boolean_diagnostic"] = {
                "value": value[0],
                "retained_match": value[0] is case["retained_expectation"],
                "withdrawn_match": value[0] is case["withdrawn_expectation"],
            }
        return result
    result["retained_match"] = value is case["retained_expectation"]
    result["withdrawn_match"] = value is case["withdrawn_expectation"]
    if case["role"] == "primary_target":
        result["outcome"] = "retained" if result["retained_match"] else "restored"
    elif case["role"].endswith("_control"):
        result["outcome"] = "control_pass" if result["retained_match"] else "control_fail"
    else:
        result["outcome"] = "diagnostic"
    if "retained_expectation_by_reading" in case:
        result["retained_match_by_reading"] = {
            name: value is expected for name, expected in case["retained_expectation_by_reading"].items()
        }
    return result
