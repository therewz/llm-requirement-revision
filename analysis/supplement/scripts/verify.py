#!/usr/bin/env python3
"""Regenerate and verify supplementary CSVs using the saved package."""
import argparse
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

SCRIPTS = Path(__file__).resolve().parent
SUPPLEMENT = SCRIPTS.parent
SCRIPTS_BY_TABLE = {
    "joint_success": "joint_success.py",
    "recovery": "recovery.py",
    "count_audit": "count_audit.py",
}


def check_tables(output):
    output.mkdir(parents=True, exist_ok=False)
    total = 0
    for table, script in SCRIPTS_BY_TABLE.items():
        destination = output / table
        subprocess.run(
            [sys.executable, str(SCRIPTS / script), "--output", str(destination)],
            check=True,
        )
        expected = {file.name: file for file in (SUPPLEMENT / table).glob("*.csv")}
        actual = {file.name: file for file in destination.glob("*.csv")}
        if not expected or actual.keys() != expected.keys():
            raise ValueError(f"Unexpected CSV inventory for {table}: {sorted(actual)}")
        for name in expected:
            if expected[name].read_bytes() != actual[name].read_bytes():
                raise ValueError(f"Reproduced CSV differs: {table}/{name}")
        total += len(expected)
        print(f"{table}: {len(expected)} matching CSVs")
    print(f"Supplementary tables reproduced byte for byte: {total}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Create a new persistent output folder.")
    args = parser.parse_args()
    if args.output:
        check_tables(args.output)
    else:
        with TemporaryDirectory(prefix="withdrawal-supplement-") as temporary:
            check_tables(Path(temporary) / "tables")


if __name__ == "__main__":
    main()
