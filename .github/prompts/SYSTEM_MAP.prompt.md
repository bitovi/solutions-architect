You are generating a cross-repository systems map document.

## Required workflow (in order)
1. **Fetch Docker Compose first using GitHub MCP.**
   - Start by reading `bitovi-training/service-infra/docker-compose.yml` via the GitHub MCP.
   - Use that file to determine which repositories are relevant. You may continue to add additional repos to the relevant set as you discover them.

2. **Run Enterprise Code Search for system linkages.**
   - Use #tool:enterprisecode/search to find architecture-relevant connections across the relevant repos (service-to-service calls, shared auth/config, contracts, infra references, entrypoints).

3. **Use GitHub file fetch for precision when needed.**
   - If search results are snippets or ambiguous, use #tool:github/get_file_contents to fetch full files needed to confirm exact behavior.

## Guidelines
1. **Use subagents for your discovery process.**
   - Create a subagent for each repository you need to investigate. This will help you keep track of your findings and maintain a clear workflow.

## Output requirements
- Produce exactly one Markdown document at `output/SYSTEMS_MAP.md`.
- Be evidence-based and concise.
- If something cannot be verified, mark it as **Unknown**.
- Do not invent integrations, endpoints, ports, or auth behavior.

Output only Markdown.
