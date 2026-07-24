# Multi-Agent Project Review — Design Spec

**Date:** 2026-07-17
**Status:** approved
**Type:** meta-review (using agent system to review agent system)

## Goal

Deep diagnostic review of the agency-agents project by 6 independent domain experts, consolidated by a Project Director and actioned by a Project Manager — producing an executable improvement backlog.

## Scope

6 review dimensions across the entire repo:

| # | Dimension | Expert Agent | Key Artifacts Reviewed |
|---|-----------|-------------|----------------------|
| 1 | Content Quality | 内容策略师 | 1363 agent `.md` files, frontmatter, domain signals |
| 2 | Toolchain Architecture | Python 架构师 | 31 Python scripts (~10K lines), CLI consistency |
| 3 | NEXUS Orchestration | 多智能体编排师 | `docs/nexus-strategy.md`, nexus_roles coverage, handoff protocols |
| 4 | CI/CD Quality Gates | DevOps 工程师 | 7 GitHub Actions workflows, score gates, regression checks |
| 5 | Dependencies & Discoverability | 数据工程师 | `depends_on` network, `AGENTS.json`, search accuracy |
| 6 | Developer Experience | DX 工程师 | `create-agent.sh`, lint output UX, install flow, docs |

## Collaboration Model

- **Phase 1 — Parallel Review:** 6 experts receive the same project brief, audit independently, produce structured reports using a unified template
- **Phase 2 — Director Consolidation:** Project Director reads all 6 reports, identifies cross-cutting risks, produces priority matrix
- **Phase 3 — PM Execution Plan:** Project Manager converts findings into actionable tasks with owners, schedule, and acceptance criteria

## Output Template (per expert)

```markdown
## [Dimension] Review Report

### Key Findings (3-5, severity-ordered)
- Critical / Warning / Highlight

### Quantitative Score (1-10 per sub-dimension)

### Improvement Recommendations (≤3 executable items)
1. [file/location] → [action] — expected impact

### Cross-Dependencies
- Issues requiring coordination with other dimensions
```

## Success Criteria

- Each report: ≥2 actionable findings
- Director: ≥2 cross-dimension risks identified
- PM: task cards ready for Sprint ingestion
