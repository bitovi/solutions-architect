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
5. Ask AI architect for a plan

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

## Files

- `AGENTS.md` - AI solutions architect operating guide
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
