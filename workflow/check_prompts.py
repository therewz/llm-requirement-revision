"""Rebuild each revision prompt and check it against the recorded opening requests."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re


INTRO = (
    "Revise the existing Python implementation to satisfy the current requirements below. "
    "Treat these requirements as authoritative. Remove restrictions they do not require, "
    "preserve all specified functionality, and avoid unrelated changes. "
    "If no changes are needed, leave the implementation unchanged."
)
ENDING = "Briefly summarize any changes."
NOTICES = {
    "RR": (
        "Additional requirement",
        "The following additional requirement is active and takes "
        "precedence where it conflicts with the requirements above:",
    ),
    "EW": (
        "Requirement withdrawal",
        "The following requirement has been withdrawn. Remove the "
        "restriction it introduced; it is not part of the current requirements:",
    ),
}
CONDITIONS = ("RR", "SA", "EW")
PROVIDERS = ("openai", "anthropic")


def require(condition, location):
    if not condition:
        raise ValueError(f"Input mismatch: {location}")


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def reconstruct(requirements, group, program, condition):
    text = (requirements / "task_description.txt").read_bytes().decode("utf-8")
    current = "**Current requirements**\n\n### Task description\n\n" + text
    inputs = list((requirements / group / program).glob("*.json"))
    require(len(inputs) == (0 if group == "G1" else 1), f"{program}: original specification")
    if inputs:
        raw = inputs[0].read_bytes().decode("utf-8")
        json.loads(raw)
        runs = re.findall(r"`+", raw)
        fence = "`" * max(3, max(map(len, runs), default=0) + 1)
        current += "\n\n### Specification\n\n" + fence + "json\n" + raw
        if not raw.endswith("\n"):
            current += "\n"
        current += fence
    if condition in NOTICES:
        heading, notice = NOTICES[condition]
        rule = (requirements / "Phase_II_requirement.txt").read_bytes().decode("utf-8")
        current += f"\n\n**{heading}**\n\n{notice}\n\n{rule}"
    return INTRO + "\n\n" + current + "\n\n" + ENDING + "\n"


def verify(root):
    inputs = root / "model_inputs"
    system = (inputs / "shared_instructions.txt").read_bytes().decode("utf-8")
    tools = {
        provider: json.loads((inputs / "tools" / (provider + ".json")).read_bytes())
        for provider in PROVIDERS
    }
    prompts, sources = {}, {}
    for program in read_csv(root / "metadata/programs.csv"):
        pid, task, group = program["participant_id"], program["task"], program["group"]
        require(pid not in sources, pid)
        source = hashlib.sha256((root / program["Repo_V2"]).read_bytes()).hexdigest()
        require(source == program["Repo_V2_sha256"], pid)
        sources[pid] = source
        for condition in CONDITIONS:
            path = inputs / ("Task_" + task) / group / pid / condition / "prompt.txt"
            expected = reconstruct(
                inputs / "requirements" / ("Task_" + task), group, pid, condition
            )
            require(path.read_bytes() == expected.encode("utf-8"), path)
            prompts[(pid, condition)] = expected
    seen = set()
    for s in read_csv(root / "metadata/sessions.csv"):
        pid, condition, provider = s["participant_id"], s["condition"], s["provider"]
        sid = s["session_id"]
        key = (pid, condition, provider)
        require(key not in seen, sid)
        seen.add(key)
        user = prompts[(pid, condition)]
        folder = root / s["session_dir"]
        plan = json.loads((folder / "plan.json").read_bytes())["plan"]
        require(
            (pid, condition, provider, sid)
            == tuple(plan[k] for k in ("participant_id", "condition", "provider", "session_id")),
            sid,
        )
        require(
            plan["source_sha256"] == sources[pid] and plan["operational_instruction"] == system, sid
        )
        require(plan["prompt_sha256"] == hashlib.sha256(user.encode("utf-8")).hexdigest(), sid)
        request = json.loads((folder / "attempts/0001_request.json").read_bytes())
        require(request["model"] == plan["model"] and request["tools"] == tools[provider], sid)
        user_message = {"role": "user", "content": user}
        if provider == "openai":
            require(request["input"] == [{"role": "system", "content": system}, user_message], sid)
        else:
            require(request["system"] == system and request["messages"] == [user_message], sid)
    require(
        seen == {(pid, arm, provider) for pid, arm in prompts for provider in PROVIDERS},
        "missing program/condition/provider combinations",
    )
    print(
        f"Verified {len(prompts)} reconstructed prompts on {len(sources)} programs and {len(seen)} opening requests."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parents[1])
    verify(parser.parse_args().package.resolve())
