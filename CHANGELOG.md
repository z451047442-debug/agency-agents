# Changelog

## [1.1.0](https://github.com/z451047442-debug/agency-agents/compare/v1.0.2...v1.1.0) (2026-08-01)


### Features

* add --no-cross-category-only flag to analyze-deps.py ([47dd173](https://github.com/z451047442-debug/agency-agents/commit/47dd17355ffa8ae9fa30758efced7eda67ea1efc))
* add --phase and --json flags to suggest-nexus-roles.py ([0715764](https://github.com/z451047442-debug/agency-agents/commit/071576452c5ae295cd46b386db89e574ef678640))
* add cross-platform Python installer (scripts/install.py) ([41591ba](https://github.com/z451047442-debug/agency-agents/commit/41591bae1aa851589986d8329b6570a6118878a8))
* add dedicated Reality Checker agent for NEXUS Phase 4 gate ([6649f9d](https://github.com/z451047442-debug/agency-agents/commit/6649f9d301577ad79d74f1caddb03200f1130a5b))
* add remote installer — no clone needed ([499d35f](https://github.com/z451047442-debug/agency-agents/commit/499d35f588115e886e12177c0b675dcc898e8779))
* add tags, keywords, complexity, estimated_duration to agent schema ([27542fd](https://github.com/z451047442-debug/agency-agents/commit/27542fd6cdf2cc1fd23a827ff9c02df10602fc7e))
* batch-add-hardening-v2 with keyword-based auto-detection ([be6ccab](https://github.com/z451047442-debug/agency-agents/commit/be6ccab449b3eba27cd200aa49d1ebce9ac0195a))
* batch-add-metadata.py for populating new frontmatter fields ([0557abc](https://github.com/z451047442-debug/agency-agents/commit/0557abccaa612d92976f7a0198eba93fbb310577))
* expand-thin-agents.py for batch content expansion of underweight agents ([d771d59](https://github.com/z451047442-debug/agency-agents/commit/d771d592c4679228ae175956d7fc8eea28bccca0))
* integrate oh-my-claudecode runtime + quality hardening — 2.2.0 ([e16feb6](https://github.com/z451047442-debug/agency-agents/commit/e16feb6cd1d4b3061451608da1d6160dbbc7a8de))
* linter and search support for new metadata fields ([f472569](https://github.com/z451047442-debug/agency-agents/commit/f47256997a7d792f878864a4a23f72ca0084fed5))
* match-nexus-agents.py for project-to-agent matching ([f07d51c](https://github.com/z451047442-debug/agency-agents/commit/f07d51c1dbf656fa5ef3e7293e5e31270d9a69ce))
* nexus-coverage.py for NEXUS phase coverage visualization ([a1629dd](https://github.com/z451047442-debug/agency-agents/commit/a1629ddb9143378c083c57527105555979a75a30))
* populate tags, keywords, complexity, estimated_duration for all 1400 agents ([5b8e44a](https://github.com/z451047442-debug/agency-agents/commit/5b8e44ad77c3a926340a2478ee5aef6ba1ddae1c))
* score baseline regression gate and agent discovery groupings ([2f28fad](https://github.com/z451047442-debug/agency-agents/commit/2f28fad558acb98e520102c2aee7a696567d941b))
* v2.2.0 — ECC patterns: security audit, cost tier, fix-lint, feedback loop ([e11b7b9](https://github.com/z451047442-debug/agency-agents/commit/e11b7b97b3ba29e2ad3587d28a8e2e425d58cc00))


### Bug Fixes

* add 19 missing sections across 15 agent files ([bde268a](https://github.com/z451047442-debug/agency-agents/commit/bde268acf0fb3a048ce170cf78313e0fc8236ec0))
* add agent count consistency check to CI (AGENTS.json ↔ pyproject.toml) ([cdf9b7b](https://github.com/z451047442-debug/agency-agents/commit/cdf9b7b0fc03acee9ef3d7663dba6536228b5dd8))
* bug fixes, code cleanup, and 90% coverage threshold (v2.0.4) ([8a509d4](https://github.com/z451047442-debug/agency-agents/commit/8a509d489d077b8549458507bd8ff07e5a46ee1d))
* comprehensive project audit and fix from prior session ([fe3811f](https://github.com/z451047442-debug/agency-agents/commit/fe3811f99d0ece1302fe6c106e81f4d0711798cf))
* critical bugs and documentation consistency audit ([2bc81e7](https://github.com/z451047442-debug/agency-agents/commit/2bc81e75fee3192655ec71ed47c91801b45afac3))
* data consistency and code quality hardening — 2.1.2 ([46ade0e](https://github.com/z451047442-debug/agency-agents/commit/46ade0e86d52bcf77dd2b6ef158862f65b35cbcc))
* discover nested agent dirs + exclude non-agent directories ([31f4d1d](https://github.com/z451047442-debug/agency-agents/commit/31f4d1dfb8636e1928c4ee0bf9627b167541f76e))
* make phase filter test non-vacuous, remove unused monkeypatch params ([064fc79](https://github.com/z451047442-debug/agency-agents/commit/064fc79dbe9073b122e54aa7f5d48f278158ef52))
* parser bug causing 40% nexus_roles undercount + NEXUS hardening rebalance ([9d3fa92](https://github.com/z451047442-debug/agency-agents/commit/9d3fa92ce519b6d061f61ba0049648feafdf2bfd))
* pipeline and schema hardening — 2.1.1 ([786f0b1](https://github.com/z451047442-debug/agency-agents/commit/786f0b19b7a785800cc8e48050b8735f308345eb))
* regenerate agent-browser.html (1,399 agents, 62 categories) ([a74f54f](https://github.com/z451047442-debug/agency-agents/commit/a74f54fcc43c1e74c7adcf142a3b83c44c1e6cf5))
* regenerate TIERS.md with correct agent counts (1,399 total, 62 categories) ([e49fb98](https://github.com/z451047442-debug/agency-agents/commit/e49fb98454ff7138aab481e5757123cc5ae680e6))
* remove 11 broken depends_on refs and fix 4 WARN-level issues ([132e6c5](https://github.com/z451047442-debug/agency-agents/commit/132e6c598fffc4d9787c3aee9fd9813d438ab208))
* resolve all README data inconsistencies between EN and ZH ([9b1e6e7](https://github.com/z451047442-debug/agency-agents/commit/9b1e6e75f0867d72c66a06e1d7a0fb5a93145171))
* resolve critical bugs and data inconsistencies (v2.2.1) ([140d28c](https://github.com/z451047442-debug/agency-agents/commit/140d28ca219c67263fc6f2649367d240ee8dae1b))
* resolve duplicate nexus_roles YAML keys in batch-add-hardening-v2 ([c596518](https://github.com/z451047442-debug/agency-agents/commit/c596518c97ce959da6311cbc531cc73e8bc22c14))
* sync agent counts and add Chinese category labels in agent-browser ([5faac82](https://github.com/z451047442-debug/agency-agents/commit/5faac828a33f70f56b0f25883805b2ad0c1065ff))
* v2.1.4 — bug fixes, doc accuracy, and reliability improvements ([8b80026](https://github.com/z451047442-debug/agency-agents/commit/8b800266573ad553a5186231afa6c39be8bc9494))

## [2.2.1] — 2026-07-31 — Bug Fixes & Data Consistency

### Fixed
- **Critical**: `fix-lint.py` undefined variable `ruff_output` — NameError crash on lint issue detection
- **High**: `batch-add-hardening-v2.py` duplicated fallback appending `nexus_roles` twice
- **High**: `quality-report.py` threshold mismatch with v1 scoring engine — `_estimate_fix_effort` always triggered suggestions
- **Medium**: `_shared/__init__.py` `atomic_write` caught `BaseException` instead of `Exception`
- **Medium**: `analyze-deps.py` in-place `.update()` mutation of module-level `CROSS_CATEGORY_BONUS` dict
- **Medium**: `extract-patterns.py` feedback file path/format inconsistent with `feedback.py`
- **Low**: Various ruff lint issues (unused imports, duplicate set items)

### Data
- **AGENTS.json**: regenerated — fixed 70 emoji values with literal double-quote characters; `total_categories` corrected 63→62
- **CLAUDE.md**: agent count 1399→1400 to match AGENTS.json actual

### Schema
- **agent-index.schema.json**: added missing `tags`, `keywords`, `model_tier`, `tdd_framework` properties
- **tools.schema.json**: added `omc-plugin` to format enum

### Changed
- `pyproject.toml`: version synchronized with `.release-please-manifest.json`
- `generate-index.py`: category count derived from agents list (more robust)
- `search-agents.py`: outdated error message now references `.py` instead of `.sh`

## [2.2.0] — 2026-07-29 — ECC Patterns: Security, Cost Awareness & Feedback Loop

### Added
- **Security**: `scripts/audit-security.py` — scans shell/Python/config files for dangerous patterns (curl pipe bash, hardcoded secrets, pickle, yaml.load, shell=True). Integrated into quality.py pipeline.
- **Cost Tier**: `model_tier` frontmatter field (premium/standard/economy) for cost-aware agent routing in NEXUS orchestrator
- **TDD Framework**: `tdd_framework` frontmatter field for language-specific test framework declarations (e.g. `pytest --cov`, `go test -cover`)
- **Fix-Lint**: `scripts/fix-lint.py` — incremental ruff + mypy auto-fix pipeline with --check/--apply modes
- **Feedback Loop**: `scripts/extract-patterns.py` — analyzes feedback.json to surface low-rated agents, common issues, and improvement suggestions
- **Architecture**: OMC Smart Plugin layer (5B) added to ARCHITECTURE.md/html with 4 artifact cards

### Changed
- `quality.py` pipeline now includes security audit step before ruff
- `build-architecture.py` includes new scripts in quality/maintenance/discovery categories
- Agent anatomy docs show new optional fields (model_tier, tdd_framework)

## [2.1.4] — 2026-07-29 — Bug Fixes & Documentation Accuracy

### Fixed
- **Bug**: `test_integration_pipeline.py` passed wrong argument type to `validate_depends_on()` — integration test was silently non-functional
- **Bug**: `analyze-deps.py` `find_cycles()` no exception handling on file read — runtime crash on unreadable agent files
- **Bug**: `score-agents.py` `--compare` displayed `X/10` but v7 scores are on 0-18 scale — misleading output
- **Bug**: `analyze-deps.py` reverse cross-category bonus overwrote hand-calibrated explicit values

### Documentation
- **README**: `project-management` agent count corrected from 22 to 24
- **README-zh**: All 56 category counts synchronized with AGENTS.json actual data; added 4 missing categories (gis, thinking-models, home-lifestyle, parenting-family); updated all 7 group header totals
- **ARCHITECTURE**: Integration targets updated from 6 to actual count; removed non-existent `convert_copilot` reference
- **CONTRIBUTING**: Fixed broken reference to non-existent `CONTRIBUTORS.md`

### Improved
- **Reliability**: `batch-nexus-roles.py` and `rebalance-nexus-phases.py` now use `atomic_write()` — prevents partial file corruption on crash
- **Robustness**: `nexus-orchestrator.py` gate mode now handles `EOFError` gracefully (piped stdin)
- **Robustness**: `ab-evaluate.py` now searches subdirectories for agent files (supports nested categories like game-development/)
- **Portability**: `check-agent-originality.sh`, `check-divisions.sh`, `analyze-deps.sh` now use python3→python fallback chain with version validation
- **Schema**: `agent-frontmatter.schema.json` added `lifecycle` field (managed by `agent-lifecycle.py`)
- **Config**: `release.yml` release-type aligned with `release-please-config.json` (`python` → `simple`)
- **Code**: `generate-index.py` uses `json.dumps()` for version/generated fields instead of raw string concatenation

## [2.1.3] — 2026-07-28 — Bug Fix & Code Quality

### Fixed
- **Bug**: `score_agent_v7()` missing `v7_word_count` field — all agent word counts showed 0 in scoring reports
- **Code**: `install-remote.py` removed unused `import sys`, fixed placeholder-less f-string
- **Reliability**: `install-remote.py` added `timeout=30` to both `urlopen()` calls (was no timeout)
- **Style**: `ab-test.py` PEP 8 import ordering (`from pathlib` moved to import block)

### Added
- **Tests**: `tests/test_install_remote.py` with 9 unit tests (slugify + install_agents with mocked network)
- **Config**: `pyproject.toml` coverage omit expanded to include `install.py` and `fix-filename-prefixes.py`

## [2.1.2] — 2026-07-26 — Data Consistency & Code Quality Hardening

### Fixed
- **Data**: `divisions.json` removed 4 zombie entries (hr-tech, network-engineering, securities, security) — 66→62 divisions, resolving check-divisions CI failure
- **CI**: `quality.sh` replaced stale `check-deps.sh` reference with `analyze-deps.py --validate`
- **CI**: `quality-gate.yml` corrected summary labels from v6 to v7 + removed redundant threshold step
- **Code**: `convert.py` unified `discover_agents()` to shared `_shared.discovery` implementation — `_solution` agents now included in conversions
- **Code**: `lint-agents.py` reused `git_last_modified()` from `_shared.validators` — eliminated duplicate subprocess logic
- **Docs**: Updated README example commands (`security` → `cybersecurity`); regenerated ARCHITECTURE.md

### Removed
- **Code**: Deleted v5/v6 scoring engines from `score-agents.py` (~570 lines of dead code) — only v7 remains active
- **Tests**: Deleted v5/v6 test classes from `test_score_agents.py` (~400 lines)

### Improved
- **Reliability**: Added `atomic_write()` utility (tmp+rename pattern) across `generate-index.py`, `agent-lifecycle.py`, `nexus-orchestrator.py`
- **Code**: Replaced 21 bare `except Exception` with specific exception types across 11 scripts
- **Tests**: Added missing `sys.path.insert` in `test_lint_agents.py`; updated convert/lifecycle/batch test mocks for refactored APIs
- **Docs**: Cleaned up stale `check-deps` references in `docs/SCRIPT-ARCHITECTURE.md` and `scripts/build-architecture.py`

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
