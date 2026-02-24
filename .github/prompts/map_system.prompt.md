You are generating a cross-repository systems map document.

## Required workflow (in order)
1. **Fetch Docker Compose first using GitHub MCP.**
   - Start by reading `bitovi-training/service-infra/docker-compose.yml` via the GitHub MCP.
   - Use that file to determine which initial repositories are relevant. 
   - As you do your research, you must add additional repos to your relevant set as you discover them, making sure you uncover all services and their interconnections.
   - Treat any shared libraries or middleware referenced in imports/config as new repositories to investigate.

2. **Run Enterprise Code Search for system linkages.**
   - Use #tool:enterprisecode/search to find architecture-relevant connections across the relevant repos (service-to-service calls, shared auth/config, contracts, infra references, entrypoints).

3. **Use GitHub file fetch for precision when needed.**
   - If search results are snippets or ambiguous, use #tool:github/get_file_contents to fetch full files needed to confirm exact behavior.

## Guidelines
1. **Use subagents for your discovery process.**
   - Create a subagent for each repository you need to investigate. This will help you keep track of your findings and maintain a clear workflow.
2. **No unverified externalities.**
   - If a related dependency appears in code, either investigate its repository with a subagent or mark the behavior as unknown if it is inaccessible.

## Output requirements
- Produce exactly one Markdown document at `output/SYSTEMS_MAP.md`.
- Be evidence-based and concise.
- If something cannot be verified, mark it as **Unknown**.
- Do not invent integrations, endpoints, ports, or auth behavior.

Output only Markdown.
