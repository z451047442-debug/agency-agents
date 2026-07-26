# Changelog

## [2.1.1] — 2026-07-26 — Pipeline & Schema Hardening

### Fixed
- **CI/CD**: `nightly-full-audit.yml` replaced removed `scripts/check-deps.sh` with `analyze-deps.py --validate`
- **Schema**: `agent-index.schema.json` added `version`, `date_added`, `lifecycle`, `vibe` fields (was 1,399 validation errors)
- **Schema**: `tools.schema.json` aligned `format` enum, `dest` type, and `required` with actual `tools.json` data (was 42 errors)
- **Security**: `SECURITY_EXEMPT_AGENTS` expanded from 4 to 12 agents to reduce false-positive warnings
- **Code**: 4 batch scripts now use atomic tmp→replace writes to prevent file corruption
- **Code**: `batch-date-added.py` added missing `newline="\n"` to prevent CRLF on Windows
- **Code**: 4 `except Exception: pass` blocks replaced with specific exception types
- **Docs**: Removed 4 stale category references from `CONTRIBUTING.md`
- **Docs**: `CONTRIBUTING_zh-CN.md` synced categories + added Getting Started, Contribution Tiers, PR Scope, Tool Compatibility
- **Docs**: Updated agent/category counts across 4 files

## [2.1.0] — 2026-07-26 — Multi-Expert Audit & Architecture Refinement

### Changed
- **Scoring**: Unified to v7 engine (0-18 scale) with calibrated thresholds; removed v3/v5/v6
- **Categories**: Merged security→cybersecurity, hr-tech→hr, securities→finance, network-engineering→infrastructure (66→62)
- **Agent count**: 1,406→1,399 due to deduplication of 7 overlapping security agents

### Fixed
- **AGENTS.json**: ~2,200 quote-format inconsistencies resolved via `get_field()` YAML quote stripping
- **README-zh.md**: 4 data inconsistencies fixed (domains, tools, agent counts, acknowledgments)
- **CLAUDE.md**: File size threshold corrected (10 KB→55 KB); check-deps references updated
- **install/lib.sh**: ALL_DIVISIONS expanded from 16 to 61 categories

### Removed
- `scripts/check-deps.py` / `check-deps.sh` — thin wrappers, superseded by `analyze-deps.py --validate`
- `security/` directory — 8 agents migrated to `cybersecurity/`

### Added
- 7 previously undocumented scripts now documented in CLAUDE.md (ab-test, validate-index, shard-index, etc.)

## [2.0.4] — 2026-07-25 — Bug Fixes & Quality Hardening

### Fixed
- **High**: `scripts/_shared/validators.py` — `find_broken_links()` now skips external `http(s)://` URLs, preventing false-positive broken link reports
- **High**: `scripts/score-agents.py` — `relative_to(REPO)` wrapped in try/except to handle file paths outside the repo (fixes pre-commit hook quality gate crash)
- **Medium**: `scripts/build-architecture.py` — fallback test count changed from sentinel `-1` to `0` for clean output rendering
- **Medium**: `scripts/convert.py` — `gold` color corrected from duplicate `#EAB308` to `#FFD700`; docstring fixed from "21" to "20" CSS colour names

### Cleaned
- Removed 28 one-off batch processing scripts and data artifacts (`upgrade_b_to_a*.py`, `fixup-*.py`, `batch-*.py`, `quality-dashboard.html`, `scores-data.json`, etc.)
- `pyproject.toml` — removed stale coverage omit and ruff per-file-ignores entries for deleted scripts

### Improved
- Test coverage threshold raised from 80% to 90%
- Added 40+ new tests covering `--cross-stats`, `--cycles`, `scenario_search`, `record_usage`, `prompt_for_feedback`, and `phase_distribution` CLI paths
- `scripts/telemetry.py` excluded from coverage (opt-in utility)
- Pre-commit hook hardened: `MAINTAINERS.md` and `QUICKSTART.md` excluded from agent scan; temp files now created inside repo for scorer compatibility

## [2.0.3] — 2026-07-25 — Consistency & Quality Baseline

