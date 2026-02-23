# solutions-architect

This repository is a lightweight workspace for using AI as a solutions architect.

This generates cross-repository plans of action. You must define target repositories in `repos.txt`, configure credentials and MCP access, and use AI to produce implementation plans.

## Purpose

- Create architecture and implementation plans
- Analyze cross-system impact
- Keep planning context centralized (`SYSTEMS_MAP.md` and `systems_map.json`)

## No extra local clones required

You do not need to clone all service repositories into this folder.

Workflow:
1. Fill `repos.txt` with `owner/repo` entries
2. Fill secrets and config in `.env`
3. Fill MCP settings in `.vscode/mcp.json`
4. Generate/update system map via `python3 generate_system_map.py`
5. Render `SYSTEMS_MAP.md` from the generated JSON
6. Generate `SOLUTION_PLAN.md` from your request

## Two-step architecture workflow

- **Step 1 (system mapping):** `SYSTEM_MAP_INSTRUCTIONS.md`
  - Used only to render `SYSTEMS_MAP.md` from `systems_map.json`.
- **Step 2 (solution planning):** `SOLUTION_PLANNING_INSTRUCTIONS.md`
  - Used for architected implementation plans from user queries.

## Required setup

### 1) Fill `.env`

Create `.env` from example:

```bash
cp .env.example .env
```

You must replace:
- `WEBHOOK_URL` with your n8n RAG codesearch webhook URL
- `GITHUB_TOKEN` with a real token that can access your target repos

Note: `generate_system_map.py` requires `GITHUB_TOKEN`.

### 2) Fill `repos.txt`

`repos.txt` must contain one repository per line in `owner/repo` format.

Example:

```txt
bitovi-training/api-tests
bitovi-training/loyalty-service
bitovi-training/order-service
```

### 3) Fill `.vscode/mcp.json`

You must replace:
- `GITHUB_PAT` in the Authorization header with your real GitHub PAT (or your MCP client's env substitution syntax)

You should also verify:
- `enterpriseCode` path (`../enterprise-ai-mcp/src/index.ts`) is correct in your local workspace

### 4) Authenticate Copilot CLI (required)

Both automation scripts (`render_system_map_with_copilot.py` and `generate_solution_plan_with_copilot.py`) assume you are already authenticated with Copilot/GitHub.

Authenticate with either:

```bash
gh auth login
```

or:

```bash
copilot
```

Then run `/login` in the Copilot session.

Optional: you may also set `COPILOT_GITHUB_TOKEN`, `GH_TOKEN`, or `GITHUB_TOKEN` in your shell/.env.

## Generate or refresh the systems map

Run:

```bash
python3 generate_system_map.py
```

This reads `repos.txt` and writes `systems_map.json` with repo metadata and inferred architecture signals.

## Generate and render `SYSTEMS_MAP.md` in one flow

`render_system_map_with_copilot.py` now does the full pipeline:

1. reads `repos.txt`
2. regenerates `systems_map.json`
3. renders `SYSTEMS_MAP.md` with the **new** Copilot CLI (`copilot`)
4. uses `SYSTEM_MAP_INSTRUCTIONS.md` by default for this step

It does **not** fall back to `gh copilot`.

### Dry run (regenerate JSON + build prompt)

```bash
python3 render_system_map_with_copilot.py
```

This regenerates `systems_map.json`, writes `.copilot_system_map_prompt.md`, and prints the command preview.

### Generate final markdown

```bash
python3 render_system_map_with_copilot.py --run
```

This runs `copilot -p "<generated-prompt>" -s --allow-all-tools --add-dir <solutions-architect-dir>` and writes `SYSTEMS_MAP.md`.

Optional:

- `--model <MODEL>` to pin a specific Copilot model
- `--copilot-cmd-template '...'` for custom execution behavior
- `--debug` to print extra execution details (command info, file sizes, subprocess snippets)
- `--instructions <PATH>` to provide a different system-map instruction file
- `--chat-log <PATH>` to append Copilot chat/output transcript (default: `.copilot_system_map_chat.log.md`)

Important behavior:

- The script **does not write markdown content from Copilot stdout** into `SYSTEMS_MAP.md`.
- Copilot is expected to update `SYSTEMS_MAP.md` via its own tool-based file edits.
- Script stdout/stderr from Copilot is appended to the chat log for debugging/auditing.

If Copilot returns auth errors, re-run `gh auth login` or `copilot` + `/login`.

## Generate `SOLUTION_PLAN.md` (step 2)

Use the minimal planner script with one required argument (your planning request):

```bash
python3 generate_solution_plan_with_copilot.py "Add loyalty points expiration with customer notifications"
```

This script:

1. reads `SYSTEMS_MAP.md`
2. reads `SOLUTION_PLANNING_INSTRUCTIONS.md`
3. runs `copilot` with a generated planning prompt
4. writes `SOLUTION_PLAN.md`

It also writes:

- `.copilot_solution_plan_prompt.md` (generated prompt)
- `.copilot_solution_plan_chat.log.md` (Copilot stdout/stderr transcript)

## Run the full user-facing workflow (step 1 + step 2)

Use this to run both steps in sequence with brief status updates:

```bash
python3 run_solutions_architect_workflow.py "Add loyalty points expiration with customer notifications"
```

It will:

1. run system-map generation/render
2. report step completion
3. run solution-plan generation
4. report step completion

When entering Copilot-heavy steps, it prints `(this could take a while)`.

## Files

- `SOLUTION_PLANNING_INSTRUCTIONS.md` - AI solutions architect planning guide (step 2)
- `generate_solution_plan_with_copilot.py` - step-2 script to generate `SOLUTION_PLAN.md` from a request
- `run_solutions_architect_workflow.py` - user-facing script to run step 1 then step 2 with status output
- `SYSTEM_MAP_INSTRUCTIONS.md` - step-1 instructions for rendering SYSTEMS_MAP.md
- `SYSTEMS_MAP.md` - AI-generated system map in context
- `SOLUTION_PLAN.md` - AI-generated implementation plan for a specific request
- `systems_map.json` - generated machine-readable system map
- `generate_system_map.py` - map generator script
- `repos.txt` - repositories to analyze
- `.env.example` - env template
- `.vscode/mcp.json` - MCP server config

## Troubleshooting

- `GITHUB_TOKEN is required`
  - Add `GITHUB_TOKEN=...` to `.env`
- GitHub MCP auth fails
  - Check bearer token value in `.vscode/mcp.json`
- Wrong repos in generated map
  - Fix `repos.txt` and rerun `python3 generate_system_map.py`
