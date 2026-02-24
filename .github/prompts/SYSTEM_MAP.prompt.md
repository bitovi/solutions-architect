You are generating a cross-repository systems map document.

## Primary Inputs (must be used)
- Repository list: `repos.txt`
- Any discovered Docker Compose files from those repos

## Operating Instructions
- Do not generate implementation plans in this step.
- If data is missing, mark it as **Unknown** instead of inventing details.

## Mandatory First Step (do this before anything else)
0. Read repos.txt so that you have the list of repositories to consider for compose discovery.
1. Use **GitHub MCP first and foremost**, not the Enterprise Code MCP, to discover Docker Compose files in every relevant repository.
2. **Use #tool:github/get_repository_tree with `recursive: true` first** for each target repository to discover candidate compose files by path.
3. Look for all common compose filenames/variants.
4. Retrieve and inspect files via #tool:github/get_file_contents after filtering.
5. Build an initial “runtime topology” from compose content (services, images/build contexts, ports, env vars, volumes, networks, depends_on).
6. After compose discovery is complete, run **#tool:enterprisecode/search** to find additional architecture-relevant files across the selected repositories (for example: READMEs, OpenAPI specs, infra docs, ADRs, auth/config files, and service entrypoints).
7. Use those Enterprise Code search results to guide targeted evidence collection for the broader system map.
8. Only after this compose-first inventory + Enterprise Code relevance search sequence is complete may you proceed with broader system mapping.

## Tool Usage Policy (strict)
1. **GitHub MCP compose discovery is required as the first operation.**
2. **Primary sequence:** #tool:github/get_repository_tree (`recursive: true`) → filter for compose filename variants → #tool:github/get_file_contents for selected matches.
3. Use tree results to collect paths first, then fetch file bodies only for candidate compose files.
4. Keep file reads minimal: do not fetch non-compose files during the compose discovery phase.
5. Stop early when the objective is satisfied (for example, if the goal is existence-only, stop after first match per repo).
6. Cache/reuse already found matches in current context; do not re-run identical scans unnecessarily.
7. **Immediately after compose discovery, run #tool:enterprisecode/search** to locate relevant non-compose artifacts needed for a large systems map.
8. Use #tool:enterprisecode/search outputs to prioritize which files to read next; avoid broad unfocused file reads.
9. After compose discovery + Enterprise Code search, use additional sources (README/OpenAPI/docs) to fill gaps and validate findings.
10. If compose files are not found for a repo, explicitly record: "No compose file found".

## Subagent Delegation Policy (strict)
- **Default to subagents for evidence collection.** Delegate targeted discovery tasks to subagents so the primary agent does not accumulate unnecessary context.
- Use subagents to gather specific artifacts from:
  - **GitHub MCP** (repository/file discovery, compose lookup, README/OpenAPI retrieval)
  - **RAG MCP(s)** (focused retrieval of architecture facts, prior decisions, and constraints)
- Keep subagent tasks narrow and outcome-based (for example: “Find all compose variants in repo X and return paths + key service metadata”).
- Ask subagents to return concise, structured summaries (bullets/tables) with file paths and evidence references—not full file dumps unless required.
- Merge only relevant subagent outputs into the parent context to minimize context-window bloat.
- If a subagent cannot find evidence, record it as **Unknown** with what was searched.

## Output Requirements
- Produce exactly one Markdown document.
- Intended output file: `output/SYSTEMS_MAP.md`
- Include these sections at minimum:
  1) Compose discovery summary (repo → compose files found)
  2) Runtime topology from compose (services, dependencies, networks)
  3) System at a glance
  4) Auth model (shared assumptions)
  5) Repository map
  6) Service dependency graph
  7) Common ports and env vars
  8) Agent playbook
  9) Known constraints / non-goals
  10) Canonical references per repo
- Be factual and evidence-based. If uncertain, explicitly mark as "Unknown" and describe what evidence is missing.
- Do not invent endpoints, ports, auth requirements, or integrations.

## Style Guidance
- Optimize for AI-agent consumption (clear sections, concise bullets, explicit dependencies).
- Include a dependency graph section (ASCII acceptable).
- Include guardrails for future agents regarding tool usage and uncertainty handling.
- Lead with compose-derived facts before README/OpenAPI-derived assumptions.
- Prefer a **subagent-first workflow** for multi-repo discovery to reduce parent-agent context load and improve traceability.

## File Update Requirement
- Use available tools to write/update `SYSTEMS_MAP.md` directly at path `output/SYSTEMS_MAP.md`.
- Treat tool-driven file edits as the source of truth for final output.

Now perform GitHub MCP compose discovery first, then run #tool:enterprisecode/search for broader relevant artifacts, then generate final `SYSTEMS_MAP.md` content.
Output only Markdown.
