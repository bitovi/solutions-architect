# SYSTEM_MAP_INSTRUCTIONS.md — System Map Rendering Instructions

Use this file for **step 1 only**: generating `SYSTEMS_MAP.md` from `systems_map.json`.

Do **not** generate implementation plans in this step.

## Goal

Produce a high-signal, evidence-based system map that describes the current architecture across repositories listed in `repos.txt`.

## Primary source of truth

- `systems_map.json` is the canonical input.
- If data is missing from JSON, mark it as **Unknown** instead of inventing details.

## Output requirements

Generate exactly one markdown document with these sections:

1. System at a glance
2. Auth model (shared assumptions)
3. Repository map
4. Service dependency graph
5. Common ports and env vars
6. Agent playbook
7. Known constraints / non-goals
8. Canonical references per repo

## Quality guardrails

- Be factual and concise.
- Prefer bullets and explicit dependency statements.
- Include a readable dependency graph (ASCII is fine).
- Clearly call out confidence/uncertainty where appropriate.
- Never invent endpoints, ports, auth flows, integrations, or ownership.
