#!/usr/bin/env python3
"""Recompute core-test transitions from recorded baseline and revision outcomes."""
import argparse
from collections import Counter, defaultdict
import csv
from fractions import Fraction
from hashlib import sha256
from io import StringIO
import itertools
import json
from math import isclose
from pathlib import Path
from statistics import median

CORE = 28
TRANSITIONS = ("PP", "PF", "FP", "FF")
VIEW = "primary69__main"
EXTRA_TURN = "S0033_SA_openai_r1"
ARMS = ("RR", "SA", "EW")
TASKS = ("A", "B")
PROVIDERS = ("openai", "anthropic")
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]


def digest(data):
    return sha256(data).hexdigest()


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def csv_rows(data):
    return list(csv.DictReader(StringIO(data.decode("utf-8"), newline="")))


def keyed(rows, fields):
    result = {tuple(row[field] for field in fields): row for row in rows}
    require(len(result) == len(rows), f"Duplicate key in {fields}")
    return result


def numerically_equal(left, right, detail):
    require(isclose(float(left), float(right), rel_tol=0, abs_tol=1e-12), detail)


class SavedEvidence:
    def __init__(self, package):
        self.package = package
        self.manifest = (package / "MANIFEST.json").read_bytes()
        self.files = json.loads(self.manifest)["files"]
        self.checked_files = set()
        self.paths = self.load_json("metadata/source_map.json")

    def checked(self, relative):
        name = str(relative)
        data = (self.package / name).read_bytes()
        record = self.files[name]
        require(
            len(data) == record["bytes"] and digest(data) == record["sha256"],
            f"Package manifest mismatch: {name}",
        )
        self.checked_files.add(name)
        return data

    def load_json(self, relative):
        return json.loads(self.checked(relative))


def suite_statuses(observation, suite_sha, label):
    suite = observation["core28"]
    outcomes = suite["results"]
    require(observation["evaluation_complete"] and suite["complete"], f"Incomplete suite: {label}")
    require(suite["suite_sha256"] == suite_sha, f"Unexpected core test source: {label}")
    require(suite["expected_case_count"] == CORE and len(outcomes) == CORE, f"Wrong suite size: {label}")
    statuses = {test_id: record[0] for test_id, record in outcomes.items()}
    require(set(statuses.values()) <= {"passed", "failed"}, f"Unexpected status: {label}")
    return statuses


