# The Agency — System Architecture v2.1.3

**1,399 AI Agent Personality Definitions · 62 Categories · 35 Tooling Scripts · 1,241 Tests · OMC Smart Plugin**

Generated: 2026-07-28 23:29 UTC

---

## Layer 0: CI/CD Pipeline (7 workflows)

| Workflow | Trigger | Actions |
|----------|---------|---------|
| Check Divisions | push/PR | validate division structure |
| Check Tools | push/PR | verify integrations sync |
| CI | push/PR to main | lint -> test -> validate -> score-gate |
| Lint Agent Files | on *.md change | YAML + structure validation |
| Nightly Full Audit | cron daily | full pipeline audit |
| Quality Gate | push/PR | score >= 5 threshold |
| Release | tag push | version + changelog |

---

## Layer 1: Test Suite (35 modules, 1,241 tests)

| Module (tests) | Module (tests) |
|----------------|----------------|
| test_score_agents.py (96) | test_clean.py (25) |
| test_agent_lifecycle.py (80) | test_rebalance_nexus_phases.py (25) |
| test_convert.py (78) | test_shard_index.py (25) |
| test_nexus_orchestrator.py (78) | test_build_architecture.py (23) |
| test_lint_agents.py (75) | test_suggest_nexus_roles.py (21) |
| test_analyze_deps.py (73) | test_batch_version.py (20) |
| test_omc_scripts.py (69) | test_check_divisions.py (18) |
| test_quality_report.py (53) | test_batch_add_deps.py (16) |
| test_search_agents.py (47) | test_batch_date_added.py (16) |
| test_batch_nexus_roles.py (42) | test_analyze_deps_auto.py (15) |
| test_build_hermes_plugin.py (40) | test_check_dupes.py (15) |
| test_expand_agent.py (40) | test_generate_index.py (11) |
| test_contribute.py (38) | test_quality_pipeline.py (10) |
| test_feedback.py (37) | test_install_remote.py (9) |
| test_validate_index.py (37) | test_batch_nexus_roles_gap.py (7) |
| test_shared.py (35) | test_integration_pipeline.py (6) |
| test_add_comm_section.py (29) | test_build_agent_browser.py (3) |
| test_check_agent_originality.py (29) |  |

---

## Layer 2: Shared Library (scripts/_shared/)

**16 public API symbols** across 4 modules

**discovery.py** — Agent file discovery engine
- Exports: `REPO, EXCLUDE_DIRS, discover_agents()`

**frontmatter.py** — YAML frontmatter parsing utilities
- Exports: `get_body(), get_field(), get_frontmatter_text(), get_list_field()`

**terminal.py** — ANSI terminal color constants + TTY detection
- Exports: `BOLD, CYAN, GREEN, RED, RESET, YELLOW, supports_color()`

**__init__.py** — Module entry point and dynamic loader
- Exports: `Re-exports all 15 symbols + load_module()`

**33 consumers**: add-comm-section · agent-lifecycle · analyze-deps-auto · analyze-deps · audit-security · batch-nexus-roles · build-agent-browser · build-architecture · build-hermes-plugin · check-agent-originality · contribute · convert · expand-agent · export-omc-agents · extract-patterns · fix-filename-prefixes · fix-lint · generate-index · generate-nexus-skills · generate-omc-hooks · generate-omc-model-routing · generate-omc-team-config · check-i18n · localize-agents · install · lint-agents · nexus-orchestrator · quality-report · rebalance-nexus-phases · score-agents · search-agents · suggest-nexus-roles · validate-index

---

## Layer 3: Tooling Scripts (35 Python modules + 19 shell wrappers)

### Quality Pipeline (11 scripts)
| Script | Purpose |
|--------|---------|
| analyze-deps-auto.py | NLP-based auto dependency mapping from agent content |
| analyze-deps.py | depends_on validation + cross-category coverage + --apply |
| audit-security.py | Security audit: shell/Python/config pattern scanning |
| check-agent-originality.py | Agent originality and similarity detection |
| check-divisions.py | Division directory structure validation |
| check-dupes.py | Duplicate detection via semantic similarity |
| lint-agents.py | YAML validation, section checks, CRLF detection, security scanning |
| quality-report.py | Unified dashboard + risk tiers + feedback integration |
| quality.py | Quality pipeline orchestration entry point |
| score-agents.py | A-D grading with risk tiers, domain signals, and score variance |
| validate-index.py | AGENTS.json JSON schema + filesystem cross-reference validation |

