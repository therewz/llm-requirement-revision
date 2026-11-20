"""Reproduce the expectation audit, patch sample and results from ratings and saved grades."""

import argparse
import ast
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from statistics import mean, median


HERE = Path(__file__).resolve().parent
ARMS = ("SA", "EW")
LABELS = ("required", "unspecified_or_ambiguous", "conflicting")
MECHANISMS = (
    "unrelated_rewrite",
    "interface_drift",
    "still_valid_constraint_removed",
    "requirement_reinterpretation",
    "other_or_insufficient_evidence",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rows(path):
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def write_rows(path, records):
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=records[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def by_key(records, field):
    result = {}
    for row in records:
        key = row[field]
        require(key not in result, f"Duplicate {field}: {key}")
        result[key] = row
    return result


def json_file(path):
    return json.loads(path.read_bytes())


def load_grades(root):
    programs = by_key(
        [r for r in rows(root / "metadata/programs.csv") if r["eligible_main69"] == "True"],
        "participant_id",
    )
    sessions = by_key(
        [
            r
            for r in rows(root / "metadata/sessions.csv")
            if r["eligible_main69"] == "True" and r["condition"] in ARMS
        ],
        "session_id",
    )
    metrics = by_key(
        [
            r
            for r in rows(root / "analysis/descriptive/session_metrics.csv")
            if r["view"] == "primary69__main" and r["condition"] in ARMS
        ],
        "session_id",
    )
    require(set(sessions) == set(metrics), "Session and analysis indices differ")
    starts = {}
    for pid, row in programs.items():
        folder = root / "evaluation" / ("Task_" + row["task"]) / "baselines/Repo_V2"
        starts[pid] = json_file(folder / (pid + ".json"))["core28"]["results"]
    scheduling_key = by_key(json_file(root / "evaluation/Task_A/O1_O2.json")["cases"], "case_id")
    frames = {}
    for sid, record in sessions.items():
        saved = json_file(root / record["evaluation"])
        require(saved["identity"]["session_id"] == sid, f"Evaluation identity: {sid}")
        grade = saved["observations"]
        pid = record["participant_id"]
        before = starts[pid]
        after = grade["core28"]["results"]
        require(
            grade["core28"]["complete"] and set(before) == set(after) and len(before) == 28, sid
        )
        passed = {t for t, result in before.items() if result[0] == "passed"}
        lost = {t for t in passed if after[t][0] == "failed"}
        included = set(json.loads(metrics[sid]["selected_case_ids"]))
        target = {
            r["case_id"]: r["status"]
            for r in saved["score"]["withdrawal"]["case_results"]
            if r["case_id"] in included
        }
        require(included and set(target) == included, f"Missing eligible targets: {sid}")
        exceptions = Counter(
            grade["targets"]["cases"][t]["exc"]
            for t in included
            if grade["targets"]["cases"][t]["kind"] == "exc"
        )
        matching_weekday_lists = empty_lists = 0
        raw_targets = grade["targets"]["cases"]
        for case_id, outcome in target.items():
            if record["task"] == "A" and outcome == "INDETERMINATE":
                raw = raw_targets[case_id]
                spec = scheduling_key[case_id]
                require(
                    raw["kind"] == "ret" and raw["type"] == "list_str", f"Non-list: {sid}/{case_id}"
                )
                controls = [raw_targets[k] for k in spec["control_ids"]]
                if (
                    len(controls) == 2
                    and all(v == raw for v in controls)
                    and set(spec["target_slots"]) - set(raw["value"])
                ):
                    matching_weekday_lists += 1
                empty_lists += int(raw["value"] == [])
        require(
            len(lost) == int(metrics[sid]["PF"])
            and len(passed) == int(metrics[sid]["core_opportunities"]),
            sid,
        )
        require(
            sum(v == "RESTORED" for v in target.values()) == int(metrics[sid]["target_met"]), sid
        )
        frames[sid] = dict(
            **record,
            passed=passed,
            lost=lost,
            target=Counter(target.values()),
            exceptions=exceptions,
            matching_weekday_lists=matching_weekday_lists,
            empty_lists=empty_lists,
        )
    return programs, frames


def agreement(left, right):
    n = len(left)
    require(n == len(right) and n > 0, "Missing paired ratings")
    observed = Fraction(sum(a == b for a, b in zip(left, right)), n)
    counts_left, counts_right = Counter(left), Counter(right)
    expected = Fraction(
        sum(count * counts_right[label] for label, count in counts_left.items()), n * n
    )
    return {
        "items": n,
        "matching": int(n * observed),
        "percent": round(float(100 * observed), 3),
        "cohens_kappa": round(float((observed - expected) / (1 - expected)), 6)
        if expected < 1
        else None,
    }


def oracle_audit(root, programs, frames):
    counts = defaultdict(Counter)
    for frame in frames.values():
        counts[frame["task"]].update(frame["lost"])
    selected = {task: sorted(c, key=lambda t: (-c[t], t))[:3] for task, c in counts.items()}
    ratings = rows(HERE / "oracle_ratings.csv")
    by_context = defaultdict(dict)
    for row in ratings:
        ctx, test = row["context_id"], row["test"]
        require(
            test not in by_context[ctx]
            and all(row[k] in LABELS for k in ("reviewer_1", "reviewer_2", "consensus")),
            ctx,
        )
        by_context[ctx][test] = row["consensus"]
    contexts = by_key(rows(HERE / "oracle_contexts.csv"), "context_id")
    require(set(contexts) == set(by_context), "Unmatched requirement contexts")
    program_context, unique_text = {}, {}
    for ctx, c in contexts.items():
        require(set(by_context[ctx]) == set(selected[c["task"]]), f"Audit ranking differs: {ctx}")
        reference = tuple((root / c[arm + "_prompt"]).read_bytes() for arm in ARMS)
        text_key = (c["task"], *reference)
        require(text_key not in unique_text, f"Duplicate prompt context: {ctx}")
        unique_text[text_key] = ctx
        for pid in c["programs"].split("|"):
            program = programs[pid]
            require(
                (c["task"], c["group"]) == (program["task"], program["group"])
                and pid not in program_context,
                pid,
            )
            prompt_dir = root / "model_inputs" / ("Task_" + c["task"]) / c["group"] / pid
            require(
                reference == tuple((prompt_dir / arm / "prompt.txt").read_bytes() for arm in ARMS),
                f"Prompt mismatch: {pid}",
            )
            program_context[pid] = ctx
    require(set(programs) == set(program_context), "Missing reviewed program")
    left = [r["reviewer_1"] for r in ratings]
    right = [r["reviewer_2"] for r in ratings]
    grid = defaultdict(dict)
    audited_losses = Counter()
    for sid, f in sorted(frames.items()):
        pid = f["participant_id"]
        for test, label in by_context[program_context[pid]].items():
            if test in f["lost"]:
                audited_losses[label] += 1
            if label == "required" and test in f["passed"]:
                key = (pid, f["task"], f["provider"], test)
                grid[key][f["condition"]] = {"loss": test in f["lost"], "grade": f["evaluation"]}
    required = []
    for (pid, task, provider, test), values in sorted(grid.items()):
        require(set(values) == set(ARMS), f"Missing condition: {pid}, {test}, {provider}")
        row = dict(
            program=pid, task=task, provider=provider, context_id=program_context[pid], test=test
        )
        for arm in ARMS:
            row[arm + "_outcome"] = "failed" if values[arm]["loss"] else "passed"
            row[arm + "_grade"] = values[arm]["grade"]
        required.append(row)
    rates = []
    for task, provider in sorted({(f["task"], f["provider"]) for f in frames.values()}):
        subset = [r for r in required if (r["task"], r["provider"]) == (task, provider)]
        pids = sorted({r["program"] for r in subset})
        rate = dict(
            task=task,
            provider=provider,
            eligible_programs=len(pids),
            baseline_passing_required_tests=len(subset),
        )
        for arm in ARMS:
            rate[arm + "_losses"] = (
                sum(r[arm + "_outcome"] == "failed" for r in subset) if pids else None
            )
            losses = [
                mean(r[arm + "_outcome"] == "failed" for r in subset if r["program"] == pid)
                for pid in pids
            ]
            rate[arm + "_mean_program_loss_percent"] = 100 * mean(losses) if pids else None
        rates.append(rate)
    return required, {
        "contexts": len(contexts),
        "ranked_tests": selected,
        "exact_agreement": agreement(left, right),
        "required_status_agreement": agreement(
            [v == "required" for v in left], [v == "required" for v in right]
        ),
        "consensus": dict(Counter(r["consensus"] for r in ratings)),
        "all_core_losses": sum(sum(c.values()) for c in counts.values()),
        "audited_losses_by_consensus": dict(audited_losses),
        "required_results": rates,
    }


def draw(stream, pool):
    seed = hashlib.sha256(("20261116:" + stream).encode("utf-8")).hexdigest()
    return random.Random(int(seed, 16)).choice(sorted(pool))


def select_patches(frames):
    strata = defaultdict(dict)
    incomplete, shared, pair_slots = set(), set(), {}
    pools = defaultdict(list)
    for sid, f in frames.items():
        strata[(f["task"], f["provider"])].setdefault(f["participant_id"], {})[f["condition"]] = sid
        if f["target"]["RESTORED"] < sum(f["target"].values()):
            incomplete.add(sid)
            bucket = "inconclusive" if f["target"]["INDETERMINATE"] else "error_only"
            pools[(f["provider"], bucket, f["condition"])].append(sid)
    for (task, provider), pairs in strata.items():
        difference = {}
        for pid, arms in pairs.items():
            sa, ew = frames[arms["SA"]], frames[arms["EW"]]
            require(sa["passed"] == ew["passed"] and sa["passed"], pid)
            difference[pid] = Fraction(len(sa["lost"]) - len(ew["lost"]), len(sa["passed"]))
        positive = {pid: d for pid, d in difference.items() if d > 0}
        middle = median(positive.values())
        largest = min(positive, key=lambda pid: (-positive[pid], pid))
        nearest = sorted(
            (pid for pid in positive if pid != largest),
            key=lambda pid: (abs(positive[pid] - middle), pid),
        )[:2]
        tie = draw(f"pair-tie:{task}:{provider}", [pid for pid, d in difference.items() if d == 0])
        slots = [
            ("largest_positive", largest),
            ("nearest_positive_median_1", nearest[0]),
            ("nearest_positive_median_2", nearest[1]),
            ("random_tie", tie),
        ]
        joint = draw(f"calibration-pair:{task}:{provider}", [pid for _, pid in slots])
        for slot, pid in slots:
            for sid in pairs[pid].values():
                pair_slots[sid] = slot
                if pid == joint:
                    shared.add(sid)
    assignment = draw(
        "calibration-failure:openai:arm-assignment",
        ["EW_inconclusive__SA_error_only", "SA_inconclusive__EW_error_only"],
    )
    openai_arm = {s.split("_", 1)[1]: s.split("_", 1)[0] for s in assignment.split("__")}
    for provider in sorted({f["provider"] for f in frames.values()}):
        for bucket in ("inconclusive", "error_only"):
            arm = openai_arm[bucket] if provider == "openai" else "SA"
            shared.add(
                draw(
                    f"calibration-failure:{provider}:{bucket}:{arm}", pools[(provider, bucket, arm)]
                )
            )
    return pair_slots, incomplete, shared


def functions(path):
    """Compare named functions by lexical scope; distinguish repeated names in the same scope."""
    result = {}
    occurrences = defaultdict(Counter)

    def walk(node, scope):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                occurrences[scope][child.name] += 1
                key = scope + ((child.name, occurrences[scope][child.name]),)
                if not isinstance(child, ast.ClassDef):
                    result[key] = ast.dump(child, include_attributes=False)
                walk(child, key)
            else:
                walk(child, scope)

    walk(ast.parse(path.read_bytes()), ())
    return result


def patch_review(root, programs, frames):
    slots, incomplete, shared = select_patches(frames)
    by_revision = defaultdict(dict)
    for r in rows(HERE / "patch_ratings.csv"):
        sid, reviewer = r["session_id"], r["rating"]
        require(reviewer not in by_revision[sid], f"Duplicate assessment: {sid}/{reviewer}")
        require((sid in shared) == (r["round"] == "shared"), f"Wrong review round: {sid}")
        require(r["obsolete_logic"] in ("removed", "bypassed", "retained", "unassessable"), sid)
        require(r["unrelated_named_function"] in ("yes", "no", "unassessable"), sid)
        require(set(filter(None, r["mechanisms"].split("|"))) <= set(MECHANISMS), sid)
        by_revision[sid][reviewer] = r
    require(
        set(by_revision) == set(slots) | incomplete,
        "Reviewed revisions differ from eligible sample",
    )
    cases = []
    for sid, obs in sorted(by_revision.items()):
        expected = (
            {"reviewer_1", "reviewer_2", "final"} if sid in shared else {"reviewer_1", "final"}
        )
        require(set(obs) == expected, f"Missing assessments: {sid}")
        final = obs["final"]
        f = frames[sid]
        pid = f["participant_id"]
        starting = programs[pid]["Repo_V2"]
        end = f["session_dir"] + "/final.py"
        left, right = functions(root / starting), functions(root / end)
        changed = sum(left.get(k) != right.get(k) for k in left.keys() | right.keys())
        included = f["target"]
        exceptions = f["exceptions"]
        case = dict(
            session_id=sid,
            participant_id=pid,
            task=f["task"],
            group=f["group"],
            provider=f["provider"],
            condition=f["condition"],
            round=final["round"],
            pair_selection_slot=slots.get(sid, ""),
            incomplete=int(sid in incomplete),
            changed_named_functions=changed,
            prior_passes=len(f["passed"]),
            lost_passes=len(f["lost"]),
            selected_targets=sum(included.values()),
        )
        for label in ("RESTORED", "RETAINED", "PARTIAL", "OTHER_FAILURE", "INDETERMINATE"):
            case[label] = included[label]
        case["inconclusive_same_list_on_three_days"] = f["matching_weekday_lists"]
        case["inconclusive_empty_list"] = f["empty_lists"]
        case["target_exceptions"] = "|".join(f"{k}={v}" for k, v in sorted(exceptions.items()))
        case.update(
            prepared_source=starting,
            revised_source=end,
            evaluation=f["evaluation"],
            prompt=f"model_inputs/Task_{f['task']}/{f['group']}/{pid}/{f['condition']}/prompt.txt",
        )
        require((root / case["prompt"]).is_file(), case["prompt"])
        cases.append(case)

    pairs = [r for r in cases if r["pair_selection_slot"]]
    failed = [r for r in cases if r["incomplete"]]

    def matched_results(arm):
        part = [r for r in pairs if r["condition"] == arm]
        labels = [by_revision[r["session_id"]]["final"] for r in part]
        return {
            "revisions": len(part),
            "unrelated_named_function": sum(i["unrelated_named_function"] == "yes" for i in labels),
            "median_named_functions_changed": median(r["changed_named_functions"] for r in part),
            "mechanisms": {
                k: sum(k in i["mechanisms"].split("|") for i in labels) for k in MECHANISMS
            },
            "no_core_loss": sum(r["lost_passes"] == 0 for r in part),
            "no_mechanism": sum(not i["mechanisms"] for i in labels),
        }

    patterns = Counter()
    for r in failed:
        if r["OTHER_FAILURE"] == r["selected_targets"]:
            patterns["error_only"] += 1
        elif r["INDETERMINATE"] == r["selected_targets"]:
            patterns["inconclusive_only"] += 1
        elif r["INDETERMINATE"] + r["OTHER_FAILURE"] == r["selected_targets"]:
            patterns["mixed_error_and_inconclusive"] += 1
        else:
            patterns["other"] += 1
    fields = ("obsolete_logic", "unrelated_named_function", "mechanisms")
    amended = sum(
        any(obs["final"][k] != obs["reviewer_1"][k] for k in fields)
        for sid, obs in by_revision.items()
        if sid not in shared
    )
    return cases, {
        "withdrawal_revisions": len(frames),
        "distinct_reviewed": len(cases),
        "shared_reviewed": len(shared),
        "remaining_reviewed": len(cases) - len(shared),
        "remaining_amended_after_first_rating": amended,
        "set_overlap": sorted(incomplete.intersection(slots)),
        "obsolete_logic": dict(
            Counter(obs["final"]["obsolete_logic"] for obs in by_revision.values())
        ),
        "matched_pairs": len(pairs) // 2,
        "matched_by_condition": {arm: matched_results(arm) for arm in ARMS},
        "incomplete_revisions": len(failed),
        "incomplete_programs": len({r["participant_id"] for r in failed}),
        "incomplete_by_task": dict(Counter(r["task"] for r in failed)),
        "incomplete_by_condition": dict(Counter(r["condition"] for r in failed)),
        "incomplete_target_outcomes": {
            k: sum(r[k] for r in failed) for k in ("OTHER_FAILURE", "INDETERMINATE")
        },
        "incomplete_same_weekday_lists": sum(
            r["inconclusive_same_list_on_three_days"] for r in failed
        ),
        "incomplete_patterns": dict(patterns),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=HERE.parent)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.package.resolve()
    programs, frames = load_grades(root)
    required, audit = oracle_audit(root, programs, frames)
    cases, patches = patch_review(root, programs, frames)
    args.output.mkdir(parents=True, exist_ok=True)
    write_rows(args.output / "required_test_outcomes.csv", required)
    write_rows(args.output / "reviewed_cases.csv", cases)
    (args.output / "summary.json").write_text(
        json.dumps({"oracle_audit": audit, "patch_review": patches}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
