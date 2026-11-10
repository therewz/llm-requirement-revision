"""Bridge canonical date strings to verified native weekday inputs."""

import ast
import re


WEEKDAY_PROFILES = {
    "S0001": "weekday_full",
    "S0002": "weekday_abbrev",
    "S0003": "weekday_full",
    "S0004": "weekday_abbrev",
    "S0005": "weekday_full",
    "S0006": "weekday_abbrev",
    "S0008": "weekday_abbrev",
    "S0010": "weekday_full",
    "S0011": "weekday_abbrev",
    "S0038": "weekday_abbrev",
    "S0040": "weekday_abbrev",
    "S0053": "weekday_abbrev",
}
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def clean(participant_id: str, source: bytes, selected_profile: str) -> tuple[bytes, list[str]]:
    """Add a date adapter to the original weekday-based function body."""
    native = WEEKDAY_PROFILES.get(participant_id)
    if native is None:
        if selected_profile.startswith("weekday_"):
            raise ValueError(f"Unreviewed native weekday source for {participant_id}")
        return source, []
    if selected_profile != native:
        raise ValueError(f"Baseline profile changed for {participant_id}")

    tree = ast.parse(source)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "suggest_slots"]
    if len(functions) != 1:
        raise ValueError(f"Unexpected scheduling entry point for {participant_id}")
    function = functions[0]
    if [arg.arg for arg in function.args.args] != ["events", "meeting_duration", "day"]:
        raise ValueError(f"Unexpected scheduling signature for {participant_id}")
    if function.body[0].col_offset != 4:
        raise ValueError(f"Unexpected function body for {participant_id}")
    if re.search(rb"\b(?:_calendar_input_date|_parsed_calendar_input)\b", source):
        raise ValueError(f"Calendar adapter name collides for {participant_id}")

    lines = source.splitlines(keepends=True)
    if ast.get_docstring(function) is not None:
        insertion = function.body[0].end_lineno
        if len(function.body) < 2 or insertion is None or insertion >= function.body[1].lineno:
            raise ValueError(f"No standalone insertion point for {participant_id}")
    else:
        insertion = function.body[0].lineno - 1
        while insertion > function.lineno:
            previous = lines[insertion - 1].lstrip()
            if previous.strip() and not previous.startswith(b"#"):
                break
            insertion -= 1
        if not lines[insertion - 1].rstrip().endswith(b":"):
            raise ValueError(f"No standalone function header for {participant_id}")
    newline = b"\r\n" if lines[insertion - 1].endswith(b"\r\n") else b"\n"
    names = WEEKDAYS if native == "weekday_full" else tuple(name[:3] for name in WEEKDAYS)
    adapter = [
        "",
        "    # Translate canonical dates to the weekday names used below.",
        "    if isinstance(day, str) and len(day) == 10:",
        "        from datetime import date as _calendar_input_date",
        "        try:",
        "            _parsed_calendar_input = _calendar_input_date.fromisoformat(day)",
        "        except ValueError:",
        "            pass",
        "        else:",
        "            if _parsed_calendar_input.isoformat() == day:",
        f"                day = {names!r}[_parsed_calendar_input.weekday()]",
    ]
    inserted = newline.join(line.encode("ascii") for line in adapter) + newline
    cleaned = b"".join(lines[:insertion]) + inserted + b"".join(lines[insertion:])
    ast.parse(cleaned)
    return cleaned, [f"Route canonical ISO dates through the existing {native} input behavior."]
