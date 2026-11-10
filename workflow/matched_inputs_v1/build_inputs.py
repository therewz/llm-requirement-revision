"""Build provider-neutral matched input drafts from frozen original artifacts.

Only files are read and written. Participant code is parsed with ast and is never
imported or executed. Prompts remain drafts while execution mode is undecided.
"""

import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "runs/withdrawal_keys_v1"
PROMPTS = ROOT / "handoff/correspondence/messages/20261104_maleknaz_three_prompts_as_relayed.txt"
MANUALS = ROOT / "runs/author_manuals_review_v1"
CONDITIONS = ("RR", "SA", "EW")
PROCESS_SENTENCE = "Update your solution, tests and documents to incorporate this requirement."
MODE_EDITS = [
    {"action": "remove", "text": "- You may run the existing tests to validate your changes.\n", "reason": "No supplied tests are included, and execution mode is undecided."},
    {"action": "remove", "text": "- Do not modify, remove, or add tests.\n", "reason": "Whether temporary self-checks are permitted depends on the later execution-mode decision."},
    {"action": "replace", "old": "- If existing tests or repository documentation conflict with the supplied specification, treat the supplied specification as authoritative.", "new": "- If repository documentation conflicts with the supplied specification, treat the supplied specification as authoritative.", "reason": "Supplied tests are excluded from all model workspaces."},
    {"action": "replace", "old": "Once finished, provide a brief summary of your modifications and the tests you executed.", "new": "Once finished, provide a brief summary of your modifications.", "reason": "Test-execution reporting is reserved for a later execution-mode decision."},
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_record(path, data):
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": digest(data), "bytes": len(data)}


def checked_bytes(relative_path, expected_hash):
    path = (ROOT / relative_path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Source path escapes the project root")
    data = path.read_bytes()
    if digest(data) != expected_hash:
        raise ValueError(f"Source hash mismatch: {relative_path}")
    return data


def paragraph(path, marker):
    """Extract the paragraph payload with explicit byte and line provenance."""
    data = path.read_bytes()
    lines = data.decode("utf-8").splitlines(keepends=True)
    matches = [(index, line) for index, line in enumerate(lines) if marker in line]
    if len(matches) != 1:
        raise ValueError(f"Expected one paragraph in {path}")
    index, line = matches[0]
    prefix_end = line.index("] ") + 2
    raw_payload = line[prefix_end:].rstrip("\r\n")
    payload = raw_payload.strip()
    start = len("".join(lines[:index]).encode()) + len(line[:prefix_end].encode())
    return payload, {
        **source_record(path, data), "line": index + 1,
        "paragraph_marker": line[:prefix_end].strip(),
        "payload_byte_start": start,
        "payload_byte_end": start + len(raw_payload.encode()),
        "normalization": "Remove extracted-paragraph outer whitespace only.",
        "payload_sha256": digest(payload.encode()),
    }


def load_task_texts():
    tasks = {}
    for task in ("A", "B"):
        descriptions = []
        requirements = []
        records = {"descriptions": [], "requirements": []}
        for group in ("G1", "G2", "G3"):
            p1 = MANUALS / f"p1_Task{task}_{group}{task}_manual.txt"
            description, record = paragraph(p1, "You are asked to implement a Python function")
            descriptions.append(description)
            records["descriptions"].append(record)
            p2 = MANUALS / f"p2_Task{task}_{group}{task}_manual_prt2_v2.txt"
            marker = "Meetings scheduled on Fridays must not start after" if task == "A" else "At least one resource must remain unallocated after assignment."
            requirement, record = paragraph(p2, marker)
            if not requirement.endswith(PROCESS_SENTENCE):
                raise ValueError(f"Unexpected requirement paragraph ending in {p2}")
            requirement = requirement[:-len(PROCESS_SENTENCE)].rstrip()
            if len(re.findall(r"\.\s|\.$", requirement)) != 3:
                raise ValueError("Expected three behavioral sentences")
            record["behavioral_payload_sha256"] = digest(requirement.encode())
            record["excluded_suffix"] = PROCESS_SENTENCE
            record["boundary_reason"] = "The first three sentences define the rule. The final sentence directs lab test/document edits, outside the prepared revision workspace."
            requirements.append(requirement)
            records["requirements"].append(record)
        if len(set(descriptions)) != 1 or len(set(requirements)) != 1:
            raise ValueError(f"Shared task or requirement text differs by group for Task {task}")
        tasks[task] = {"description": descriptions[0], "requirement": requirements[0], "provenance": records}
    return tasks


def load_prompt_templates():
    data = PROMPTS.read_bytes()
    text = data.decode("utf-8")
    lead = "You are a coding agent responsible for maintaining an existing Python repository."
    starts = [match.start() for match in re.finditer(re.escape(lead), text)]
    ending = "Once finished, provide a brief summary of your modifications and the tests you executed."
    if len(starts) != 3:
        raise ValueError("Expected three original prompts")
    templates = {}
    spans = {}
    for condition, start in zip(CONDITIONS, starts):
        end = text.index(ending, start) + len(ending)
        original = text[start:end]
        template = original
        for edit in MODE_EDITS:
            old = edit.get("old", edit.get("text"))
            if template.count(old) != 1:
                raise ValueError(f"Expected one mode-dependent clause for {condition}")
            template = template.replace(old, edit.get("new", ""))
        templates[condition] = template
        spans[condition] = {
            "byte_start": len(text[:start].encode()), "byte_end": len(text[:end].encode()),
            "line_start": text[:start].count("\n") + 1,
            "line_end": text[:end].count("\n") + 1,
            "original_sha256": digest(original.encode()),
            "mode_neutral_sha256": digest(template.encode()),
        }
    return templates, {**source_record(PROMPTS, data), "spans": spans, "common_mode_edits": MODE_EDITS}


def fenced_json(raw_bytes):
    text = raw_bytes.decode("utf-8")
    json.loads(text)
    longest = max((len(match.group()) for match in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}json\n{text}" + ("" if text.endswith("\n") else "\n") + fence


def specification_text(description, specification_bytes):
    result = "### Original task description\n\n" + description
    if specification_bytes is not None:
        result += "\n\n### Participant's Phase-I specification\n\n" + fenced_json(specification_bytes)
    return result


def render_prompt(template, current, requirement):
    """Substitute trusted template tokens once, preserving inserted source text."""
    values = {"[INSERT PHASE I REQUIREMENTS]": current, "[INSERT PHASE II REQUIREMENT]": requirement}
    return re.sub(r"\[INSERT PHASE I REQUIREMENTS\]|\[INSERT PHASE II REQUIREMENT\]", lambda match: values[match.group()], template) + "\n"


def audit_imports(source):
    tree = ast.parse(source)
    imports = set()
    relative = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                relative.append(node.module)
            elif node.module:
                imports.add(node.module.split(".")[0])
    outside = sorted(imports - set(sys.stdlib_module_names))
    dynamic = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "__import__":
            dynamic.append(node.lineno)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
            dynamic.append(node.lineno)
    if outside or relative or dynamic:
        raise ValueError(f"Dependency review required: {outside}, {relative}, {dynamic}")
    return {"method": "static AST import inspection", "stdlib_imports": sorted(imports), "nonstdlib_imports": outside, "participant_execution": False}


def write_same(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f"Refusing to overwrite differing prepared artifact: {path}")
    path.write_bytes(data)


def build(output_root):
    output_root = Path(output_root)
    freeze_bytes = (BASELINE / "freeze.json").read_bytes()
    freeze = json.loads(freeze_bytes)
    inventory_path = BASELINE / "inventory.json"
    inventory_bytes = checked_bytes(inventory_path.relative_to(ROOT), freeze["hashes"][inventory_path.relative_to(ROOT).as_posix()])
    inventory = json.loads(inventory_bytes)
    if len(inventory) != 72 or len({row["participant_id"] for row in inventory}) != 72:
        raise ValueError("Expected exactly 72 original participants")
    tasks = load_task_texts()
    templates, template_provenance = load_prompt_templates()
    metadata_path = BASELINE / "derived/programs.csv"
    metadata_bytes = metadata_path.read_bytes()
    research_flags = {row["participant_id"]: row for row in csv.DictReader(metadata_bytes.decode().splitlines())}
    records = []
    for row in sorted(inventory, key=lambda item: item["participant_id"]):
        sid, task, group = row["participant_id"], row["task"], row["group"]
        source = checked_bytes(row["P2"]["path"], row["P2"]["sha256"])
        imports = audit_imports(source)
        specs = row["P1"]["specifications"]
        if len(specs) != (0 if group == "G1" else 1):
            raise ValueError(f"Unexpected Phase-I specification count for {sid}")
        raw_spec = checked_bytes(specs[0]["path"], specs[0]["sha256"]) if specs else None
        current = specification_text(tasks[task]["description"], raw_spec)
        active_block = "**Additional Requirement**\n\n" + tasks[task]["requirement"] + "\n\n"
        notice_block = "**Requirement Withdrawal**\n\nThe following previously implemented requirement has been withdrawn and is no longer applicable:\n\n" + tasks[task]["requirement"] + "\n\nUpdate the implementation to remove the behavioral restriction introduced by this requirement and restore the behavior permitted by the current specification. Preserve all other specified functionality.\n\n"
        prepared = {}
        condition_records = {}
        for condition in CONDITIONS:
            prompt = render_prompt(templates[condition], current, tasks[task]["requirement"])
            block = {"RR": active_block, "SA": "", "EW": notice_block}[condition]
            context = "**Current Specification**\n\n" + current + "\n\n" + block
            prepared[condition] = prompt
            folder = output_root / "packets" / sid / condition
            payloads = {"workspace/src/solution.py": source, "condition_context.md": context.encode(), "prompt_draft.md": prompt.encode()}
            hashes = {}
            for name, payload in payloads.items():
                destination = folder / name
                write_same(destination, payload)
                hashes[name] = {"sha256": digest(payload), "bytes": len(payload)}
            actual = {path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file()}
            if actual != set(payloads):
                raise ValueError(f"Unexpected packet files for {sid}/{condition}")
            condition_records[condition] = {"path": f"packets/{sid}/{condition}", "files": hashes}
        if prepared["EW"].replace(notice_block, "", 1) != prepared["SA"]:
            raise ValueError(f"SA/EW mismatch beyond withdrawal notice for {sid}")
        if prepared["RR"].replace(active_block, "", 1) != prepared["SA"]:
            raise ValueError(f"RR mismatch beyond active requirement for {sid}")
        records.append({
            "participant_id": sid, "task": task, "group": group,
            "source_code": row["P2"], "phase_i_specification": specs,
            "imports": imports, "conditions": condition_records,
            "pair_checks": {"sa_ew_only_notice": True, "rr_sa_only_active_requirement": True, "same_source_bytes": True},
            "research_metadata_only": research_flags[sid],
        })
    manifest = {
        "schema_version": 1, "status": "MODE_NEUTRAL_DRAFTS_PENDING_EXECUTION_MODE_AND_CONFLICT_REVIEW",
        "live_enabled": False, "provider_adapter": None, "model_configuration": None,
        "generation_api_calls": 0, "participant_execution": False,
        "participant_count": len(records), "packet_count": len(records) * 3,
        "specification_count": sum(bool(row["phase_i_specification"]) for row in records),
        "model_workspace_allowlist": ["src/solution.py"],
        "delivery_layout": "prompt_draft.md is the provider-neutral instruction artifact. condition_context.md is an extracted review view. workspace/ is the only model filesystem subtree. Research metadata is outside it.",
        "generation_mode": "undecided", "approval_reference": None,
        "build_code": source_record(Path(__file__), Path(__file__).read_bytes()),
        "inventory": source_record(inventory_path, inventory_bytes),
        "baseline_freeze": source_record(BASELINE / "freeze.json", freeze_bytes),
        "research_metadata_source": source_record(metadata_path, metadata_bytes),
        "tasks": tasks, "prompt_source": template_provenance,
        "historical_instruction_flag": "The authentic task paragraph includes permission to use ChatGPT and write tests. That historical sentence is preserved. Operational execution/test permissions require a later common provider wrapper decision.",
        "records": records,
    }
    write_same(output_root / "build_manifest.json", (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode())
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "runs/matched_inputs_v1")
    args = parser.parse_args()
    manifest = build(args.output)
    print(json.dumps({"participants": manifest["participant_count"], "packets": manifest["packet_count"], "live_enabled": manifest["live_enabled"]}))


if __name__ == "__main__":
    main()
