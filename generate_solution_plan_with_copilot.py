#!/usr/bin/env python3
"""
Generate output/SOLUTION_PLAN.md from a user request using Copilot CLI.

This is step 2 of the solutions-architect workflow:
1) output/SYSTEMS_MAP.md already exists (step 1)
2) This script produces an architected implementation plan using:
   - output/SYSTEMS_MAP.md
   - SOLUTION_PLANNING_INSTRUCTIONS.md

The script is intentionally minimal:
- one required CLI argument: the planning request
- fixed input/output paths
- no optional flags
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        os.environ[key] = value


def prepare_copilot_env_for_subprocess() -> dict[str, str]:
    """Build environment for Copilot subprocess (assumes user is already authenticated)."""
    return os.environ.copy()


def require_copilot_cmd() -> list[str]:
    if shutil.which("copilot"):
        return ["copilot"]
    die(
        "Unable to locate `copilot` in PATH. Install the new Copilot CLI "
        "(e.g. `npm install -g @github/copilot`, `brew install copilot-cli`, "
        "or `winget install GitHub.Copilot`) and run again."
    )


def build_prompt(
    request: str,
    systems_map_path: Path,
    instructions_path: Path,
    output_path: Path,
    instructions_text: str,
) -> str:
    return textwrap.dedent(
        f"""
        You are an AI Solutions Architect generating an implementation plan.

        ## User Request
        {request}

        ## Primary Inputs (must be used)
        - Systems map: {systems_map_path}
        - Planning instructions: {instructions_path}

        ## Planning Instructions (verbatim)
        ```markdown
        {instructions_text}
        ```

        ## Source and Tooling Policy (strict)
        1. Treat `SYSTEMS_MAP.md` as the primary architecture context.
        2. Follow all constraints and guardrails from `SOLUTION_PLANNING_INSTRUCTIONS.md`.
        3. If uncertainty remains, mark it explicitly as Unknown and list missing evidence.
        4. Do not invent implementation details, contracts, or dependencies.

        ## Output Requirements
        - Produce exactly one Markdown plan at: {output_path}
        - The plan must include all required sections specified in `SOLUTION_PLANNING_INSTRUCTIONS.md`.
        - Keep recommendations execution-ready and scoped by impacted system/repo.

        ## File Update Requirement
        - Use available tools to write/update `{output_path.name}` directly at path `{output_path}`.
        - Treat tool-driven file edits as the source of truth for final output.

        Now read SYSTEMS_MAP.md and generate the final solution plan.
        Output only Markdown.
        """
    ).strip() + "\n"


def append_chat_log(log_path: Path, result: subprocess.CompletedProcess[str], label: str = "copilot") -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    content = (
        f"\n\n# {label} @ {ts}\n"
        f"- exit_code: {result.returncode}\n\n"
        "## stdout\n\n"
        "```text\n"
        f"{result.stdout or ''}"
        "\n```\n\n"
        "## stderr\n\n"
        "```text\n"
        f"{result.stderr or ''}"
        "\n```\n"
    )
    with log_path.open("a", encoding="utf-8") as f:
        f.write(content)


def main() -> None:
    here = Path(__file__).resolve().parent
    load_dotenv(here / ".env")
    copilot_env = prepare_copilot_env_for_subprocess()

    parser = argparse.ArgumentParser(
        description="Generate output/SOLUTION_PLAN.md from a planning request using Copilot CLI"
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

    output_dir = (here / "output").resolve()
    systems_map_path = (output_dir / "SYSTEMS_MAP.md").resolve()
    instructions_path = (here / "SOLUTION_PLANNING_INSTRUCTIONS.md").resolve()
    output_path = (output_dir / "SOLUTION_PLAN.md").resolve()
    prompt_path = (output_dir / ".copilot_solution_plan_prompt.md").resolve()
    chat_log = (output_dir / ".copilot_solution_plan_chat.log.md").resolve()

    output_dir.mkdir(parents=True, exist_ok=True)

    if not systems_map_path.exists() or systems_map_path.stat().st_size == 0:
        die(
            f"Missing or empty systems map: {systems_map_path}. "
            "Run step 1 first to generate output/SYSTEMS_MAP.md."
        )
    if not instructions_path.exists() or instructions_path.stat().st_size == 0:
        die(f"Missing or empty planning instructions: {instructions_path}")

    instructions_text = instructions_path.read_text(encoding="utf-8")
    prompt = build_prompt(
        request=request,
        systems_map_path=systems_map_path,
        instructions_path=instructions_path,
        output_path=output_path,
        instructions_text=instructions_text,
    )

    prompt_path.write_text(prompt, encoding="utf-8")
    print(f"Wrote prompt: {prompt_path}")

    copilot_cmd = require_copilot_cmd()
    cmd = [*copilot_cmd, "-p", prompt, "-s", "--allow-all-tools", "--add-dir", str(here)]

    print("Running Copilot to generate SOLUTION_PLAN.md (this could take a while)...")
    result = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
        env=copilot_env,
    )
    append_chat_log(chat_log, result, label="copilot")

    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        die(
            f"Copilot command failed with exit code {result.returncode}. "
            f"See log: {chat_log}"
        )

    if not output_path.exists() or output_path.stat().st_size == 0:
        die(
            f"Copilot command succeeded but output is missing/empty: {output_path}. "
            f"See log: {chat_log}"
        )

    print(f"Wrote markdown: {output_path}")
    print(f"Copilot transcript: {chat_log}")


if __name__ == "__main__":
    main()
