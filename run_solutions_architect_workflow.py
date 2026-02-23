#!/usr/bin/env python3
"""
User-facing workflow runner for solutions-architect.

Runs both steps in order:
1) Render output/SYSTEMS_MAP.md
2) Generate output/SOLUTION_PLAN.md
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def run_step(title: str, cmd: list[str]) -> None:
    print(f"\n{title}")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        die(f"Step failed ({result.returncode}): {' '.join(cmd)}")


def main() -> None:
    here = Path(__file__).resolve().parent
    step1_script = here / "render_system_map_with_copilot.py"
    step2_script = here / "generate_solution_plan_with_copilot.py"

    if not step1_script.exists():
        die(f"Missing script: {step1_script}")
    if not step2_script.exists():
        die(f"Missing script: {step2_script}")

    parser = argparse.ArgumentParser(
        description="Run full solutions-architect workflow: system map + solution plan"
    )
    parser.add_argument(
        "request",
        nargs="+",
        help="Planning request, e.g. \"Add loyalty points expiration with notifications\"",
    )
    args = parser.parse_args()
    request = " ".join(args.request).strip()
    if not request:
        die("Planning request is required.")

    print("Starting solutions-architect workflow...")

    print("Step 1/2: Build and render system map")
    print("- preparing system map inputs")
    run_step(
        "- running Copilot command (this could take a while): system-map render",
        [sys.executable, str(step1_script), "--run"],
    )
    print("✓ Step 1 complete: output/SYSTEMS_MAP.md updated")

    print("\nStep 2/2: Generate architected solution plan")
    run_step(
        "- running Copilot command (this could take a while): solution-plan generation",
        [sys.executable, str(step2_script), request],
    )
    print("✓ Step 2 complete: output/SOLUTION_PLAN.md updated")

    print("\nDone.")


if __name__ == "__main__":
    main()
