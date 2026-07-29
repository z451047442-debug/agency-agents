# Agency Hardening & Quality Enhancement — Design Spec

**Date**: 2026-07-30
**Status**: draft
**Priority**: Hardening (P1) → Quality (P2) → NEXUS Tools (P3) → Metadata Fields (P4)

---

## 1. NEXUS Hardening Rebalance (P1)

### Current State
- 127 agents with `phase-4-hardening`, vs 773 for `phase-3-build`
- Phase 4 playbook defines 8 core roles, but coverage is uneven
- `scripts/suggest-nexus-roles.py` already exists for keyword-based phase matching

### Approach

**Step 1 — Bulk Reclassify**
Run `suggest-nexus-roles.py` across all agents, identify candidates for `phase-4-hardening`, batch-add via existing `batch-nexus-roles.py` pattern. Expected yield: 50-80 agents.

**Step 2 — Gap Analysis**
Compare existing hardening agents against the 8 playbook roles:

| Role | Status | Action |
|------|--------|--------|
| Evidence Collector | Partial coverage | Find or create |
| API Tester | Likely exists (testing category) | Verify |
| Performance Benchmarker | Likely exists (testing category) | Verify |
| Legal Compliance Checker | Likely exists (legal/cybersecurity) | Verify |
| Test Results Analyzer | Covered (`testing-test-results-analyzer`) | Done |
| Workflow Optimizer | Partial coverage | Find or create |
| Infrastructure Maintainer | Covered (infrastructure category) | Verify |
| Reality Checker | **Missing** — needs dedicated agent | Create |

**Step 3 — Create Missing Agents**
Only create agents for roles with genuine gaps. Target: 3-5 new agents max.

**Target**: 127 → 180+ hardening agents, all 8 core roles covered.

---

## 2. Quality Governance (P2)

### Current State
- 104 agents flagged: 51 no cross-category deps, 33 thin content (1-3/7 sections), 10 no deps at all
- Score distribution: A=55, B=1242, C=100, D=2 — concentrated in B band, low variance (stddev 0.83)

### Approach

**Phase 1 — Auto-fix Dependencies**
Extend or create a script that:
1. Reads flagged agents with "no cross-category depends_on"
2. Queries `analyze-deps.py --json` for suggested cross-category deps
3. Applies suggestions automatically (with dry-run mode)
4. Validates all references resolve

**Phase 2 — Content Expansion**
New script `scripts/expand-thin-agents.py`:
1. Reads agents with 1-3/7 substantive sections
2. For each, generates missing sections based on agent category and existing content
3. Uses the Organic Content Expansion pattern (already in `scripts/expand-agent.py`)
4. Batch mode with per-agent verification

**Target**: Zero agents with no cross-category deps, thin agents reduced from 33 to < 10.

---

## 3. NEXUS Orchestration Tools (P3)

### New Scripts

**`scripts/match-nexus-agents.py`**
- Input: project description (natural language) or structured requirements
- Output: suggested agent roster per NEXUS phase
- Uses keyword matching + `nexus_roles` index
- Flags: `--phase <n>` to scope to single phase, `--json` for machine output

**`scripts/nexus-coverage.py`**
- Input: none (reads all agents)
- Output: per-phase heatmap showing agent count, category diversity, role coverage
- Flags: `--category <name>` to drill into single category, `--gaps` to show uncovered roles
- Visual terminal output (bar charts like `nexus-orchestrator.py --stats`)

---

## 4. New Metadata Fields (P4)

### New Fields

| Field | Type | Purpose |
|-------|------|---------|
| `tags` | `string[]` | Free-form tags for improved searchability (e.g., "cloud", "security", "frontend") |
| `keywords` | `string[]` | Structured search keywords, used by `search-agents.py` for ranking |
| `complexity` | `enum["low","medium","high"]` | NEXUS scheduling weight — routes complex tasks to premium models |
| `estimated_duration` | `string` (max 32 chars) | Expected task duration hint (e.g., "2-4h", "1-2d") for NEXUS timeboxing |

### Implementation
1. Add fields to `schemas/agent-frontmatter.schema.json`
2. Update `scripts/lint-agents.py` to recognize (not require) new fields
3. Update `scripts/score-agents.py` scoring dimensions (optional, v8)
4. Update `scripts/search-agents.py` to weight `tags` and `keywords`
5. Add batch-population script for initial seeding

---

## 5. Execution Order

```
P1: Hardening Rebalance
  ├── 1a. Run suggest-nexus-roles across all agents
  ├── 1b. Batch-add phase-4-hardening to high-confidence suggestions
  ├── 1c. Gap analysis against 8 playbook roles
  └── 1d. Create missing role agents (3-5 max)

P2: Quality Governance
  ├── 2a. Auto-fix cross-category depends_on for 51 agents
  └── 2b. Content expansion for 33 thin agents

P3: NEXUS Tools
  ├── 3a. match-nexus-agents.py
  └── 3b. nexus-coverage.py

P4: Metadata Fields
  ├── 4a. Schema + linter updates
  ├── 4b. Search script updates
  └── 4c. Batch population
```

---

## 6. Success Criteria

- [ ] Hardening agent count ≥ 180
- [ ] All 8 Phase 4 playbook roles have dedicated coverage
- [ ] Zero agents flagged for "no cross-category depends_on"
- [ ] Thin agents (1-3 sections) reduced from 33 to < 10
- [ ] `match-nexus-agents.py` produces valid agent rosters for given project descriptions
- [ ] `nexus-coverage.py` shows accurate per-phase coverage heatmap
- [ ] 4 new metadata fields added to schema, linter, and search
- [ ] All existing scripts continue to pass (no regressions)
- [ ] `python -m pytest tests/ --cov=scripts` passes
