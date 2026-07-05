# 🛠️ Development Setup

> Set up your local environment to contribute agents, fix scripts, or add tool integrations.

---

## Prerequisites

| Tool | Minimum Version | Check |
|------|----------------|-------|
| **Python** | 3.11+ | `python --version` |
| **Git** | 2.30+ | `git --version` |
| **bash** | 3.2+ | `bash --version` |
| **Git Bash** (Windows) | Latest | Included with Git for Windows |

**Windows users**: If you do not have bash, use Git Bash (bundled with [Git for Windows](https://git-scm.com/download/win)). The Python scripts are fully cross-platform and do not require bash. Shell scripts (`*.sh`) run in Git Bash or WSL.

---

## Clone and Setup

```bash
git clone https://github.com/z451047442-debug/agency-agents.git
cd agency-agents

# Install Python test dependencies
pip install -r requirements-dev.txt
```

The only Python dependencies are `pytest>=7.0` and `pyyaml>=6.0`. The project has no runtime code -- these are for testing and validation only.

---

## Running Tests

All tests live under `tests/` and use pytest:

```bash
# Run all tests
python -m pytest tests/ -v

# Run the lint-agent tests only
python -m pytest tests/test_lint_agents.py -v

# Run the converter tests only
python -m pytest tests/test_convert.py -v

# Run a specific test
python -m pytest tests/test_lint_agents.py::TestGetField -v
```

Tests are imported as modules (not subprocesses) so individual functions can be unit-tested directly. The test conftest (`tests/conftest.py`) provides shared fixtures including `SAMPLE_AGENT_CONTENT` and a `make_agent_file()` helper.

**Writing tests**: When fixing a script or adding a feature, include a test. The CI runs `pytest` on ubuntu, macos, and windows -- so tests must be cross-platform (use `pathlib.Path`, not `os.path` string concatenation).

---

## Running the Linter

Validate agent files against the quality standard:

```bash
# Lint everything
python scripts/lint-agents.py --all

# Lint specific files
python scripts/lint-agents.py path/to/agent.md

# Skip git-freshness checks (useful in CI on shallow clones)
python scripts/lint-agents.py --all --no-freshness

# Lint only changed files (respects CI diff)
python scripts/lint-agents.py file1.md file2.md
```

The linter enforces:
- **ERROR**: Missing required frontmatter fields (`name`, `description`, `emoji`, `color`)
- **WARN**: Missing recommended sections, file < 100 words, file > 10 KB, missing `nexus_roles`

---

## Pre-Commit Hook Setup

The repo includes a pre-commit hook that auto-validates staged agent files before each commit:

```bash
cp scripts/git-hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

On commit, the hook:
1. Collects all staged `.md` files (skipping `docs/`, `examples/`, `integrations/`)
2. Runs `lint-agents.py` on each agent file
3. Reminds you to run `generate-index.sh` if `AGENTS.json` is not staged alongside agent changes
4. Blocks the commit on any ERROR-level findings

---

## CI Overview

All CI workflows run on pull requests and pushes to `main`. See `.github/workflows/` for the full source.

### Multi-platform (ubuntu, macos, windows)

| Workflow | What It Does |
|----------|-------------|
| **Lint agents** | Runs `lint-agents.py` on changed `.md` files + originality check |
| **Verify index** | Checks `AGENTS.json` is not stale via `generate-index.sh --check` |
| **Validate index** | Validates `AGENTS.json` against JSON schema via `validate-index.py` |
| **Python tests** | Runs `pytest tests/ -v` |
| **i18n validation** | Runs `check-i18n.py --strict` for translation coverage and encoding |

### Ubuntu-only (shell-script-heavy integration tests)

| Workflow | What It Does |
|----------|-------------|
| **Integration tests** | Runs `search-agents.sh`, `create-agent.sh`, `lint-agents.sh`, and `convert.sh --check` |
| **Check divisions** | Validates `divisions.json` consistency |
| **Check tools** | Validates `tools.json` consistency |

### On main push only

| Workflow | What It Does |
|----------|-------------|
| **Release** | Runs `release-please` to automate version bumps and changelogs |

---

## Quick Reference

| Task | Command |
|------|---------|
| Install test deps | `pip install -r requirements-dev.txt` |
| Run all tests | `python -m pytest tests/ -v` |
| Lint all agents | `python scripts/lint-agents.py --all` |
| Regenerate index | `./scripts/generate-index.sh` |
| Run converter | `python scripts/convert.py` |
| Create a new agent | `./scripts/create-agent.sh` |
| Install pre-commit hook | `cp scripts/git-hooks/pre-commit .git/hooks/pre-commit` |

---

## Next Steps

- [Contributing Guide](../CONTRIBUTING.md) -- How to add agents and submit PRs
- [Contributing Translations](CONTRIBUTING-I18N.md) -- How to add i18n translations
- [Script Architecture](SCRIPT-ARCHITECTURE.md) -- How the scripts system is organized
- [Troubleshooting](TROUBLESHOOTING.md) -- Common issues and fixes
