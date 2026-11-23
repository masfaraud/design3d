#!/usr/bin/env python3
"""
Coverage ratchet: fails if the coverage of the project or of a file drops below its threshold.

Run it after ``coverage json``. When coverage has increased, raise the thresholds to the values it suggests, so that
coverage can never go back down.
"""

import json
import sys

MIN_FILE_COVERAGE = 55.6
MIN_PROJECT_COVERAGE = 74.8

# Modules compiled by Cython, which coverage cannot trace.
UNTRACKED_MODULES = [
    "design3d/nurbs/fitting.py",
    "design3d/nurbs/operations.py",
]


def main(report_path: str = "coverage.json") -> int:
    """Checks the coverage report against the thresholds, and returns the exit code."""
    with open(report_path, "r", encoding="utf-8") as file:
        report = json.load(file)

    errors = []
    project_coverage = report["totals"]["percent_covered"]
    print(f"Project coverage: {project_coverage:.2f} % (min {MIN_PROJECT_COVERAGE} %)")
    if project_coverage < MIN_PROJECT_COVERAGE:
        errors.append(f"Project coverage {project_coverage:.2f} % is below {MIN_PROJECT_COVERAGE} %")

    min_file_coverage = 100.0
    for file_name, data in sorted(report["files"].items()):
        if any(file_name.endswith(module) for module in UNTRACKED_MODULES):
            print(f"{file_name}: untracked")
            continue
        file_coverage = data["summary"]["percent_covered"]
        min_file_coverage = min(min_file_coverage, file_coverage)
        if file_coverage < MIN_FILE_COVERAGE:
            errors.append(f"{file_name} coverage {file_coverage:.2f} % is below {MIN_FILE_COVERAGE} %")

    for error in errors:
        print(f"[Coverage] {error}")
    if errors:
        return 1

    if project_coverage - MIN_PROJECT_COVERAGE >= 0.1:
        print(f"[Coverage] Raise MIN_PROJECT_COVERAGE to {int(project_coverage * 10) / 10}")
    if min_file_coverage - MIN_FILE_COVERAGE >= 0.1:
        print(f"[Coverage] Raise MIN_FILE_COVERAGE to {int(min_file_coverage * 10) / 10}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