def reconstruct(evidence):
    """Read saved observations and derive counts before consulting analysis exports."""
    manifest = evidence.load_json("metadata/baseline_manifest.json")
    programs = keyed(
        csv_rows(evidence.checked("metadata/programs.csv")), ["participant_id"],
    )
    bases = keyed(manifest["records"], ["participant_id"])
    require(bases.keys() == programs.keys() and len(bases) == 72, "Wrong baseline cohort")

    suite_shas = {
        task: digest(evidence.checked(f"evaluation/Task_{task}/T_core.py")) for task in TASKS
    }
    starts = {}
    for (participant,), base in bases.items():
        program = programs[(participant,)]
        expected_inclusion = bool(base["eligible_case_ids"])
        require(
            program["eligible_main69"] == str(expected_inclusion),
            f"Conflicting cohort evidence: {participant}",
        )
        if not expected_inclusion:
            continue
        task = base["task"]
        baseline_path = f"evaluation/Task_{task}/baselines/Repo_V2/{participant}.json"
        baseline_data = evidence.checked(baseline_path)
        require(digest(baseline_data) == base["baseline_sha256"], f"Wrong baseline: {participant}")
        baseline = json.loads(baseline_data)
        require(
            all(baseline[k] == base[k] == program[k] for k in ("participant_id", "task", "group")),
            f"Baseline identity mismatch: {participant}",
        )
        prepared_sha = digest(evidence.checked(program["Repo_V2"]))
        require(
            baseline["source_sha256"] == base["starting_source_sha256"]
            == program["Repo_V2_sha256"] == prepared_sha,
            f"Incorrect prepared source binding: {participant}",
        )
        statuses = suite_statuses(baseline, suite_shas[task], participant)
        require(
            {test for test, status in statuses.items() if status == "passed"}
            == set(base["core_baseline_pass_ids"]),
            f"Wrong baseline pass IDs: {participant}",
        )
        starts[participant] = (base, statuses, baseline_path)
    require(
        Counter(base["task"] for base, _, _ in starts.values()) == {"A": 35, "B": 34},
        "Wrong main cohort",
    )

    all_sessions = csv_rows(evidence.checked("metadata/sessions.csv"))
    require(len(all_sessions) == 432, "Wrong original session inventory")
    keyed(all_sessions, ["session_id"])
    keyed(all_sessions, ["participant_id", "provider", "condition"])
    require(
        all(row["eligible_main69"] == str(row["participant_id"] in starts) for row in all_sessions),
        "Session inventory disagrees with baseline eligibility",
    )
    sessions = [row for row in all_sessions if row["participant_id"] in starts]
    expected = set(itertools.product(starts, PROVIDERS, ARMS))
    require(
        {(row["participant_id"], row["provider"], row["condition"]) for row in sessions} == expected,
        "Incomplete main session grid",
    )

    sessions_out = []
    comparisons = {}
    for session in sorted(sessions, key=lambda row: row["session_id"]):
        sid = session["session_id"]
        participant = session["participant_id"]
        base, before, baseline_path = starts[participant]
        task, provider, condition = (session[key] for key in ("task", "provider", "condition"))
        grade_path = Path(session["evaluation"])
        extra_turn = grade_path.parent.name == "extra_turn"
        require(extra_turn == (sid == EXTRA_TURN), f"Unexpected grade selection: {sid}")
        grade_data = evidence.checked(grade_path)
        grade = json.loads(grade_data)
        identity = {key: session[key] for key in (
            "session_id", "participant_id", "task", "group", "provider", "condition"
        )}
        require(
            all(
                grade["identity"][field] == grade["observations"][field]
                == grade["score"][field] == value
                for field, value in identity.items()
            ),
            f"Revision identity mismatch: {sid}",
        )
        require(session["task"] == base["task"] and session["group"] == base["group"], sid)
        after = suite_statuses(grade["observations"], suite_shas[task], sid)
        require(before.keys() == after.keys(), f"Core test IDs differ: {sid}")
        final_sha = digest(evidence.checked(grade_path.with_name("final.py")))
        require(
            grade["observations"]["source_sha256"] == grade["binding"]["final_source_sha256"] == final_sha
            and grade["score"]["baseline_source_sha256"] == base["starting_source_sha256"],
            f"Wrong baseline/final code binding: {sid}",
        )
        if extra_turn:
            original_final = Path(session["session_dir"]) / "final.py"
            require(
                digest(evidence.checked(original_final)) == final_sha,
                f"Extra-turn artifact changed final code: {sid}",
            )
        changes = {}
        for test_id in before:
            key = ("P" if before[test_id] == "passed" else "F") + (
                "P" if after[test_id] == "passed" else "F"
            )
            changes[test_id] = key
            comparisons[(sid, test_id)] = (before[test_id], after[test_id], key)
        tally = Counter(changes.values())
        baseline_passes = tally["PP"] + tally["PF"]
        score = grade["score"]["core_preservation"]
        require(
            score["complete"]
            and score["opportunity_count"] == baseline_passes
            and score["loss_count"] == tally["PF"]
            and set(score["known_observed_loss_ids"]) == {t for t, v in changes.items() if v == "PF"},
            f"Stored score disagrees with core observations: {sid}",
        )
        sessions_out.append({
            **identity, "used_extra_turn": extra_turn, "core_tests": CORE,
            "prior_passes": baseline_passes, "prior_failures": CORE - baseline_passes,
            **{key: tally[key] for key in TRANSITIONS},
            **{f"{key}_fraction": float(Fraction(tally[key], CORE)) for key in TRANSITIONS},
            "core_loss_rate": float(Fraction(tally["PF"], baseline_passes)) if baseline_passes else None,
            "any_core_loss": int(tally["PF"] > 0) if baseline_passes else None,
            "baseline_path": baseline_path, "baseline_sha256": base["baseline_sha256"],
            "evaluation_path": str(grade_path), "grade_sha256": digest(grade_data),
            "final_source_sha256": final_sha,
        })
    require(len(sessions_out) == 414 and len(comparisons) == 414 * CORE, "Wrong comparison totals")
    return sessions_out, comparisons