### Fixed
- **High**: `CLAUDE.md` — agent count corrected 1200+→1406, categories 50+→66
- **High**: `ARCHITECTURE.md` — version aligned (2.0.1→2.0.2), NEXUS phases 8→7, coverage threshold field fixed, integration targets 6→14 with full tool table
- **High**: `scripts/_shared/validators.py` — removed non-existent `medical-devices` from HIGH_RISK_CATEGORIES (caused incorrect risk tiering)
- **High**: `pyproject.toml` — fixed `add_methodology_framework*` omit glob (underscore→hyphen), added 3 missing historical scripts to omit list
- **Medium**: `scripts/build-architecture.py` — fixed E402 (import not at top of file)
- **Medium**: `scripts/nexus-orchestrator.py` — fixed E402 (import not at top of file)
- **Medium**: `scripts/telemetry.py` — fixed E402 (import not at top of file)
- **Medium**: `scripts/feedback.py` — fixed E402 (import not at top of file)

### Changed
- **Low**: `pyproject.toml` — added per-file-ignores for legacy maintenance scripts to suppress known ruff warnings
- **Low**: `scripts/quality.py` — added comment explaining `--cov-fail-under=35` vs CI 80% threshold

## [2.0.2] — 2026-07-24 — Code Quality & Documentation Audit

### Fixed
- **Critical**: `scripts/score-agents.py` — fixed banker's rounding in health_score (`round(0.5)=0` → `int(x+0.5)`)
- **Critical**: `scripts/score-agents.py` — Top 10/Bottom 10 now sort by version-correct score field (v5/v6/v7)
- **Critical**: `scripts/score-agents.py` — Bottom 10 display uses version-specific risk_tier field
- **Critical**: `scripts/lint-agents.py` — handles `UnicodeDecodeError` gracefully instead of crashing
- **Critical**: `scripts/install.sh` — parallel mode passes multi-word arguments via positional `$1`
- **High**: `schemas/agent-frontmatter.schema.json` — added `slate` to color pattern
- **High**: `divisions.json` — fixed label casing: Hr→HR, Hr Tech→HR Tech, Iot→IoT
- **High**: `pyproject.toml` — added `bandit>=1.7` to dev dependencies
- **High**: `requirements.txt` — converted from lock-file to declarative dependency format
- **High**: `README.md` / `README-zh.md` — agent count 1,366→1,406, categories 65→66, tools 26→14
- **High**: `ARCHITECTURE.md` — fixed Phase 2 duplication, 8→7 phases, test count unified, version updated
- **High**: `docs/DEVELOPMENT.md` — Python version aligned with pyproject.toml (3.11+→3.10+)
- **High**: `docs/TIERS.md` — updated generation metadata to v7 engine

### Removed
- 19 root-level junk files: development scripts, empty files, leftover artifacts
- 3 `_solution/` .csproj files (staged for deletion)

## [2.0.1] — 2026-07-24 — Production Readiness Audit

### Fixed
- **Critical**: `pyproject.toml` — moved `--cov-fail-under=80` from global pytest addopts to `[tool.coverage.report]` (fixes cross-platform CI crashes without pytest-cov)
- **Critical**: `scripts/check-deps.py` — added `if __name__ == "__main__"` guard to prevent import-triggered subprocess execution
- **Critical**: `scripts/_shared/frontmatter.py` — `get_field()` now parses multi-line YAML block scalars (`|`, `>`)
- **Critical**: `scripts/_shared/validators.py` — `git_last_modified()` handles `ValueError`; `find_broken_links()` strips URI fragments before path check
- **Critical**: `scripts/lint-agents.py` — broken link detection strips URI fragments (e.g., `file.md#section`)
- **Critical**: `.release-please-manifest.json` / `release-please-config.json` — version aligned with `pyproject.toml` (2.0.0)
- **High**: `scripts/score-agents.py` — `--v5`/`--v6`/`--v7` flags now show correct version scores in terminal output
- **High**: `scripts/convert.py` — `run_hermes()` catches `CalledProcessError` + `FileNotFoundError` without aborting pipeline
- **High**: `CLAUDE.md` — fixed reference to non-existent `scripts/check-tools.py`
- **High**: `schemas/tools.schema.json` — added `kebab` to required fields, matching `check-tools.sh` validator
- **High**: `schemas/agent-frontmatter.schema.json` — fixed `$id` URI format consistency
- **High**: `scripts/batch-add-deps.py` — aligned hardcoded exclude list with `_shared/discovery.py` EXCLUDE_DIRS
- **High**: `.github/workflows/quality-gate.yml` — fixed threshold/comment mismatch (v6 >=10)
- **High**: `.github/workflows/ci.yml` — raised score-gate threshold from 6 to 9 (v5 scale 0-15)
- **Medium**: `README.md` / `README-zh.md` — agent count updated 1,292 -> 1,406
- **Medium**: `ARCHITECTURE.md` — test count updated 1,153 -> 1,161
- **Medium**: `.github/workflows/check-divisions.yml` — added Python setup step
- **Medium**: `.gitignore` — added `.mypy_cache/` and `.ruff_cache/` entries
- **Low**: `scripts/git-hooks/pre-commit` — cross-platform Python detection + temp file paths
- **Tests**: `tests/test_check_deps.py` — adapted to call `mod.main()` after module-level guard

