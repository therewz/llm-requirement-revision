#!/usr/bin/env python3
"""Reconcile core preservation pair signs and oracle-audit coverage from saved observations.

Standard library only. No participant code, graders, or model calls are run.
"""
import argparse
import csv
import hashlib
import io
import itertools
import json
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_PACKAGE = HERE.parents[2]
D = "analysis/descriptive/"
EXP = "analysis/sensitivity/expanded_conflicts/"
PRIMARY = "primary69__main"
TASKS = ("A", "B")
PROVIDERS = ("openai", "anthropic")
ARMS = ("RR", "SA", "EW")
SENSITIVITIES = ("main", "original_limit", "exclude_conflicts", "conflicts_only",
                 "exclude_cleaned", "cleaned_only", "drop_duplicate_friday",
                 "strict_controls", "phase_i_format", "phase_i_no_conflict",
                 "phase_i_all_targets")
EXPANDED_VARIANTS = ("expanded_exclude_conflicts", "expanded_conflicts_only",
                     "expanded_phase_i_no_conflict")

if not __debug__:
    raise RuntimeError("Run without -O so all audit assertions remain enabled.")


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Saved:
    def __init__(self, package):
        self.package = package.resolve()
        manifest = (self.package / "MANIFEST.json").read_bytes()
        self.manifest = json.loads(manifest)["files"]
        self.package_manifest_sha = digest(manifest)
        self.map = self.json("metadata/source_map.json")

    def read(self, relpath):
        file = self.manifest[relpath]
        data = (self.package / relpath).read_bytes()
        assert len(data) == file["bytes"] and digest(data) == file["sha256"], relpath
        return data

    def json(self, relpath):
        return json.loads(self.read(relpath))

    def csv(self, relpath):
        return list(csv.DictReader(io.StringIO(self.read(relpath).decode())))


def index(rows, keys):
    indexed = {}
    for row in rows:
        key = tuple(row[k] for k in keys)
        assert key not in indexed, key
        indexed[key] = row
    return indexed


