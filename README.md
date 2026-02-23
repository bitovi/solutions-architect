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
6. Ask AI architect for a plan

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

If Copilot returns auth errors, open an interactive session and run `/login`:

```bash
copilot
```

## Files

- `SOLUTION_PLANNING_INSTRUCTIONS.md` - AI solutions architect planning guide (step 2)
- `SYSTEM_MAP_INSTRUCTIONS.md` - step-1 instructions for rendering SYSTEMS_MAP.md
- `SYSTEMS_MAP.md` - AI-generated system map in context
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
