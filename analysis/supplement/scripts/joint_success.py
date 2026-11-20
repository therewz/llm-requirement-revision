"""Reconstruct the primary SA/EW joint outcomes from saved evidence only."""

import argparse
import csv
import hashlib
import io
import itertools
import json
import math
import re
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_PACKAGE = HERE.parents[2]
MAIN = "primary69__main"
ARMS = ("SA", "EW")
TASKS = ("A", "B")
PROVIDERS = ("openai", "anthropic")
CELLS = ("both", "restoration_only", "preservation_only", "neither", "unassessable")
PAIR_GROUPS = {("A", "openai"): 35, ("A", "anthropic"): 35,
               ("B", "openai"): 34, ("B", "anthropic"): 34}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def indexed(rows, key):
    result = {}
    for row in rows:
        value = key(row)
        require(value not in result, f"Duplicate row: {value}")
        result[value] = row
    return result


class Evidence:
    def __init__(self, root):
        self.root = root.resolve()
        self.digests = {}
        self.manifest = self.json("metadata/descriptive_source_manifest.json")
        self.paths = self.json("metadata/source_map.json")

    def read(self, path, expected=None):
        absolute = (self.root / path).resolve()
        require(absolute.is_relative_to(self.root), f"Path outside package: {path}")
        data = absolute.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if expected is not None:
            require(digest == expected, f"Hash mismatch: {path}")
        self.digests[str(path)] = digest
        return data

    def json(self, path, expected=None):
        return json.loads(self.read(path, expected))

    def original(self, historical):
        return self.json(self.paths[historical], self.manifest["inputs"][historical])

    def table(self, name):
        data = self.read(f"analysis/descriptive/{name}", self.manifest["outputs"][name])
        return list(csv.DictReader(io.StringIO(data.decode("utf-8"), newline="")))


def time_slots(observation):
    if not observation or (observation.get("kind"), observation.get("type")) != ("ret", "list_str"):
        return None
    values = observation.get("value")
    if isinstance(values, list) and all(
        isinstance(slot, str) and re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", slot) for slot in values
    ):
        return set(values)
    return None


def bool_value(observation):
    if observation and (observation.get("kind"), observation.get("type")) == ("ret", "bool"):
        value = observation.get("value")
        if type(value) is bool:
            return value
    return None


def linked_ids(case):
    return case.get("control_ids", case.get("linked_controls", []))


def target_evidence(task, case, keys, observations):
    case_id = case["case_id"]
    observation = observations.get(case_id)
    controls = {}
    linked = linked_ids(case)
    require(bool(linked), f"No associated controls: {case_id}")
    if task == "A":
        slots = time_slots(observation)
        targets = set(case["expected"]["withdrawn"]["present"])
        require(targets == set(case["target_slots"]), f"Answer-key target mismatch: {case_id}")
        early = set(case["early_any"])
        require(bool(early), f"No Friday-morning check: {case_id}")
        morning = ("missing" if observation is None else "invalid_target_response" if slots is None
                   else "pass" if early & slots else "fail")
        for control_id in linked:
            response = observations.get(control_id)
            control_slots = time_slots(response)
            controls[control_id] = ("missing" if response is None else
                                   "pass" if control_slots is not None and targets <= control_slots else "fail")
        restored = slots is not None and targets <= slots
    else:
        value = bool_value(observation)
        morning = "not_applicable"
        for control_id in linked:
            response = observations.get(control_id)
            definition = keys[control_id]
            expected = definition["withdrawn_expectation"]
            require(type(expected) is bool and expected is definition["retained_expectation"],
                    f"Unexpected Task B control answer: {control_id}")
            controls[control_id] = "missing" if response is None else "pass" if bool_value(response) is expected else "fail"
        restored = value is case["withdrawn_expectation"]
    return None if observation is None else restored, controls, morning


def joint_cell(restored, preserved):
    if restored is None or preserved is None:
        return "unassessable"
    return { (True, True): "both", (True, False): "restoration_only",
             (False, True): "preservation_only", (False, False): "neither" }[restored, preserved]