## [2.0.0] — 2026-07-18 — Project Renaissance

### Scoring Engine v2
- 5-dimension scoring with real variance (StdDev 0.3 to 1.64)
- New Content Originality dimension: boilerplate penalty + tool richness
- Distribution statistics (mean/stddev/quartiles) in all reports
- Fixed banker's rounding bug (round to int(x+0.5))

### Gold Agent Quality
- 151 Gold agents at 100% A-grade (up from 35 at 26%)
- 10-round automated enhancement pipeline
- 152 template phrases removed via boilerplate cleaner

### NEXUS Validation
- First complete 7-phase NEXUS project (nexus-validation)
- Gate automation with JSON evidence files

### New Tools (11 scripts)
- agency CLI: 14 commands via pip install
- A/B test framework (5 cases, 90% avg)
- Telemetry: opt-in usage tracking + recommendations
- Automated enhancement pipeline (4 scripts)
- Quality Dashboard (Chart.js)

### Infrastructure
- pip install agency-agents with build-system config
- score-agents.sh: 380-line bash to 7-line wrapper
- CI thresholds recalibrated for v2 distribution

---

## [1.0.0] — 2026-07-10

### Added
- CI pipeline (`.github/workflows/ci.yml`): lint → validate → test → score gate
- `scripts/_shared/` package with `discovery`, `frontmatter`, `terminal` utilities
- `load_module()` helper for importing hyphen-named Python modules cleanly
- `jsonschema` to dev dependencies (3 schema validation tests now run)
- `pyproject.toml` with ruff, mypy, pytest, coverage configuration

### Changed
- **Breaking (internal):** Migrated `SourceFileLoader` → `importlib.util` across all scripts (Python 3.12+ compatibility)
- Unified color helpers, REPO, EXCLUDE_DIRS, frontmatter parsing via `_shared/` imports
- `get_body()` now returns original content when no frontmatter delimiters exist (defensive fallback)
- `requirements.txt` converted from UTF-16 to UTF-8

### Fixed
- `jsonschema` import causing 3 skipped schema validation tests
- Redundant `depends_on` inline parsing in `get_list_field()`
- Test monkeypatching broken by `_shared` import indirection (REPO aliasing)

### Removed
- 150+ lines of duplicated frontmatter/color/discovery code across 9 scripts
- All `importlib.machinery.SourceFileLoader` usage (deprecated in Python 3.12)
- Redundant `requirements-dev.txt`

---

## [0.1.0] — 2026-07-03

### Added
- Initial release: 1184 agent personality definitions across 50+ categories
- Agent validation (YAML frontmatter + structure checks)
- Dependency analysis (`depends_on`) with 100% coverage
- Quality scoring pipeline (A-D grades)
- Multi-tool integration: Claude Code, Cursor, Copilot, Gemini CLI, Windsurf, Codex, Kimi
- NEXUS multi-agent orchestration framework (7-phase pipeline)
- AGENTS.json index generation
