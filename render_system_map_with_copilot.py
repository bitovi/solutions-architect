#!/usr/bin/env python3
"""
Render output/SYSTEMS_MAP.md from output/systems_map.json using Copilot CLI.

This script is designed for "vacuum mode" where only the solutions-architect
folder is available locally. It provides Copilot with:
  1) the generated output/systems_map.json
  2) operating instructions/guardrails from SYSTEM_MAP_INSTRUCTIONS.md

The prompt enforces MCP tool usage policy:
  - Prefer RAG search MCP for discovery
  - Use GitHub MCP only when strictly necessary (rate limits)

Note:
  - This render step uses dedicated system-map instructions, not solution-planning instructions.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def debug_log(enabled: bool, message: str) -> None:
    if enabled:
        print(f"[debug] {message}")


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


def build_prompt(
    json_path: Path,
    output_path: Path,
    instructions_text: str,
    required_sections: list[str],
) -> str:
    sections = "\n".join(f"- {s}" for s in required_sections)

    return textwrap.dedent(
        f"""
        You are generating a cross-repository systems map document.

        ## Primary Inputs (must be used)
        - JSON source of truth: {json_path}
        - Operating instructions: system map instructions content below

        ## Operating Instructions (verbatim)
        ```markdown
        {instructions_text}
        ```

        ## Tool Usage Policy (strict)
        1. Treat `{json_path.name}` as primary source-of-truth for repo metadata, inferred edges, and extracted docs.
        2. Use RAG/discovery MCP first for broad searches or ambiguity resolution.
        3. Use GitHub MCP only when absolutely necessary for precision retrieval and only after JSON + RAG are insufficient.
           - Keep GitHub MCP calls minimal due to rate limits.
           - Never do broad exploratory sweeps with GitHub MCP.
        4. If needed, read README/OpenAPI files referenced in JSON to validate or clarify details.

        ## Output Requirements
        - Produce exactly one Markdown document to be written to: {output_path}
        - Include these sections at minimum:
        {sections}
        - Be factual and evidence-based. If uncertain, explicitly mark as "Unknown" and describe what evidence is missing.
        - Do not invent endpoints, ports, auth requirements, or integrations.

        ## Style Guidance
        - Optimize for AI-agent consumption (clear sections, concise bullets, explicit dependencies).
        - Include a dependency graph section (ASCII acceptable).
        - Include guardrails for future agents regarding tool usage and uncertainty handling.

        ## File Update Requirement
        - Use available tools to write/update `{output_path.name}` directly at path `{output_path}`.
        - Treat tool-driven file edits as the source of truth for final output.

        Now read `{json_path.name}` and generate the final SYSTEMS_MAP.md content.
        Output only Markdown.
        """
    ).strip() + "\n"


def run_command(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )


def run_generate_system_map(here: Path, debug: bool = False) -> Path:
    """Regenerate output/systems_map.json from repos.txt before rendering markdown."""
    generator = here / "generate_system_map.py"
    if not generator.exists():
        die(f"Missing generator script: {generator}")

    cmd = [sys.executable, str(generator)]
    debug_log(debug, f"generator command: {' '.join(shlex.quote(c) for c in cmd)}")
    print("Generating output/systems_map.json from repos.txt...")
    result = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        die("Failed to generate output/systems_map.json from repos.txt.")

    if result.stdout:
        debug_log(debug, "generator stdout:\n" + result.stdout.strip())
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    json_path = here / "output" / "systems_map.json"
    if not json_path.exists() or json_path.stat().st_size == 0:
        die(f"Generator completed but output/systems_map.json is missing/empty: {json_path}")
    debug_log(debug, f"output/systems_map.json size={json_path.stat().st_size} bytes")
    return json_path


def require_copilot_cmd() -> list[str]:
    """Return Copilot CLI base command or fail with install guidance."""
    if shutil.which("copilot"):
        return ["copilot"]
    die(
        "Unable to locate `copilot` in PATH. Install the new Copilot CLI "
        "(e.g. `npm install -g @github/copilot`, `brew install copilot-cli`, "
        "or `winget install GitHub.Copilot`) and run again."
    )


def build_auto_copilot_command(base: list[str], prompt: str, model: str, add_dir: Path) -> list[str]:
    """Build a stable Copilot CLI invocation for one-shot markdown rendering."""
    cmd = [*base, "-p", prompt, "-s", "--allow-all-tools", "--add-dir", str(add_dir)]
    if model:
        cmd.extend(["--model", model])
    return cmd


def format_auto_command_preview(base: list[str], model: str, add_dir: Path) -> str:
    """Render a readable command preview without embedding full prompt text."""
    preview = [*base, "-p", "<generated-prompt>", "-s", "--allow-all-tools", "--add-dir", str(add_dir)]
    if model:
        preview.extend(["--model", model])

    return " ".join(shlex.quote(c) for c in preview)


def print_copilot_failure_diagnostics(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        print(result.stdout, file=sys.stderr)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    print(
        "Hint: Ensure you're authenticated via `gh auth login` or `copilot` + `/login`.\n"
        "Hint: You may also set COPILOT_GITHUB_TOKEN / GH_TOKEN / GITHUB_TOKEN if desired.",
        file=sys.stderr,
    )


def debug_log_subprocess_result(debug: bool, name: str, result: subprocess.CompletedProcess[str]) -> None:
    if not debug:
        return
    debug_log(True, f"{name} exit_code={result.returncode}")
    if result.stdout:
        debug_log(True, f"{name} stdout (first 500 chars):\n{result.stdout[:500]}")
    if result.stderr:
        debug_log(True, f"{name} stderr (first 500 chars):\n{result.stderr[:500]}")


def append_chat_log(log_path: Path, label: str, result: subprocess.CompletedProcess[str]) -> None:
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

    parser = argparse.ArgumentParser(
        description="Generate output/systems_map.json from repos.txt and render output/SYSTEMS_MAP.md with Copilot CLI"
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        default=str(here / "output" / "SYSTEMS_MAP.md"),
        help="Path for generated output/SYSTEMS_MAP.md",
    )
    parser.add_argument(
        "--instructions",
        dest="instructions_path",
        default=str(here / "SYSTEM_MAP_INSTRUCTIONS.md"),
        help="Path to system-map rendering instructions (default: SYSTEM_MAP_INSTRUCTIONS.md)",
    )
    parser.add_argument(
        "--prompt-out",
        dest="prompt_out",
        default=str(here / "output" / ".copilot_system_map_prompt.md"),
        help="Path to write generated prompt",
    )
    parser.add_argument(
        "--chat-log",
        dest="chat_log",
        default=str(here / "output" / ".copilot_system_map_chat.log.md"),
        help="Path to append Copilot stdout/stderr logs.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute Copilot CLI command template (otherwise only writes prompt)",
    )
    parser.add_argument(
        "--copilot-cmd-template",
        dest="copilot_cmd_template",
        default=os.environ.get("COPILOT_CMD_TEMPLATE", ""),
        help=(
            "Shell command template used when --run is set. Must include "
            "{prompt_file} and {output_file}. Example: "
            "'copilot -p \"$(cat {prompt_file})\" -s > {output_file}'"
        ),
    )
    parser.add_argument(
        "--model",
        default="",
        help="Optional Copilot model override (passed as --model).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logs for generator/copilot command execution.",
    )
    args = parser.parse_args()
    copilot_env = prepare_copilot_env_for_subprocess()

    debug_log(args.debug, f"workspace={here}")
    json_path = run_generate_system_map(here, debug=args.debug).resolve()
    output_path = Path(args.output_path).resolve()
    instructions_path = Path(args.instructions_path).resolve()
    prompt_out = Path(args.prompt_out).resolve()
    chat_log = Path(args.chat_log).resolve()
    debug_log(args.debug, f"json_path={json_path}")
    debug_log(args.debug, f"output_path={output_path}")
    debug_log(args.debug, f"instructions_path={instructions_path}")
    debug_log(args.debug, f"chat_log={chat_log}")

    if not instructions_path.exists():
        die(
            "Instructions file not found: "
            f"{instructions_path}. Use --instructions to supply a valid system-map instructions file."
        )

    instructions_text = instructions_path.read_text(encoding="utf-8")

    required_sections = [
        "1) System at a glance",
        "2) Auth model (shared assumptions)",
        "3) Repository map",
        "4) Service dependency graph",
        "5) Common ports and env vars",
        "6) Agent playbook",
        "7) Known constraints / non-goals",
        "8) Canonical references per repo",
    ]

    prompt = build_prompt(
        json_path=json_path,
        output_path=output_path,
        instructions_text=instructions_text,
        required_sections=required_sections,
    )

    prompt_out.parent.mkdir(parents=True, exist_ok=True)
    prompt_out.write_text(prompt, encoding="utf-8")
    print(f"Wrote prompt: {prompt_out}")
    debug_log(args.debug, f"prompt size={prompt_out.stat().st_size} bytes")

    auto_preview = format_auto_command_preview(require_copilot_cmd(), args.model, here)
    print(f"Auto command preview: {auto_preview}")

    if not args.run:
        print(
            "Dry run complete. Re-run with --run to execute Copilot, or provide "
            "--copilot-cmd-template for custom execution behavior."
        )
        return

    template = (args.copilot_cmd_template or "").strip()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if template:
        if "{prompt_file}" not in template or "{output_file}" not in template:
            die("Command template must include both {prompt_file} and {output_file} placeholders.")

        command = template.format(
            prompt_file=shlex.quote(str(prompt_out)),
            output_file=shlex.quote(str(output_path)),
        )
        debug_log(args.debug, f"template command: {command}")
        print(f"Running Copilot command (this could take a while): {command}")
        result = run_command(command)
        debug_log_subprocess_result(args.debug, "copilot-template", result)
        append_chat_log(chat_log, "copilot-template", result)
        if result.returncode != 0:
            print_copilot_failure_diagnostics(result)
            die(f"Copilot command failed with exit code {result.returncode}")
    else:
        base = require_copilot_cmd()
        cmd = build_auto_copilot_command(base=base, prompt=prompt, model=args.model, add_dir=here)
        print(
            "Running Copilot command (this could take a while): "
            f"{format_auto_command_preview(base, args.model, here)}"
        )
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=False,
            env=copilot_env,
        )
        debug_log_subprocess_result(args.debug, "copilot", result)
        append_chat_log(chat_log, "copilot", result)
        if result.returncode != 0:
            print_copilot_failure_diagnostics(result)
            die(f"Copilot command failed with exit code {result.returncode}")
    debug_log(args.debug, f"chat log appended: {chat_log}")

    if not output_path.exists() or output_path.stat().st_size == 0:
        die(
            f"Copilot command succeeded but output is missing/empty: {output_path}. "
            f"See chat log for details: {chat_log}"
        )

    debug_log(args.debug, f"output markdown size={output_path.stat().st_size} bytes")
    print(f"Wrote markdown: {output_path}")


if __name__ == "__main__":
    main()