def strict_restoration(restored, control_states):
    # A known failure is enough to rule out strict restoration. Missing or
    # invalid target observations remain unknown if no requirement is known to fail.
    if restored is False or "fail" in control_states:
        return False
    if restored is None or {"missing", "invalid_target_response"} & set(control_states):
        return None
    require(all(state in {"pass", "not_applicable"} for state in control_states), "Unknown control state")
    return True


def build(evidence):
    base_path = "runs/cleaned_starts_v1/baseline_manifest.json"
    baseline = indexed(evidence.original(base_path)["records"], lambda row: row["participant_id"])
    selected = {pid: row for pid, row in baseline.items() if row["eligible_case_ids"]}
    membership = indexed((row for row in evidence.table("membership.csv") if row["view"] == MAIN),
                         lambda row: row["participant_id"])
    require(set(membership) == set(baseline) and len(baseline) == 72, "Incomplete membership or baseline")
    require(set(selected) == {pid for pid, row in membership.items() if row["included"] == "True"},
            "Primary cohort differs from baseline eligibility")
    require(Counter(row["task"] for row in selected.values()) == {"A": 35, "B": 34}, "Unexpected cohort")

    keys, key_digests = {}, {}
    for task in TASKS:
        path = f"evaluation/Task_{task}/O1_O2.json"
        keys[task] = indexed(evidence.json(path)["cases"], lambda case: case["case_id"])
        key_digests[task] = evidence.digests[path]
    metrics = indexed((row for row in evidence.table("session_metrics.csv")
                       if row["view"] == MAIN and row["condition"] in ARMS), lambda row: row["session_id"])
    expected_sessions = set(itertools.product(selected, PROVIDERS, ARMS))
    require(set((row["participant_id"], row["provider"], row["condition"]) for row in metrics.values())
            == expected_sessions and len(metrics) == len(expected_sessions), "Incomplete or duplicate primary SA/EW slots")

    raw_core = indexed((row for row in evidence.table("raw_test_outcomes.csv")
                        if row["session_id"] in metrics and row["suite"] == "core28"),
                        lambda row: (row["session_id"], row["test_id"]))
    raw_targets = indexed((row for row in evidence.table("raw_target_outcomes.csv") if row["session_id"] in metrics),
                          lambda row: (row["session_id"], row["case_id"]))
    raw_baseline = indexed((row for row in evidence.table("baseline_test_outcomes.csv")
                            if row["participant_id"] in selected and row["suite"] == "core28"),
                           lambda row: (row["participant_id"], row["test_id"]))

    baseline_passes, baseline_statuses = {}, {}
    for pid, row in selected.items():
        obs = evidence.original(row["baseline_path"])
        require(evidence.digests[evidence.paths[row["baseline_path"]]] == row["baseline_sha256"], f"Baseline digest: {pid}")
        require(obs["source_sha256"] == row["starting_source_sha256"], f"Baseline source: {pid}")
        saved = obs["core28"]["results"]
        status = {name: result[0] for name, result in saved.items()}
        require(obs["evaluation_complete"] and obs["core28"]["complete"] and len(status) == 28
                and set(status.values()) <= {"passed", "failed"}, f"Missing baseline core results: {pid}")
        require(all(raw_baseline[pid, test]["baseline_status"] == value for test, value in status.items()),
                f"Baseline observation vs. CSV mismatch: {pid}")
        baseline_statuses[pid] = status
        baseline_passes[pid] = {name for name, value in status.items() if value == "passed"}
        require(set(row["core_baseline_pass_ids"]) == baseline_passes[pid], f"Baseline passes disagree: {pid}")
        require(set(json.loads(membership[pid]["selected_case_ids"])) == set(row["eligible_case_ids"]),
                f"Cohort eligible IDs disagree: {pid}")

    arms, checks = {}, []
    for sid, metric in sorted(metrics.items()):
        pid, task = metric["participant_id"], metric["task"]
        base, task_keys = selected[pid], keys[task]
        ids = json.loads(metric["selected_case_ids"])
        require(set(ids) == set(base["eligible_case_ids"]) and len(ids) == len(set(ids))
                and base["task"] == task, f"Unexpected target set: {sid}")
        grade_path = metric["grade_path"]
        row = {key: metric[key] for key in ("session_id", "participant_id", "task", "provider", "condition")}
        row.update(grade_path=grade_path, grade_sha256="", core_baseline_passes=len(baseline_passes[pid]),
                   core_passes_lost=None, restored_targets=None, eligible_targets=len(ids),
                   restoration=None, strict_restoration=None, preserved=None,
                   linked_checks_failed=None, linked_checks_missing=None,
                   friday_morning_failed=None, friday_morning_missing=None,
                   friday_morning_invalid_target_response=None)
        exclusions = []
        if not baseline_passes[pid]:
            exclusions.append("no_prior_core_passes")
        if not ids:
            exclusions.append("no_eligible_targets")
        if metric["evaluated"] != "True":
            require(not grade_path, f"Unexpected grade for unevaluated session: {sid}")
            exclusions.append(metric["missing_reason"] or "grade_missing")
        else:
            grade = evidence.original(grade_path)
            row["grade_sha256"] = evidence.digests[evidence.paths[grade_path]]
            for source in (grade["identity"], grade["score"], grade["observations"]):
                require(all(source[key] == row[key] for key in ("session_id", "participant_id", "task", "provider", "condition")),
                        f"Grade identity mismatch: {sid}")
            obs, score = grade["observations"], grade["score"]
            require(score["baseline_source_sha256"] == base["starting_source_sha256"] == metric["source_sha256"],
                    f"Prepared source mismatch: {sid}")
            require(obs["source_sha256"] == grade["binding"]["final_source_sha256"], f"Final source mismatch: {sid}")
            core = {name: result[0] for name, result in obs["core28"]["results"].items()}
            require(set(core) == set(baseline_statuses[pid]) and set(core.values()) <= {"passed", "failed"},
                    f"Incomplete core results: {sid}")
            losses = {name for name in baseline_passes[pid] if core[name] != "passed"}
            require(losses == set(score["core_preservation"]["known_observed_loss_ids"]), f"Grade core loss mismatch: {sid}")
            require(int(metric["core_opportunities"]) == len(baseline_passes[pid]) and int(metric["PF"]) == len(losses),
                    f"Metric core loss mismatch: {sid}")
            for test, revision_status in core.items():
                raw = raw_core[sid, test]
                prior = baseline_statuses[pid][test]
                expected_transition = ("P" if prior == "passed" else "F") + ("P" if revision_status == "passed" else "F")
                require((raw["baseline_status"], raw["revision_status"], raw["transition"], raw["grade_sha256"])
                        == (prior, revision_status, expected_transition, row["grade_sha256"]), f"Raw core row mismatch: {sid}/{test}")
            if not score["core_preservation"]["complete"]:
                exclusions.append("core_results_missing")
            elif baseline_passes[pid]:
                row["preserved"] = not losses
            row["core_passes_lost"] = len(losses)
            target = obs["targets"]
            require(target["answer_key_sha256"] == key_digests[task], f"Answer-key digest mismatch: {sid}")
            targets = indexed(score["withdrawal"]["case_results"], lambda case: case["case_id"])
            require(set(targets) == set(ids), f"Grade target set mismatch: {sid}")
            require({cid for id_ in ids for cid in linked_ids(task_keys[id_])} == set(base["required_linked_controls_after_edit"]),
                    f"Linked-control set mismatch: {sid}")
            control_states, linked_states, morning_states, restorations = [], [], [], []
            for cid in ids:
                stored, raw = targets[cid], raw_targets[sid, cid]
                observed, linked, morning = target_evidence(task, task_keys[cid], task_keys, target["cases"])
                require((stored["status"] == "RESTORED") == (observed is True), f"Saved target predicate mismatch: {sid}/{cid}")
                require(raw["outcome"] == stored["status"] and raw["grade_sha256"] == row["grade_sha256"],
                        f"Raw target grade mismatch: {sid}/{cid}")
                for field in ("controls_ok", "morning_ok"):
                    recorded = stored.get(field)
                    require(raw[field] == ("" if recorded is None else str(recorded)), f"Raw target {field} mismatch: {sid}/{cid}")
                if type(stored.get("controls_ok")) is bool:
                    require(stored["controls_ok"] == all(item == "pass" for item in linked.values()),
                            f"Linked control mismatch: {sid}/{cid}")
                if type(stored.get("morning_ok")) is bool:
                    require(stored["morning_ok"] == (morning == "pass"), f"Friday-morning mismatch: {sid}/{cid}")
                if "control_missing" in stored:
                    require(set(stored["control_missing"]) == {key for key, value in linked.items() if value == "missing"},
                            f"Missing linked controls mismatch: {sid}/{cid}")
                restorations.append(observed)
                linked_states.extend(linked.values())
                morning_states.append(morning)
                control_states.extend([*linked.values(), morning])
                checks.append(dict(session_id=sid, task=task, provider=row["provider"], condition=row["condition"],
                                   case_id=cid, saved_outcome=stored["status"], target_restored=observed,
                                   linked_controls=json.dumps(linked, sort_keys=True), friday_morning=morning))
            if None in restorations or not score["withdrawal"]["complete"]:
                exclusions.append("target_results_missing")
            elif ids:
                row["restoration"] = all(restorations)
                require(int(row["restoration"]) == int(metric["all_target_success"]), f"Metric restoration mismatch: {sid}")
                row["strict_restoration"] = strict_restoration(row["restoration"], control_states)
            row.update(restored_targets=sum(value is True for value in restorations),
                       linked_checks_failed=linked_states.count("fail"), linked_checks_missing=linked_states.count("missing"),
                       friday_morning_failed=morning_states.count("fail"), friday_morning_missing=morning_states.count("missing"),
                       friday_morning_invalid_target_response=morning_states.count("invalid_target_response"))
        row["unassessable_reason"] = ";".join(exclusions)
        row["main_cell"] = "unassessable" if exclusions else joint_cell(row["restoration"], row["preserved"])
        row["strict_cell"] = "unassessable" if exclusions else joint_cell(row["strict_restoration"], row["preserved"])
        key = (pid, row["provider"], row["condition"])
        arms[key] = row
    require(len(raw_core) == 276 * 28 and len(checks) == len(raw_targets) == 1524,
            "Unexpected primary raw record counts")
    return arms, checks