def csv_write(output, name, rows):
    with (output / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def verify_identity(actual, source, keys):
    for key in keys:
        assert actual[key] == source[key], (key, actual[key], source[key])


def core_status(record):
    suite = record["core28"]
    assert record["evaluation_complete"] and suite["complete"]
    assert suite["expected_case_count"] == len(suite["results"]) == 28
    result = {test: observation[0] for test, observation in suite["results"].items()}
    assert all(result.values())
    return result


def read_observations(saved):
    bases = index(saved.json("metadata/baseline_manifest.json")["records"], ("participant_id",))
    programs = index(saved.csv("metadata/programs.csv"), ("participant_id",))
    baseline_rows = index(
        [row for row in saved.csv(D + "baseline_test_outcomes.csv") if row["suite"] == "core28"],
        ("participant_id", "test_id"),
    )
    raw_tests = index(
        [row for row in saved.csv(D + "raw_test_outcomes.csv") if row["suite"] == "core28"],
        ("session_id", "test_id"),
    )
    raw_baselines = {}
    for (pid,), base in bases.items():
        prog = programs[pid,]
        path = saved.map[base["baseline_path"]]
        data = saved.read(path)
        assert digest(data) == base["baseline_sha256"], path
        record = json.loads(data)
        verify_identity(record, base, ("participant_id", "task", "group"))
        verify_identity(prog, base, ("participant_id", "task", "group"))
        assert digest(saved.read(prog["Repo_V2"])) == record["source_sha256"] == base["starting_source_sha256"]
        assert record["source_sha256"] == prog["Repo_V2_sha256"]
        assert base["source_changed"] == (prog["prepared_changed"] == "True")
        assert base["source_changed"] == (prog["original_phase_II_sha256"] != prog["Repo_V2_sha256"])
        raw_baselines[pid] = before = core_status(record)
        assert {t for t, status in before.items() if status == "passed"} == set(base["core_baseline_pass_ids"])
        for test, status in before.items():
            csv_row = baseline_rows.pop((pid, test))
            assert (csv_row["baseline_status"], csv_row["baseline_path"], csv_row["baseline_sha256"]) == (
                status, base["baseline_path"], base["baseline_sha256"])
    assert set(programs) == set(bases) and not baseline_rows
    extension = saved.json("metadata/analysis_policy.json")["extra_turn_session"]
    original_audit = index(saved.json("metadata/session_audit.json")["sessions"], ("session_id",))
    metrics = {}
    for session in saved.csv("metadata/sessions.csv"):
        pid, sid = session["participant_id"], session["session_id"]
        verify_identity(original_audit[sid,], session, ("session_id", "task", "group", "provider", "condition"))
        original_evaluated = original_audit[sid,]["evaluation_status"] == "evaluated"
        assert original_evaluated == (sid != extension)
        assert session["eligible_main69"] == programs[pid,]["eligible_main69"]
        assert session["eligible_alternative62"] == programs[pid,]["eligible_alternative62"]
        assert (session["eligible_main69"] == "True") == bool(bases[pid,]["eligible_case_ids"])
        path = session["evaluation"]
        data = saved.read(path)
        grade = json.loads(data)
        assert grade["status"] == "evaluated"
        verify_identity(grade["identity"], session,
                        ("session_id", "participant_id", "task", "group", "provider", "condition"))
        final_path = str(Path(path).with_name("final.py"))
        final_sha = digest(saved.read(final_path))
        assert grade["binding"]["final_source_sha256"] == grade["observations"]["source_sha256"] == final_sha
        assert grade["score"]["baseline_source_sha256"] == bases[pid,]["starting_source_sha256"]
        if sid == extension:
            assert session["evaluation"].endswith("/extra_turn/evaluation.json")
            assert digest(saved.read(session["session_dir"] + "/final.py")) == final_sha
            assert saved.json(str(Path(path).with_name("result.json")))["model_turns"] == 9
            assert not (saved.package / session["session_dir"] / "evaluation.json").exists()
        else:
            assert path == session["session_dir"] + "/evaluation.json"
        old = raw_baselines[pid]
        new = core_status(grade["observations"])
        assert set(old) == set(new)
        counts = Counter()
        lost = []
        for test, before in old.items():
            transition = ("P" if before == "passed" else "F") + ("P" if new[test] == "passed" else "F")
            counts[transition] += 1
            if transition == "PF":
                lost.append(test)
            row = raw_tests.pop((sid, test))
            verify_identity(row, session, ("session_id", "participant_id", "task", "group", "provider", "condition"))
            assert saved.map[row["grade_path"]] == path
            assert (row["baseline_status"], row["revision_status"], row["transition"],
                    row["grade_sha256"], row["final_source_sha256"]) == (
                    before, new[test], transition, digest(data), final_sha), (sid, test)
            assert (row["used_extra_turn"] == "True") == (sid == extension)
        key = (pid, session["provider"], session["condition"])
        opportunities = counts["PP"] + counts["PF"]
        core = grade["score"]["core_preservation"]
        assert opportunities == core["opportunity_count"] and set(lost) == set(core["known_observed_loss_ids"])
        assert counts["PF"] == core["loss_count"]
        assert key not in metrics, key
        metrics[key] = {
            "session": sid, "grade": path, "original_evaluated": original_evaluated,
            "lost": tuple(sorted(lost)), "opportunities": opportunities, "counts": counts,
        }
    assert not raw_tests
    assert set(metrics) == set(itertools.product(raw_baselines, PROVIDERS, ARMS))
    assert len(metrics) == len(original_audit) == 432
    return {pid: base for (pid,), base in bases.items()}, raw_baselines, metrics, extension


def eligibility(base, cohort, variant, old_conflicts, expanded_conflicts):
    pid = base["participant_id"]
    targets = set(base["eligible_case_ids"])
    factual = base["original_phase_i_predicates"]
    restored = {test for test in targets if factual.get(test, {}).get("restored") is True}
    if cohort == "all72_preservation":
        return True
    active = targets
    if cohort == "alternative62" or variant in (
            "phase_i_format", "phase_i_no_conflict", "expanded_phase_i_no_conflict"):
        active = restored
    if variant == "phase_i_format":
        active = {test for test in active if factual[test].get("original_return_format_valid") is True}
    if variant == "drop_duplicate_friday" and base["task"] == "A" and base["source_changed"]:
        active = active - {"A-F4"}
    if not active:
        return False
    if variant in ("exclude_conflicts", "phase_i_no_conflict"):
        return pid not in old_conflicts
    if variant == "conflicts_only":
        return pid in old_conflicts
    if variant in ("expanded_exclude_conflicts", "expanded_phase_i_no_conflict"):
        return pid not in expanded_conflicts
    if variant == "expanded_conflicts_only":
        return pid in expanded_conflicts
    if variant == "exclude_cleaned":
        return not base["source_changed"]
    if variant == "cleaned_only":
        return base["source_changed"]
    if variant == "phase_i_all_targets":
        return restored == targets
    return True


def matched_views(saved, bases, raw_baselines, metrics, extension):
    conflict = saved.json("metadata/expanded_conflict_policy.json")
    old = set(conflict["original_conflict_ids"])
    expanded = set(conflict["new_conflict_ids"])
    assert expanded == old | {conflict["additional_conflict_id"]}
    views = list(itertools.product(("primary69", "alternative62"), SENSITIVITIES + EXPANDED_VARIANTS))
    views.extend([("all72_preservation", "main"), ("all72_preservation", "original_limit")])
    members = index(saved.csv(D + "membership.csv") + saved.csv(EXP + "membership.csv"),
                    ("view", "participant_id"))
    saved_metrics = index(saved.csv(D + "session_metrics.csv") + saved.csv(EXP + "session_metrics.csv"),
                          ("view", "session_id"))
    paired = []
    for cohort, variant in views:
        view = cohort + "__" + variant
        for pid, base in sorted(bases.items()):
            claimed = members.pop((view, pid))
            eligible = eligibility(base, cohort, variant, old, expanded)
            assert (claimed["included"] == "True") == eligible, (view, pid)
            verify_identity(claimed, base, ("participant_id", "task", "group"))
            denom = sum(status == "passed" for status in raw_baselines[pid].values())
            assert int(claimed["core_baseline_passes"]) == denom
            if not eligible:
                continue
            for provider in PROVIDERS:
                arms = {arm: metrics[pid, provider, arm] for arm in ARMS}
                observed = {}
                for arm, values in arms.items():
                    sid = values["session"]
                    archive = saved_metrics.pop((view, sid))
                    observe = variant != "original_limit" or values["original_evaluated"]
                    observed[arm] = observe
                    assert observe == (archive["evaluated"] == "True"), (view, sid)
                    if observe:
                        assert not archive["missing_reason"]
                        assert saved.map[archive["grade_path"]] == values["grade"]
                        assert (archive["used_extra_turn"] == "True") == (sid == extension)
                        assert int(archive["core_loss_count"]) == len(values["lost"])
                        for transition in ("PP", "PF", "FP", "FF"):
                            assert int(archive[transition]) == values["counts"][transition]
                        assert int(archive["core_opportunities"]) == denom == values["opportunities"]
                        assert (not archive["core_loss_rate"]) == (denom == 0)
                        if denom:
                            assert abs(float(archive["core_loss_rate"]) - len(values["lost"]) / denom) < 1e-12
                    else:
                        assert sid == extension and not archive["grade_path"] and not archive["core_loss_rate"]
                        assert archive["missing_reason"] == "original_eight_turn_limit_no_grade"
                # Both revisions start from the same baseline, so comparing exact loss
                # counts gives the same direction as comparing the two rates.
                left, right = (len(arms[c]["lost"]) if observed[c] else None for c in ("SA", "EW"))
                missing = [c for c in ("SA", "EW") if not observed[c]]
                delta = Fraction(right - left, denom) if denom and not missing else None
                direction = ("improved" if delta < 0 else "worsened" if delta > 0 else "tied") if delta is not None else (
                    "missing_grade" if missing else "no_baseline_passes")
                paired.append(dict(
                    view=view, task=base["task"], provider=provider, participant_id=pid,
                    group=base["group"], baseline_passes=denom, SA_losses=left, EW_losses=right,
                    EW_minus_SA_loss_rate=str(delta) if delta is not None else "",
                    outcome=direction, missing_arms="+".join(missing), SA_session=arms["SA"]["session"],
                    EW_session=arms["EW"]["session"],
                    SA_grade=arms["SA"]["grade"] if observed["SA"] else "",
                    EW_grade=arms["EW"]["grade"] if observed["EW"] else "",
                ))
    assert not members and not saved_metrics
    return sorted(paired, key=lambda r: (r["view"], r["task"], r["provider"], r["participant_id"]))


def compare_saved_signs(saved, pairs):
    def select(path):
        return [r for r in saved.csv(path)
                if r["metric"] == "core_loss_rate" and r["contrast"] == "EW minus SA"]

    def row_key(r):
        return r["view"], r["task"], r["provider"], r["participant_id"]

    signs = index(select("analysis/statistics/paired_observations.csv") +
                  select(EXP + "paired_observations.csv"),
                  ("view", "task", "provider", "participant_id"))
    summaries = index(select("analysis/statistics/reporting/paired_all_views.csv") +
                      select(EXP + "paired_wilcoxon.csv"), ("view", "task", "provider"))
    grouped = defaultdict(list)
    for row in pairs:
        key = row_key(row)
        grouped[key[:3]].append(row)
        grouped[(row["view"], "all", "all")].append(row)
        if not row["EW_minus_SA_loss_rate"]:
            assert key not in signs, key
            continue
        old = signs.pop(key)
        for prefix, arm in (("left", "SA"), ("right", "EW")):
            assert Fraction(int(old[prefix + "_num"]), int(old[prefix + "_den"])) == Fraction(
                row[arm + "_losses"], row["baseline_passes"]), key
        assert Fraction(int(old["difference_num"]), int(old["difference_den"])) == Fraction(
            row["EW_minus_SA_loss_rate"]), key
    assert not signs
    # Retain any empty task/model strata rather than dropping them from output.
    for key in summaries:
        grouped.setdefault(key, [])
    result = []
    for (view, task, provider), rows in sorted(grouped.items()):
        counts = Counter(row["outcome"] for row in rows)
        n = sum(counts[key] for key in ("improved", "tied", "worsened"))
        item = dict(view=view, task=task, provider=provider, planned_pairs=len(rows),
                    assessable_pairs=n, improved=counts["improved"], tied=counts["tied"],
                    worsened=counts["worsened"], missing_grade=counts["missing_grade"],
                    no_baseline_passes=counts["no_baseline_passes"], unassessable_pairs=len(rows)-n)
        assert item["unassessable_pairs"] == counts["missing_grade"] + counts["no_baseline_passes"]
        if task != "all":
            old = summaries.pop((view, task, provider))
            columns = {"n_planned": "planned_pairs", "n_pairs": "assessable_pairs",
                       "decreased": "improved", "tied": "tied", "increased": "worsened",
                       "excluded_missing_or_undefined": "unassessable_pairs"}
            assert all(int(old[k]) == item[v] for k, v in columns.items()), (view, task, provider)
            excluded = [row["participant_id"] for row in rows if not row["EW_minus_SA_loss_rate"]]
            assert sorted(excluded) == sorted(json.loads(old["excluded_participants"]))
        result.append(item)
    assert not summaries
    return result


def measure_rank_coverage(saved, pairs, raw_baselines, metrics):
    snapshot = saved.json("analysis/supplement/inputs/focused_expectation_ranking.json")
    frozen = snapshot["rankings"]
    by_task = defaultdict(Counter)
    members = defaultdict(set)
    for pair in pairs:
        if pair["view"] != PRIMARY:
            continue
        pid, task, provider = (pair[k] for k in ("participant_id", "task", "provider"))
        members[task].add(pid)
        by_task[task].update({test: 0 for test in raw_baselines[pid]})
        for arm in ("SA", "EW"):
            by_task[task].update(metrics[pid, provider, arm]["lost"])
    ranking, coverage = [], []
    for task, counts in sorted(by_task.items()):
        assert len(counts) == 28
        rank = [dict(test_id=test, PF=counts[test], rank=i, selected=i <= 3)
                for i, test in enumerate(sorted(counts, key=lambda t: (-counts[t], t)), 1)]
        assert rank == frozen[task], (task, rank)
        selected = sum(row["PF"] for row in rank if row["selected"])
        total = sum(counts.values())
        coverage.append(dict(task=task, primary_programs=len(members[task]), selected_test_ids=3,
                             lost_passes_in_selected_tests=selected, all_lost_passes=total,
                             share_percent=float(Fraction(selected * 100, total))))
        ranking.extend(dict(task=task, **row) for row in rank)
    selected = sum(r["lost_passes_in_selected_tests"] for r in coverage)
    total = sum(r["all_lost_passes"] for r in coverage)
    coverage.append(dict(task="all", primary_programs=sum(r["primary_programs"] for r in coverage),
                         selected_test_ids=6, lost_passes_in_selected_tests=selected, all_lost_passes=total,
                         share_percent=float(Fraction(selected * 100, total))))
    return ranking, coverage, snapshot["frozen_selection_sha256"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    saved = Saved(args.package)
    bases, raw_baselines, metrics, extension = read_observations(saved)
    pairs = matched_views(saved, bases, raw_baselines, metrics, extension)
    counts = compare_saved_signs(saved, pairs)
    ranking, coverage, selection_sha = measure_rank_coverage(saved, pairs, raw_baselines, metrics)
    args.output.mkdir(parents=True, exist_ok=False)
    csv_write(args.output, "paired_core_loss_counts.csv", counts)
    csv_write(args.output, "pair_observations.csv", pairs)
    csv_write(args.output, "oracle_test_ranking.csv", ranking)
    csv_write(args.output, "oracle_test_coverage.csv", coverage)
    results = dict(
        status="Verified against saved grades and archived reporting tables",
        baselines=len(bases), selected_grades=len(metrics), core_test_observations=len(metrics) * 28,
        existing_views=len({row["view"] for row in counts}), pair_view_rows=len(pairs),
        view_and_task_model_summary_rows=len(counts),
        original_grade_missing_for=extension, package_manifest_sha256=saved.package_manifest_sha,
        frozen_review_selection_sha256=selection_sha, new_significance_tests=False,
        participant_executions=0, model_calls=0, manual_labels=0,
    )
    (args.output / "validation.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