def summarize(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["task"], row["provider"], row["condition"])].append(row)
    summary = []
    for task, provider, condition in itertools.product(TASKS, PROVIDERS, ARMS):
        arm = grouped[(task, provider, condition)]
        n = len(arm)
        assessable = [row for row in arm if row["prior_passes"]]
        counts = {key: sum(row[key] for row in arm) for key in TRANSITIONS}
        require(sum(counts.values()) == n * CORE, "Wrong arm core count")
        affected = sum(row["any_core_loss"] for row in assessable)
        losses = [row["PF"] for row in arm]
        mean_loss_rate = (
            sum(Fraction(row["PF"], row["prior_passes"]) for row in assessable) / len(assessable)
            if assessable else None
        )
        summary.append({
            "task": task, "provider": provider, "condition": condition,
            "programs": n, "core_test_records": n * CORE,
            "prior_passes": counts["PP"] + counts["PF"],
            "prior_failures": counts["FP"] + counts["FF"],
            **{f"{key}_count": counts[key] for key in TRANSITIONS},
            **{f"mean_{key}_fraction": float(Fraction(counts[key], n * CORE)) for key in TRANSITIONS},
            "regression_rate_programs": len(assessable),
            "programs_without_prior_passes": n - len(assessable),
            "mean_core_loss_rate": float(mean_loss_rate) if mean_loss_rate is not None else None,
            "programs_with_core_loss": affected,
            "share_with_core_loss": float(Fraction(affected, len(assessable))) if assessable else None,
            "mean_core_losses_per_revision": float(Fraction(counts["PF"], n)),
            "median_core_losses_per_revision": median(losses),
            "min_core_losses_per_revision": min(losses),
            "max_core_losses_per_revision": max(losses),
        })
    return summary


def recovery_pairs(rows):
    pairs = keyed(rows, ["participant_id", "provider", "condition"])
    out = []
    for task, provider in itertools.product(TASKS, PROVIDERS):
        ids = sorted({row["participant_id"] for row in rows if row["task"] == task})
        pairs_here = [(pairs[(pid, provider, "SA")], pairs[(pid, provider, "EW")]) for pid in ids]
        require(all(sa["prior_passes"] == ew["prior_passes"] for sa, ew in pairs_here), "Mismatched baseline")
        n = len(pairs_here)
        sa_count, ew_count = (sum(pair[i]["FP"] for pair in pairs_here) for i in range(2))
        out.append({
            "task": task, "provider": provider, "matched_programs": n,
            "core_test_records_per_arm": n * CORE, "SA_FP": sa_count, "EW_FP": ew_count,
            "SA_mean_FP_fraction": float(Fraction(sa_count, n * CORE)),
            "EW_mean_FP_fraction": float(Fraction(ew_count, n * CORE)),
            "EW_minus_SA_percentage_points": float(Fraction(100 * (ew_count - sa_count), n * CORE)),
        })
    return out


