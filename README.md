# solutions-architect

This workspace is for cross-repository architecture planning using pre-made prompt files and MCP-driven discovery.

There are no Python Copilot runner scripts anymore. Prompt execution is user-controlled.

## Purpose

- Generate human-readable planning artifacts (`output/SYSTEMS_MAP.md`, `output/SOLUTION_PLAN.md`) using prompt files
- Drive system mapping from repository evidence, with Docker Compose discovery first

## Required setup

1) Create `.env` from template:

```bash
cp .env.example .env
```

2) Populate values in `.env`:
- `WEBHOOK_URL` (if your MCP flow needs it)

3) Fill `repos.txt` with one `owner/repo` per line.

4) Configure MCP (`.vscode/mcp.json`) and authenticate Copilot CLI (`copilot`, then `/login`).

## Standard workflow

### Step 1: Render `SYSTEMS_MAP.md` using prompt template

Use:
- `.github/prompts/SYSTEM_MAP_PROMP.prompt.md`

The system-map prompt now requires a **compose-first** approach:
- Use GitHub MCP first to find Docker Compose files in all relevant repos
- Build runtime topology from compose files before broader mapping

Then run the prompt with your preferred Copilot workflow and write output to:
- `output/SYSTEMS_MAP.md`

### Step 2: Generate `SOLUTION_PLAN.md` using prompt template

Use:
- `.github/prompts/SOLUTION_PLAN_PROMPT.prompt.md`
- `output/SYSTEMS_MAP.md`

Before running Copilot, replace placeholder:
- `{{USER_REQUEST}}`

Then run the prompt with your preferred Copilot workflow and write output to:
- `output/SOLUTION_PLAN.md`

## Prompt templates

- `.github/prompts/SYSTEM_MAP_PROMP.prompt.md`
- `.github/prompts/SOLUTION_PLAN_PROMPT.prompt.md`

These are canonical, pre-made prompts intended to be copied/adapted per run.

## Files

- `.github/prompts/SYSTEM_MAP_PROMP.prompt.md` - system-map prompt template (compose-first)
- `.github/prompts/SOLUTION_PLAN_PROMPT.prompt.md` - solution-plan prompt template
- `repos.txt` - repositories to analyze
- `.env.example` - environment template

## Troubleshooting

- Wrong repos in generated map
  - Fix `repos.txt` and rerun the system-map prompt workflow
