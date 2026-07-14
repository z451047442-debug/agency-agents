# The Agency — System Architecture v1.0.0

**1,292 AI Agent Personality Definitions · 65 Categories · 26 Tooling Scripts · 1,013 Tests**

---

## Layer 0: CI/CD Pipeline (7 workflows)

| Workflow | Trigger | Actions |
|----------|---------|---------|
| ci.yml | push/PR to main | lint -> test -> validate -> score-gate |
| lint-agents.yml | on *.md change | YAML + structure validation |
| quality-gate.yml | push/PR | score >= 5 threshold |
| release.yml | tag push | version + changelog |
| nightly-full-audit.yml | cron daily | full pipeline |
| check-divisions.yml | push/PR | validate division structure |
| check-tools.yml | push/PR | verify integrations sync |

---

## Layer 1: Test Suite (17 modules, 380 tests)

| Module | Tests | Module | Tests |
|--------|-------|--------|-------|
| test_convert.py | 61 | test_expand_agent.py | 13 |
| test_lint_agents.py | 46 | test_shard_index.py | 14 |
| test_build_hermes_plugin.py | 31 | test_add_comm_section.py | 14 |
| test_batch_nexus_roles.py | 30 | test_analyze_deps_auto.py | 12 |
| test_search_agents.py | 27 | test_contribute.py | 10 |
| test_validate_index.py | 25 | test_score_agents.py | 8 |
| test_shared.py | 23 | test_batch_add_deps.py | 6 |
| test_quality_report.py | 23 | | |
| test_agent_lifecycle.py | 20 | | |
| test_analyze_deps.py | 17 | | |

---

## Layer 2: Shared Library (scripts/_shared/)

### Public API (16 symbols)

**Colors:** BOLD, CYAN, GREEN, MAGENTA, RED, RESET, YELLOW

**Parsing:** get_body(), get_field(), get_frontmatter_text(), get_list_field()

**Discovery:** EXCLUDE_DIRS, REPO, discover_agents()

**Utility:** supports_color(), load_module()

### Module Details

**discovery.py**
- `REPO: Path` — repo root directory
- `EXCLUDE_DIRS: frozenset` — non-agent directories to skip
- `discover_agents(category_filter=None)` -> iterator of `(category, rel_path, file_path)`

**frontmatter.py**
- `get_frontmatter_text(content)` -> str — YAML between --- delimiters
- `get_body(content)` -> str — content after YAML frontmatter (returns content when no delimiters)
- `get_field(field, fm_text)` -> str — single YAML field value
- `get_list_field(field, fm_text)` -> list[str] — YAML list items under a field

**terminal.py**
- `supports_color()` -> bool — TTY detection
- ANSI color constants: GREEN, YELLOW, RED, BOLD, CYAN, MAGENTA, RESET

**__init__.py**
- Re-exports all 15 symbols from submodules
- `load_module(name, path)` -> module — importlib.util wrapper replacing deprecated SourceFileLoader

### Consumers (14 scripts)

lint-agents · convert · score-agents · analyze-deps · quality-report ·
agent-lifecycle · contribute · expand-agent · add-comm-section ·
search-agents · validate-index · generate-index · i18n/check-i18n · i18n/localize-agents

---

## Layer 3: Tooling Scripts (26 modules)

### Quality Pipeline

| Script | Purpose |
|--------|---------|
| lint-agents.py | YAML validation, section checks, CRLF detection, security scanner |
| score-agents.py | A-D grading (0-10): content_depth(3) + structure(3) + frontmatter(2) + file_health(2) |
| analyze-deps.py | depends_on validation, broken link detection, dependency suggestion |
| quality-report.py | Unified dashboard, effort estimation, category health |
| validate-index.py | AGENTS.json JSON schema + filesystem cross-reference |
| analyze-deps-auto.py | NLP-based auto dependency mapping from agent content |

### Maintenance Tools

| Script | Purpose |
|--------|---------|
| agent-lifecycle.py | draft -> review -> published -> deprecated lifecycle tracking |
| contribute.py | Contribution dashboard (beginner/intermediate/advanced skill levels) |
| expand-agent.py | B-grade -> A-grade content expansion with template engine |
| add-comm-section.py | Communication Style section generator with domain-specific traits |
| batch-add-deps.py | Bulk depends_on frontmatter manipulation |
| batch-nexus-roles.py | Bulk nexus_roles assignment |

### Integration Tools

| Script | Purpose |
|--------|---------|
| convert.py | .md -> 8 target tool formats, parallel mode |
| build-hermes-plugin.py | Hermes IDE plugin packaging |

### Discovery Tools

| Script | Purpose |
|--------|---------|
| search-agents.py | Keyword/category/regex search, paginated results |
| generate-index.py | AGENTS.json index generator (cross-platform; --check for CI) |
| shard-index.py | AGENTS.json splitter, parallel processing |
| i18n/check-i18n.py | Translation coverage, template generation |
| i18n/localize-agents.py | Name+description patching from JSON translation maps |

---

## Layer 4: Agent Content (1292 .md files, 62 categories)

### Category Distribution (Top 20)

| # | Category | Agents | # | Category | Agents |
|---|----------|--------|---|----------|--------|
| 1 | engineering | 112 | 11 | education | 24 |
| 2 | infrastructure | 97 | 12 | project-management | 23 |
| 3 | marketing | 84 | 13 | automotive | 22 |
| 4 | healthcare | 50 | 14 | legal | 22 |
| 5 | data-science | 46 | 15 | specialized | 20 |
| 6 | manufacturing | 43 | 16 | testing | 20 |
| 7 | construction | 40 | 17 | iot | 19 |
| 8 | energy | 40 | 18 | logistics | 19 |
| 9 | cybersecurity | 36 | 19 | hr / sales | 15 |
| 10 | finance | 36 | 20 | food-beverage / robotics | 15 |