def check_exports(evidence, rows, comparisons, summary):
    """Use saved analysis tables only to cross-check fresh reconstruction."""
    directory = "analysis/descriptive/"
    metrics = csv_rows(evidence.checked(directory + "session_metrics.csv"))
    previous = keyed([row for row in metrics if row["view"] == VIEW], ["session_id"])
    require(previous.keys() == {(row["session_id"],) for row in rows}, "Session export IDs differ")
    for row in rows:
        sid = row["session_id"]
        saved = previous[(sid,)]
        require(
            evidence.paths[saved["grade_path"]] == row["evaluation_path"]
            and saved["evaluated"] == "True" and saved["used_extra_turn"] == str(row["used_extra_turn"]),
            f"Saved metrics use a different grade: {sid}",
        )
        for k in TRANSITIONS:
            require(int(saved[k]) == row[k], f"Saved transition tally mismatch: {sid}, {k}")
            numerically_equal(saved[f"{k}_fraction"], row[f"{k}_fraction"], (sid, k))
        require(int(saved["core_opportunities"]) == row["prior_passes"], f"Opportunity mismatch: {sid}")
        require(int(saved["core_loss_count"]) == row["PF"] and int(saved["core_gains"]) == row["FP"], sid)
        require(int(saved["core_absolute_passes"]) == row["PP"] + row["FP"], sid)
        if row["prior_passes"]:
            numerically_equal(saved["core_loss_rate"], row["core_loss_rate"], sid)
            require(int(saved["any_core_loss"]) == row["any_core_loss"], sid)
        else:
            require(saved["core_loss_rate"] == saved["any_core_loss"] == "", sid)
    test_rows = csv_rows(evidence.checked(directory + "raw_test_outcomes.csv"))
    test_rows = [r for r in test_rows if (r["session_id"],) in previous and r["suite"] == "core28"]
    keyed(test_rows, ["session_id", "test_id"])
    by_session = {row["session_id"]: row for row in rows}
    witness = {}
    for row in test_rows:
        rebuilt = by_session[row["session_id"]]
        require(
            row["grade_sha256"] == rebuilt["grade_sha256"]
            and row["final_source_sha256"] == rebuilt["final_source_sha256"]
            and evidence.paths[row["grade_path"]] == rebuilt["evaluation_path"],
            f"Raw export cites a different artifact: {row['session_id']}",
        )
        witness[(row["session_id"], row["test_id"])] = tuple(
            row[k] for k in ("baseline_status", "revision_status", "transition")
        )
    require(witness == comparisons, "Saved per-test transitions differ")
    base_rows = csv_rows(evidence.checked(directory + "baseline_test_outcomes.csv"))
    main_ids = {row["participant_id"] for row in rows}
    exported_bases = keyed(
        [r for r in base_rows if r["participant_id"] in main_ids and r["suite"] == "core28"],
        ["participant_id", "test_id"],
    )
    require(len(exported_bases) == 69 * CORE, "Wrong baseline export inventory")
    for (sid, test), (before, _, _) in comparisons.items():
        row = by_session[sid]
        record = exported_bases[(row["participant_id"], test)]
        require(
            record["baseline_status"] == before
            and evidence.paths[record["baseline_path"]] == row["baseline_path"]
            and record["baseline_sha256"] == row["baseline_sha256"],
            f"Wrong baseline export record: {sid}, {test}",
        )
    arms = csv_rows(evidence.checked(directory + "arm_summary.csv"))
    previous_arms = keyed(
        [r for r in arms if r["view"] == VIEW], ["task", "provider", "condition"],
    )
    require(len(previous_arms) == len(summary) == 12, "Wrong arm summary inventory")
    for arm in summary:
        key = tuple(arm[k] for k in ("task", "provider", "condition"))
        saved = previous_arms[key]
        require(int(saved["programs"]) == int(saved["evaluated"]) == arm["programs"], key)
        for k in TRANSITIONS:
            require(int(saved[f"{k}_count"]) == arm[f"{k}_count"], (key, k))
            numerically_equal(saved[f"{k}_fraction_mean"], arm[f"mean_{k}_fraction"], (key, k))
        require(int(saved["any_core_loss_count"]) == arm["programs_with_core_loss"], key)
        checks = {
            "core_loss_rate_mean": "mean_core_loss_rate",
            "any_core_loss_mean": "share_with_core_loss",
            "core_loss_count_mean": "mean_core_losses_per_revision",
            "core_loss_count_median": "median_core_losses_per_revision",
            "core_loss_count_min": "min_core_losses_per_revision",
            "core_loss_count_max": "max_core_losses_per_revision",
        }
        for source, computed in checks.items():
            numerically_equal(saved[source], arm[computed], (key, source))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=PROJECT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = SavedEvidence(args.package)
    rows, comparisons = reconstruct(evidence)
    summary = summarize(rows)
    pairs = recovery_pairs(rows)
    check_exports(evidence, rows, comparisons, summary)
    args.output.mkdir(parents=True, exist_ok=False)
    files = {
        "revision_transitions.csv": rows,
        "arm_transitions.csv": summary,
        "matched_recovery.csv": pairs,
    }
    for name, table in files.items():
        write_csv(args.output / name, table)
    verification = {
        "scope": VIEW,
        "source_manifest_sha256": digest(evidence.manifest),
        "prepared_baselines_checked": len({r["participant_id"] for r in rows}),
        "grades_checked": len(rows),
        "core_test_transitions_checked": len(comparisons),
        "arms_checked_against_export": len(summary),
        "recovery_pairs_per_task_model": [r["matched_programs"] for r in pairs],
        "manifest_bound_package_files_checked": len(evidence.checked_files),
        "extra_turn_grades": [row["session_id"] for row in rows if row["used_extra_turn"]],
        "outputs": {name: digest((args.output / name).read_bytes()) for name in files},
    }
    (args.output / "verification.json").write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verification, indent=2))


if __name__ == "__main__":
    main()