### Maintenance Tools (12 scripts)
| Script | Purpose |
|--------|---------|
| add-comm-section.py | Communication Style section generator with domain traits |
| agent-lifecycle.py | draft -> review -> published -> deprecated lifecycle |
| batch-add-deps.py | Bulk depends_on frontmatter field manipulation |
| batch-date-added.py | Bulk date_added field population |
| batch-nexus-roles.py | Bulk nexus_roles field assignment |
| batch-version.py | Bulk version field population |
| clean.py | Project cleanup: __pycache__, build artifacts |
| contribute.py | Contribution dashboard with skill-level filtering |
| expand-agent.py | B-grade to A-grade content expansion with template engine |
| fix-lint.py | Incremental lint fixer: ruff + mypy auto-fix pipeline |
| rebalance-nexus-phases.py | Rebalance agent distribution across NEXUS phases |
| suggest-nexus-roles.py | Auto-suggest NEXUS roles based on agent content |

### Integration Tools (4 scripts)
| Script | Purpose |
|--------|---------|
| build-hermes-plugin.py | Hermes IDE plugin packaging and bundling |
| convert.py | .md to 9 target tool formats, with parallel mode |
| generate-index.py | AGENTS.json index generator with --check CI mode |
| shard-index.py | AGENTS.json splitter for parallel processing |

### Discovery & Orchestration (8 scripts)
| Script | Purpose |
|--------|---------|
| build-agent-browser.py | Self-contained agent browser HTML generator |
| build-architecture.py | ARCHITECTURE.md / .html auto-generator from live project data |
| extract-patterns.py | Feedback pattern analysis: surface improvement insights |
| feedback.py | User feedback collection — ratings, comments, issue reports |
| nexus-orchestrator.py | NEXUS multi-agent orchestration engine |
| search-agents.py | Keyword, category, and regex search with paginated results |
| i18n/check-i18n.py | Translation coverage tracking and template generation |
| i18n/localize-agents.py | Name + description patching from JSON translation maps |

Plus 19 shell wrappers (thin entry points delegating to .py counterparts).

---

## Layer 4: Agent Content (1,399 .md files, 62 categories)

### Category Distribution (all 62)

| 中文 | English | Agents |
|----|---------|--------|
| 工程开发 | engineering | 114 |
| 基础设施 | infrastructure | 111 |
| 市场营销 | marketing | 85 |
| 医疗健康 | healthcare | 54 |
| 金融 | finance | 53 |
| 数据科学 | data-science | 47 |
| 制造业 | manufacturing | 47 |
| 能源 | energy | 44 |
| 建筑工程 | construction | 43 |
| 网络安全 | cybersecurity | 39 |
| 环境 | environmental | 38 |
| 教育 | education | 36 |
| 航空航天 | aerospace | 33 |
| 媒体娱乐 | media-entertainment | 31 |
| 游戏开发 | game-development | 26 |
| 专业角色 | specialized | 26 |
| 设计 | design | 25 |
| 法律 | legal | 25 |
| 项目管理 | project-management | 24 |
| 汽车 | automotive | 23 |
| 人力资源 | hr | 22 |
| 物流 | logistics | 22 |
| 测试 | testing | 21 |
| 物联网 | iot | 20 |
| 食品饮料 | food-beverage | 16 |
| 地理信息 | gis | 16 |
| 机器人 | robotics | 16 |
| 销售 | sales | 16 |
| 空间计算 | spatial-computing | 16 |
| 旅游 | tourism | 16 |
| 零售 | retail | 15 |
| 农业 | agriculture | 14 |
| 政府 | government | 14 |
| 产品 | product | 14 |
| Web3 | web3 | 14 |
| 客户服务 | customer-service | 13 |
| 彩票 | lottery | 13 |
| 电信 | telecom | 13 |
| 思维模型 | thinking-models | 13 |
| 保险 | insurance | 12 |
| 运营 | operations | 12 |
| 房地产 | real-estate | 12 |
| 质量管理 | quality | 11 |
| 行政管理 | administration | 10 |
| 医药生物 | pharma-biotech | 9 |
| 出版 | publishing | 9 |
| 体育 | sports | 9 |
| 应急管理 | emergency | 7 |
| 活动会展 | events | 7 |
| 时尚 | fashion | 7 |
| 本地化 | localization | 7 |
| 矿业 | mining | 7 |
| 战略咨询 | strategy | 7 |
| 美妆 | beauty | 6 |
| 林业 | forestry | 6 |
| 公益 | nonprofit | 6 |
| 宠物 | pets | 6 |
| 家居生活 | home-lifestyle | 5 |
| 博物馆 | museums | 5 |
| 亲子家庭 | parenting-family | 5 |
| 解决方案 | _solution | 3 |
| 图书馆 | libraries | 3 |

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
emoji: "🎯"             # required (1-8 chars)
color: cyan                    # required (named or #RRGGBB)

version: "1.0.0"              # standard (auto-populated)
date_added: "2026-07-03"      # standard (auto-populated)

vibe: "personality primer"     # optional
model_tier: standard          # optional (premium/standard/economy)
tdd_framework: "pytest --cov" # optional (test framework for TDD)
nexus_roles:                  # optional (NEXUS pipeline phases)
  - phase-0-discovery
