# CLAUDE.md — The Agency

## Project overview

The Agency is a collection of 1000+ AI agent personality definitions (`.md` files with YAML frontmatter) organized into 50+ industry categories. Each agent file defines a specialized expert — its identity, mission, workflows, deliverables, and communication style. These files are installed into AI coding tools (Claude Code, Copilot, Cursor, Windsurf, Gemini CLI, etc.) to provide on-demand domain expertise.

The project has **no runtime code** — it is a content repository. Python scripts under `scripts/` handle installation, linting, validation, indexing, and tool-specific integration. Shell scripts in the same directory are thin wrappers around their Python counterparts.

## Common commands

```bash
# Validate all agent files (YAML frontmatter + structure checks)
# Python is the canonical implementation; shell scripts are thin wrappers
./scripts/lint-agents.sh               # wrapper -> Python (Linux/macOS)
python scripts/lint-agents.py --all    # Python (cross-platform)
python scripts/lint-agents.py path/to/agent.md
python scripts/lint-agents.py --all --no-freshness  # skip git date check (faster)

# Validate specific changed files (used in CI)
./scripts/lint-agents.sh path/to/agent.md
python scripts/lint-agents.py path/to/agent.md

# Install agents into Claude Code (no convert step needed — reads .md directly)
./scripts/install.sh --tool claude-code
./scripts/install.sh --tool claude-code --division engineering,design

# Generate integration files for other tools (Cursor, Copilot, Gemini CLI, etc.)
# Run BEFORE installing those tools, NOT needed for Claude Code
# Python is the canonical implementation; shell scripts are thin wrappers
./scripts/convert.sh                # wrapper -> Python (all tools)
python scripts/convert.py           # all tools (Python, cross-platform)
./scripts/convert.sh --tool cursor
python scripts/convert.py --tool cursor
python scripts/convert.py --parallel --jobs 4   # parallel mode for speed

# Install agents into other tools (requires convert.sh first)
./scripts/install.sh                # interactive selector (auto-detects installed tools)

# Uninstall agents | list installed
./scripts/install.sh --uninstall --tool claude-code
./scripts/install.sh --list-installed

# Search agents by keyword or category
./scripts/search-agents.sh kubernetes
./scripts/search-agents.sh --category cybersecurity
./scripts/search-agents.sh --list-categories | --stats

# Scaffold a new agent
./scripts/create-agent.sh           # interactive
./scripts/create-agent.sh --name "My Agent" --category engineering --emoji "⭐" --color "blue"

# Quality & maintenance tools
./scripts/score-agents.sh            # quality scoring (A-D grades)
./scripts/score-agents.sh --category infrastructure
./scripts/check-deps.sh              # validate depends_on references
./scripts/check-deps.sh --manifest   # output depends_on.json
./scripts/check-dupes.sh             # detect near-duplicate agents
./scripts/check-dupes.sh --threshold 0.85 --category engineering
./scripts/batch-version.sh --dry-run # preview version field additions
./scripts/batch-version.sh --category data-science

# Python code quality
python -m ruff check scripts/        # lint Python scripts
python -m ruff check scripts/ --fix  # auto-fix lint issues
python -m pytest tests/ --cov=scripts --cov-report=term-missing  # test + coverage
python -m mypy scripts/              # static type checking (optional)

# Post-install verification
./scripts/install.sh --list-installed              # show installed agents per tool
./scripts/install.sh --verify --tool claude-code    # verify install integrity
./scripts/install.sh --uninstall --agent engineering-frontend-developer --tool claude-code
./scripts/convert.sh --check                       # verify integrations/ is in sync (CI)

# Git maintenance tools
./scripts/agent-diff.sh path/to/agent.md
./scripts/agent-diff.sh --changed
./scripts/clean.sh --dry-run && ./scripts/clean.sh
./scripts/setup-hooks.sh

# Regenerate AGENTS.json index
./scripts/generate-index.sh

# Run full quality pipeline (lint + deps + score + tests)
./scripts/quality.sh          # full
./scripts/quality.sh --quick  # skip slow checks
```

## Agent file anatomy

Every agent is a single `.md` file in a category directory (e.g., `engineering/engineering-frontend-developer.md`).

### Required frontmatter

```yaml
---
name: "Agent Display Name"     # 1-120 chars
description: "One-sentence..." # 10-500 chars
emoji: 🎯                       # 1-8 chars
color: cyan                    # named color or #RRGGBB
---
```

Standard frontmatter (auto-populated, present on all agents):

```yaml
version: "1.0.0"              # semantic version of this agent definition
date_added: "2026-07-03"      # ISO date the agent was first added to the repo
```

Optional frontmatter: `vibe` (personality primer), `nexus_roles` (NEXUS pipeline phases), `depends_on` (agent IDs this agent needs).

### Required body sections

- `## 🧠 Your Identity & Memory` (or similar `Identity` header)
- `## 🎯 Your Core Mission` (or similar `Mission` header)
- `## 🚨 Critical Rules You Must Follow` (or similar `Rules` header)
- Deliverables and workflow descriptions

### Validation rules

The linter (`scripts/lint-agents.py`) enforces:
- **ERROR**: missing required frontmatter fields (`name`, `description`, `emoji`, `color`), invalid YAML, CRLF line endings
- **WARN**: missing recommended sections, file < 100 words, file > 10 KB, missing `nexus_roles`, broken internal links, filename/category mismatch, missing SOUL/AGENTS headers
- **INFO**: stale content (>12 months since last git change), empty `depends_on`

## Category directory conventions

- Each category directory contains only agent `.md` files (flat, no nesting except `game-development/` which has subdirectories per engine)
- `docs/` — NEXUS orchestration documentation (playbooks, runbooks, coordination, teams)
- `examples/` — workflow examples (not agents)
- `integrations/` — generated output from `convert.sh` (contents are `.gitignore`d except README.md)
- `schemas/` — JSON Schema for agent frontmatter validation
- `scripts/` — tooling (install, convert, lint, index generation)
- `strategy/` — Strategy consulting agents (business strategy, CEO coaching, ESG, VC advisory)
- `libraries/` — Cross-industry infrastructure agents (archivists, digital librarians)
- `specialized/` — Cross-cutting role agents (CFO, CSM, DPO, ESG officer, grant writer)
- `_solution/` — Solution-level meta-agents coordinating multi-agent teams for specific project types

## Adding a new agent

1. Pick the right category directory (or propose a new one)
2. Create `<category>-<agent-name>.md` with:
   - Valid YAML frontmatter (name, description, emoji, color required; version and date_added auto-populated by create-agent.sh)
   - Identity, Mission, Rules, Deliverables, and Workflow sections
   - At least 100 words of meaningful content
3. Run `./scripts/lint-agents.sh <your-file>` to validate
4. Run `./scripts/generate-index.sh` to update AGENTS.json

## NEXUS — multi-agent orchestration

The `docs/nexus-strategy.md` defines a 7-phase pipeline (Discovery → Strategy → Foundation → Build → Hardening → Launch → Operate) for coordinating multiple agents. Agents opt into phases via the `nexus_roles` frontmatter field. See `docs/playbooks/` for per-phase playbooks and `docs/runbooks/` for scenario-based examples.

## Project conventions

- File names: lowercase kebab-case, prefixed with category (e.g., `engineering-frontend-developer.md`)
- Content language: English (with `name` and `description` in Chinese where applicable)
- Color values: named CSS colors (`cyan`, `blue`, `teal`) or hex codes (`#E63946`)
- The `AGENTS.json` index should be regenerated after any agent add/move/delete