def paired(arms):
    rows = []
    identities = sorted({(row["task"], row["provider"], row["participant_id"]) for row in arms.values()})
    for task, provider, pid in identities:
        sa, ew = (arms[pid, provider, condition] for condition in ARMS)
        for view in ("main", "strict"):
            cell_field = f"{view}_cell"
            reasons = {}
            for case in (sa, ew):
                if case[cell_field] == "unassessable":
                    reasons[case["condition"]] = case["unassessable_reason"] or "strict_controls_unassessable"
            assessable = not reasons
            rows.append(dict(task=task, provider=provider, participant_id=pid, definition=view,
                             assessable=assessable, SA_session=sa["session_id"], EW_session=ew["session_id"],
                             SA_cell=sa[cell_field], EW_cell=ew[cell_field],
                             unassessable_reasons=json.dumps(reasons, sort_keys=True),
                             EW_minus_SA=int(ew[cell_field] == "both") - int(sa[cell_field] == "both") if assessable else None))
    return rows


def summary(pairs):
    result = []
    for view in ("main", "strict"):
        for task, provider in (*PAIR_GROUPS, ("all", "all")):
            rows = [row for row in pairs if row["definition"] == view and
                    (task == "all" or (row["task"], row["provider"]) == (task, provider))]
            assessable = [row for row in rows if row["assessable"]]
            expected = sum(PAIR_GROUPS.values()) if task == "all" else PAIR_GROUPS[task, provider]
            require(len(rows) == expected, f"Wrong pair count for {view}/{task}/{provider}")
            record = dict(definition=view, task=task, provider=provider, expected_pairs=expected,
                          assessable_pairs=len(assessable), unassessable_pairs=expected-len(assessable))
            for arm in ARMS:
                counts = Counter(row[f"{arm}_cell"] for row in assessable)
                for cell in CELLS[:-1]:
                    record[f"{arm}_{cell}"] = counts[cell]
                require(sum(counts.values()) == len(assessable), "Invalid partition")
                record[f"{arm}_joint_percent"] = 100 * counts["both"] / len(assessable) if assessable else None
            direction = Counter(row["EW_minus_SA"] for row in assessable)
            record.update(EW_only_joint=direction[1], SA_only_joint=direction[-1], tied_joint=direction[0],
                          both_arms_joint=sum(r["SA_cell"] == r["EW_cell"] == "both" for r in assessable),
                          neither_arm_joint=sum(r["SA_cell"] != "both" and r["EW_cell"] != "both" for r in assessable),
                          EW_minus_SA_pp=100 * (direction[1]-direction[-1]) / len(assessable) if assessable else None)
            require(record["EW_both"] - record["SA_both"] == direction[1] - direction[-1], "Invalid paired difference")
            result.append(record)
    return result


