# Changelog

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
