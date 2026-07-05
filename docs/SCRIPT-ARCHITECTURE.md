# 🏗️ Script Architecture

> How the scripts system is organized, why Python is the canonical layer, and where each piece lives.

---

## Design Principle: Python Canonical, Shell as Wrapper

All core logic is implemented in Python as the single source of truth. Shell scripts (`*.sh`) are thin wrappers that either delegate to the Python version or provide a bash-native TUI where interactivity matters.

**Why Python?**
- Cross-platform without toolchain dependencies (works on Windows, macOS, Linux)
- Readable error messages and stack traces
- Testable -- `tests/` imports script modules directly
- One implementation to maintain, not two

**Why keep shell wrappers?**
- The interactive installer TUI (`install.sh`) is a pure-bash curses-style terminal app
- Some contributors work in bash-only environments
- Legacy tooling (pipelines, dotfiles) may call the `.sh` paths

Where both a `.py` and `.sh` exist for the same task, the `.py` is canonical. The `.sh` either delegates or has a note at the top pointing to the Python version.

---

## Directory Map

```
scripts/
├── lib.sh                   Shared bash helpers: frontmatter parsing, ANSI colors, TUI primitives
├── convert.py               Canonical converter: .md -> tool-specific formats (integrations/)
├── convert.sh               Shell wrapper: delegates to convert.py
├── lint-agents.py            Canonical linter: validates agent .md files
├── lint-agents.sh            Shell wrapper: delegates to lint-agents.py or bash-native path
├── install.sh               Interactive installer (pure bash TUI) + tool dispatch
├── install/
│   ├── lib.sh               Shared install infrastructure: progress bars, detection, selection engine
│   ├── install-claude-code.sh   Per-tool install module
│   ├── install-cursor.sh        Per-tool install module
│   ├── install-copilot.sh       Per-tool install module
│   ├── ... (14 tools total)     One module per supported tool
├── generate-index.sh         Scans all agent .md files, writes AGENTS.json
├── validate-index.py          Validates AGENTS.json against JSON schema
├── search-agents.sh           Agent search by keyword, category, or listing
├── create-agent.sh            Interactive agent scaffold generator
├── score-agents.sh            Quality scoring (A-D grades) with weighted heuristics
├── check-agent-originality.sh Near-duplicate detection via cosine similarity
├── check-deps.sh              Validates depends_on references across the roster
├── check-dupes.sh             Fuzzy duplicate detection with adjustable threshold
├── check-divisions.sh         Division consistency check (directories vs divisions.json)
├── check-tools.sh             Tool consistency check (integrations vs tools.json)
├── batch-version.sh           Bulk-add version: "1.0.0" to agents lacking it
├── batch-date-added.sh        Bulk-add date_added from git history
├── agent-diff.sh              Semantic diff between agent file versions
├── clean.sh                   Cleanup: remove temp files, generated output
├── build-hermes-plugin.py     Build Hermes plugin from agent files
├── suggest-nexus-roles.sh     Suggest NEXUS pipeline phases for an agent
├── i18n/
│   ├── agent-names-zh.json    Chinese translations (source of truth)
│   ├── localize-agents.py      Canonical Python localizer
│   ├── check-i18n.py           Coverage stats, encoding validation, template generation
│   └── check-i18n.sh           Shell wrapper: delegates to check-i18n.py
├── git-hooks/
│   ├── pre-commit             Pre-commit hook: lint staged agents, remind about AGENTS.json
│   └── README.md
└── README.md                  (scripts/README.md if it exists)
```

---

## Key Scripts

### `lint-agents.py` (canonical) / `lint-agents.sh` (wrapper)

Validates agent `.md` files. Reads YAML frontmatter, checks required fields (`name`, `description`, `emoji`, `color`), validates section structure (Identity, Mission, Rules via regex heuristics), checks word count and file size limits, warns on stale files, and validates `nexus_roles` against known phases.

### `convert.py` (canonical) / `convert.sh` (wrapper)

Reads all agent `.md` files and generates tool-specific integration files under `integrations/`. Each tool has a `convert_<tool>()` function. Supports `--parallel` for multi-threaded execution and `--check` to verify `integrations/` is in sync.

### `install.sh`

Pure-bash interactive installer with a terminal UI. Reads converted files from `integrations/` and copies/symlinks them into each tool's config directory. Dispatches per-tool logic to modules under `scripts/install/`. Supports `--division`, `--agent`, `--link`, `--uninstall`, and `--list-installed`.

### `generate-index.sh`

Scans all agent `.md` files, extracts frontmatter via awk, and writes `AGENTS.json` -- a sorted, formatted JSON catalog of every agent. The `--check` flag compares against the on-disk file and exits non-zero if they differ (used in CI).

---

## i18n Toolchain

| Script | Purpose |
|--------|---------|
| `i18n/check-i18n.py` | Reports coverage per language, finds untranslated agents, validates UTF-8 encoding, generates translation templates |
| `i18n/localize-agents.py` | Patches installed agent files with translations from `agent-names-{lang}.json` |
| `i18n/agent-names-zh.json` | Chinese translation mapping (source of truth for zh) |

To add a new language, create `agent-names-{lang}.json` following the format in the existing file. See [`CONTRIBUTING-I18N.md`](CONTRIBUTING-I18N.md) for the full guide.

---

## Testing

Tests live under `tests/` and import scripts as Python modules (not subprocesses):

```
tests/
├── __init__.py
├── conftest.py              Shared fixtures: SAMPLE_AGENT_CONTENT, make_agent_file()
├── test_lint_agents.py       Unit tests for lint-agents.py (frontmatter parsing, validation)
└── test_convert.py           Unit tests for convert.py (each converter function)
```

Tests run via `python -m pytest tests/ -v`. The only dependency is `pytest>=7.0` plus `pyyaml` (for YAML frontmatter parsing).

---

## CI Workflows (`.github/workflows/`)

| Workflow | Platforms | What It Validates |
|----------|-----------|-------------------|
| `lint-agents.yml` | ubuntu, macos, windows | Agent linting, originality check, index freshness, schema validation, pytest, i18n -- plus ubuntu-only integration tests (convert.sh --check, search, create-agent) |
| `check-divisions.yml` | ubuntu | `divisions.json` matches on-disk directories |
| `check-tools.yml` | ubuntu | `tools.json` matches on-disk integrations |
| `release.yml` | ubuntu | Release-please automation on main push |

All multi-platform jobs use `fail-fast: false` so a macos-specific issue does not hide a windows-specific one.

---

## Conventions

- **Python scripts**: Use `pathlib.Path`, `REPO = Path(__file__).resolve().parent.parent`, and `_supports_color()` for terminal output.
- **Shell scripts**: Use `set -euo pipefail`, source `lib.sh` for shared helpers (ANSI, get_field, slugify), and prefer `awk` for frontmatter extraction over external YAML parsers.
- **Per-tool modules**: Each lives in `scripts/install/install-<tool>.sh` and exposes `install_tool_<tool>()` and `uninstall_tool_<tool>()` functions sourced by `install.sh`.
- **CI**: Python-based checks run on all three OSes. Shell-heavy checks (convert.sh, create-agent.sh, search-agents.sh) run ubuntu-only to avoid redundant cross-platform coverage.