def verify_summaries(evidence, results):
    arms = indexed((r for r in evidence.table("arm_summary.csv") if r["view"] == MAIN and r["condition"] in ARMS),
                   lambda r: (r["task"], r["provider"], r["condition"]))
    pairs = indexed((r for r in evidence.table("paired_summary.csv")
                     if r["view"] == MAIN and r["contrast"] == "EW minus SA" and r["axis"] == "condition"
                     and r["metric"] == "combined_success"),
                    lambda r: (r["task"], r["context"]))
    for r in results:
        task, provider = r["task"], r["provider"]
        if r["definition"] != "main" or task == "all":
            continue
        pair = pairs[task, provider]
        require((int(pair["n_pairs"]), int(pair["increased"]), int(pair["decreased"]), int(pair["tied"]))
                == (r["assessable_pairs"], r["EW_only_joint"], r["SA_only_joint"], r["tied_joint"]),
                f"Prior paired summary disagrees: {task}/{provider}")
        require(math.isclose(float(pair["difference_percentage_points"]), r["EW_minus_SA_pp"]),
                f"Prior aggregate difference disagrees: {task}/{provider}")
        for arm in ARMS:
            require(int(arms[task, provider, arm]["combined_success_count"]) == r[f"{arm}_both"],
                    f"Prior unpaired joint count disagrees: {task}/{provider}/{arm}")


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--output", type=Path, required=True, help="Create a new output directory")
    options = parser.parse_args()
    evidence = Evidence(options.package)
    arms, checks = build(evidence)
    pairs = paired(arms)
    results = summary(pairs)
    verify_summaries(evidence, results)
    options.output.mkdir(exist_ok=False)
    for name, rows in (("joint_summary.csv", results), ("joint_per_pair.csv", pairs),
                       ("revision_detail.csv", list(arms.values())), ("control_detail.csv", checks)):
        write_csv(options.output / name, rows)
    audit = dict(verified_grades=276, verified_baselines=69, verified_core_test_transitions=276*28,
                 verified_eligible_targets=len(checks), reading="saved_data_only",
                 linked_observations=sum(len(json.loads(r["linked_controls"])) for r in checks),
                 friday_morning_predicates=sum(r["task"] == "A" for r in checks),
                 inputs_sha256=evidence.digests,
                 outputs_sha256={path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in sorted(options.output.glob("*.csv"))})
    (options.output / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    for row in results:
        print(row["definition"], row["task"], row["provider"], row["SA_both"], row["EW_both"], row["assessable_pairs"])


if __name__ == "__main__":
    main()