42 more categories: aerospace(32), environmental(33), game-dev(24),
media-entertainment(24), design(24), spatial-computing(15), gis(13), web3(13),
customer-service(12), network-eng(12), retail(12), telecom(12), tourism(12),
agriculture(12), insurance(11), operations(11), product(11), securities(11),
government(10), lottery(10), real-estate(10), quality(9), pharma-biotech(8),
administration(7), strategy(7), security(6), localization(4), mining(4), sports(4),
emergency(4), events(4), fashion(4), nonprofit(4), publishing(4), beauty(3),
forestry(3), hr-tech(3), pets(3), libraries(2), museums(2)

### Special Directories

- `_solution/` — meta-agents for multi-agent team coordination
- `libraries/` — cross-industry infrastructure (archivists, librarians)
- `specialized/` — cross-cutting roles (CFO, CSM, DPO, ESG officer, grant writer)
- `strategy/` — strategy consulting (CEO coach, VC advisory, ESG)
- `docs/` — NEXUS orchestration (playbooks, runbooks, coordination)

### Agent File Anatomy

```yaml
---
name: "Agent Display Name"     # required (1-120 chars)
description: "One-sentence..." # required (10-500 chars)
emoji: "🎯"                     # required (1-8 chars)
color: cyan                    # required (named or #RRGGBB)

version: "1.0.0"              # standard (auto-populated)
date_added: "2026-07-03"      # standard (auto-populated)

vibe: "personality primer"    # optional
nexus_roles:                  # optional (NEXUS pipeline phases)
  - phase-0-discovery
depends_on:                   # optional (agent IDs this agent needs)
  - engineering-backend-architect
lifecycle: published          # optional (draft/review/published/deprecated)
---

## Identity & Memory          <-- required
## Core Mission               <-- required
## Critical Rules             <-- required
[deliverables, workflow,      <-- recommended
 metrics, communication]
```

---

## Layer 5: Integration Targets (8 tools)

| Tool | Format | Converter |
|------|--------|-----------|
| Claude Code | .md | direct (no conversion) |
| Cursor | .mdc | convert_cursor() |
| Copilot | .md | convert_copilot() |
| Gemini CLI | .gm.md | convert_gemini_cli() |
| Windsurf | .windsurf | convert_windsurf() |
| Codex | .codex | convert_codex() |
| Kimi | .kimi.md | convert_kimi() |
| Antigravity | .ag.md | convert_antigravity() |

---

## Data Flow: Quality Pipeline

```
agent.md
  |
  v
lint-agents.py  ---> errors/warnings
  |
  v
score-agents.py ---> A-D grade (0-10)
  |
  v
analyze-deps.py ---> broken/valid deps
  |
  +---> quality-report.py    (unified dashboard)
  +---> contribute.py        (contribution opportunities)
  +---> agent-lifecycle.py   (state tracking)
  +---> expand-agent.py      (B->A upgrade path)
```

---

## NEXUS Multi-Agent Orchestration

```
Phase 0: Discovery  ->  Phase 1: Strategy  ->  Phase 2: Foundation
Phase 3: Build      ->  Phase 4: Hardening  ->  Phase 5: Launch
Phase 6: Operate

Agents opt-in via "nexus_roles" frontmatter field
Playbooks: docs/playbooks/  |  Runbooks: docs/runbooks/
Strategy doc: docs/nexus-strategy.md
```

---

## Dependency Graph (Import Relationships)

```
                     _shared/
              (discovery, frontmatter, terminal, load_module)
              /           |              \
             /            |               \
    lint-agents.py  score-agents.py   convert.py
         |               |                |
         v               v                v
quality-report.py  analyze-deps.py  agent-lifecycle.py
                   contribute.py   expand-agent.py
                                   add-comm-section.py
                                   search-agents.py
                                   validate-index.py
                                   generate-index.py
                                   i18n/check-i18n.py
                                   i18n/localize-agents.py

---> import via _shared       (all shared: colors, frontmatter, discovery)
---> import via load_module() (hyphenated: score-agents, lint-agents)
```

---

## Gaps & Next Steps

### P0: Critical
- [x] Install verification in CI (test install.sh end-to-end)
- [x] Git tag v1.0.0 + GitHub Release

### P1: High
- [x] Test coverage 100% (903 tests, 3292 lines, 0 missed)
- [x] mypy static type checking (runs in CI extended job)
- [x] Pre-commit hooks auto-install mechanism (scripts/setup-hooks.sh)

### P2: Medium
- [x] Agent duplication detection in CI (check-dupes.sh in extended job)
- [x] i18n coverage tracking in CI (check-i18n.py --strict in extended job)
- [x] Agent versioning strategy (docs/AGENT-VERSIONING.md)
- [x] PR template + CODEOWNERS

### P3: Nice-to-Have
- [ ] Agent download/usage metrics
- [x] Web-based agent browser/search UI (agent-browser.html)
- [ ] Automated agent generation from templates
- [ ] Cross-tool agent sync verification
- [x] NEXUS role assignment — 1292/1292 agents with nexus_roles (0 orphans)
- [x] Cross-platform CI matrix (Windows + Ubuntu, Python 3.10-3.12)
- [x] Shell→Python migration complete — all scripts have standalone .py files (including generate-index.py)
- [x] NEXUS orchestrator script (scripts/nexus-orchestrator.py)
- [x] Coverage gate unified to 90% across local and CI
- [x] Cross-platform index generator (scripts/generate-index.py)
- [x] Agent index schema fix (depends_on/nexus_roles in agent-index.schema.json)
- [x] Domain expansion: database (+10), military/defense (+9), education (+7), tools (+12)