depends_on:                   # optional (agent IDs this agent needs)
  - engineering-backend-architect
---

## Identity & Memory          <-- required
## Core Mission               <-- required
## Critical Rules             <-- required
[deliverables, workflow,      <-- recommended
 metrics, communication]
```

---

## Layer 5: Integration Targets (10 tools)

| Tool | Format | Converter |
|------|--------|-----------|
| Claude Code | .md | direct (no conversion) |
| Cursor | .mdc | convert_cursor() |
| Gemini CLI | .md | convert_gemini_cli() |
| Codex | .toml | convert_codex() |
| Kimi | .md | convert_kimi() |
| Antigravity | .md | convert_antigravity() |
| OpenCode | .md | convert_opencode() |
| OpenClaw | .md | convert_openclaw() |
| Qwen | .md | convert_qwen() |
| Osaurus | .md | convert_osaurus() |

---

## Layer 5B: OMC 智能插件层 (4 个生成器, plugin 模式)

OMC (oh-my-claudecode) 是唯一不通过 convert.py 转换的集成目标 — 它由 4 个专用生成器产生 4 种不同的配置产物，反向增强 Claude Code 自身的智能能力：

| 产物 | 生成器 | 输出 | 规模 | 功能 |
|----|-----|----|----|----|
| NEXUS Skills | generate-nexus-skills.py | SKILL.md | 7 files | 按阶段关键词触发的 skill 文件，内含该阶段 agent 列表和质量门检查清单 |
| 模型路由 | generate-omc-model-routing.py | model-routing.json | 1399 条目 | 按 agent 质量评分分配模型层级 — A级→Opus / B级→Sonnet / C/D级→Haiku |
| 关键词 Hook | generate-omc-hooks.py | hooks.json | 领域→agent | 从 agent 名称和描述中提取领域关键词，用户提及时自动推荐对应 agent |
| 团队管线 | generate-omc-team-config.py | team-config.json | 5 阶段管线 | NEXUS 7阶段 → OMC 5阶段团队管线映射 (plan→prd→exec→verify→fix) |

> 与 Layer 5 的 10 个工具不同，OMC 不生成 agent 文件副本，而是将 agent 元数据转化为运行时智能 — 模型路由、关键词触发、阶段编排、团队协作。

---

## Layer 6: Data Flow & Module Dependency

### Shared Foundation

All 35 Python scripts read agent data through `_shared/` — none call each other's output:

```
                      _shared/
          (discovery, frontmatter, terminal)
         /     /    |     |    \        \\
        /     /     |     |     \        \\
   lint    score  analyze convert  search  validate
 agents  agents  -deps   .py     agents  -index
   .py     .py    .py             .py     .py
    |       |      |               |
    v       v      v               v
  errors  grades  broken       paginated
                  refs          results
```

### Quality Pipeline (orchestrated by quality.py)

```
quality.py
  ├── lint-agents.py       → 0 errors, 2 warnings
  ├── score-agents.py      → 100% A grade
  ├── analyze-deps.py      → 0 broken references
  ├── ruff check           → clean
  └── pytest --cov         → 93%+ coverage
```

### Key Consumers (grouped by role)

| Role | Script |
|------|--------|
| **Quality Gate** | `lint-agents.py`, `score-agents.py`, `analyze-deps.py`, `quality-report.py`, `validate-index.py` |
| **Maintenance** | `agent-lifecycle.py`, `contribute.py`, `expand-agent.py`, `add-comm-section.py` |
| **Integration** | `convert.py`, `generate-index.py`, `build-agent-browser.py`, `build-architecture.py` |
| **Discovery** | `search-agents.py`, `i18n/check-i18n.py`, `i18n/localize-agents.py` |

All 16 consumers depend on `_shared/` modules; cross-script imports use `load_module()` for hyphenated filenames.

---

## Layer 7: NEXUS Multi-Agent Orchestration

Phase 0: Discovery -> Phase 1: Strategy -> Phase 2: Foundation -> Phase 3: Build -> Phase 4: Hardening -> Phase 5: Launch -> Phase 6: Operate

**7 phases** with 1,399 agents distributed across them (agents opt in via `nexus_roles` frontmatter field).

Resources: `docs/nexus-strategy.md` | `docs/nexus-cycle.md` | `docs/playbooks/` | `docs/runbooks/` | `docs/teams/` | `docs/coordination/`

---

## Project Health

| Metric | Value |
|--------|-------|
| Version | v2.1.3 |
| Python | >=3.10 |
| Coverage threshold | 90% |
| Agent files | 1,399 |
| Tool scripts | 35 (.py) + 19 (.sh) |
| Tests | 1,241 across 35 modules |
| CI workflows | 7 |
| Integration targets | 10 |
| OMC plugin artifacts | 4 |
| NEXUS phases | 7 |

Generated: 2026-07-28 23:29 UTC
