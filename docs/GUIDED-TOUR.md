# 🚀 5-Minute Guided Tour

Get from zero to using your first AI specialist. No coding required.

---

## Step 1: Clone and Install (60 seconds)

```bash
git clone https://github.com/z451047442-debug/agency-agents.git
cd agency-agents

# Install agents into Claude Code (reads .md files directly — no conversion needed)
./scripts/install.sh --tool claude-code
```

**Windows users**: Use Git Bash. If you don't have bash, copy agent files manually — see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

**Other tools**: Replace `claude-code` with `cursor`, `copilot`, `windsurf`, or any of the [14 supported tools](integrations/).

---

## Step 2: Pick Your First Agent (30 seconds)

Browse the [full roster in README](../README.md) or search by keyword:

```bash
./scripts/search-agents.sh frontend
./scripts/search-agents.sh --category cybersecurity
./scripts/search-agents.sh --list-categories
```

For this tour, let's use **Frontend Developer** — a React/TypeScript specialist.

---

## Step 3: Use It (3 minutes)

### In Claude Code

Start Claude Code in your project, then invoke the agent:

```
@frontend-developer Build me a login form component with email validation
```

The agent loads with its full personality, workflow, and expertise — it knows to:
- Use React + TypeScript by default
- Include form validation and error states
- Follow accessibility best practices
- Provide the complete component, not just a snippet

### In Cursor

After installing with `--tool cursor`, the agent becomes available as a rule:
1. Open Command Palette (`Ctrl+Shift+P`)
2. Type "Cursor Rules"
3. Select the agent rule for your current file

### In GitHub Copilot

After installing with `--tool copilot`, use the agent picker:
1. Open Copilot Chat
2. Click the agent dropdown
3. Select your installed specialist

---

## Step 4: Build a Team (optional)

The real power is combining agents. Here's a landing page build:

```
@backend-architect Design the API endpoints for a waitlist signup
@frontend-developer Build the React landing page with the signup form
@ui-designer Review the visual hierarchy and spacing
@seo-specialist Audit the meta tags and content structure
@evidence-collector Screenshot the final page and verify everything works
```

Each agent brings its own process, quality standards, and deliverables.

---

## What's Next?

- **Browse by domain**: [60+ categories](../README.md) from aerospace to web3
- **Real scenarios**: [Use Cases](../USE-CASES.md) — multi-agent teams in action
- **Deep orchestration**: [NEXUS](nexus-strategy.md) — coordinate agents in structured pipelines
- **Contribute**: [Add your own agent](../CONTRIBUTING.md) or request one
- **Troubleshoot**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if anything doesn't work

---

## Quick Reference

| Task | Command |
|------|---------|
| Install to Claude Code | `./scripts/install.sh --tool claude-code` |
| Install specific domains | `./scripts/install.sh --tool claude-code --division engineering,design` |
| Search agents | `./scripts/search-agents.sh kubernetes` |
| List categories | `./scripts/search-agents.sh --list-categories` |
| Create a new agent | `./scripts/create-agent.sh` |
| Validate your agent | `./scripts/lint-agents.sh path/to/agent.md` |
| Uninstall | `./scripts/install.sh --uninstall --tool claude-code` |
