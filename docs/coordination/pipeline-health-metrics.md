# 📊 NEXUS Pipeline Health Metrics

> How do we know if the NEXUS pipeline itself is improving? These metrics measure the pipeline's effectiveness — distinct from product metrics (what we build) and business metrics (what we earn). The Agents Orchestrator collects these at each sprint boundary and produces a quarterly trend report.

---

## Core Pipeline Metrics

### Phase Transit Time
**What**: Median calendar days spent in each phase.  
**Why**: Identifies bottlenecks — if Phase 3 is 3x Phase 1, task scoping or QA bandwidth may be the issue.  
**Target**: Phase 0 ≤ 7d, Phase 1 ≤ 5d, Phase 2 ≤ 5d, Phase 3 ≤ 14d/sprint, Phase 4 ≤ 7d, Phase 5 ≤ 7d.

| Phase | Sprint N-3 | Sprint N-2 | Sprint N-1 | Sprint N | Trend |
|-------|-----------|-----------|-----------|----------|-------|
| 0 — Discovery | — | — | 6d | 5d | ↓ improving |
| 1 — Strategy | — | — | 4d | 3d | ↓ improving |
| 2 — Foundation | — | — | 5d | 5d | → stable |
| 3 — Build | — | — | 16d | 14d | ↓ improving |
| 4 — Hardening | — | — | 8d | 6d | ↓ improving |
| 5 — Launch | — | — | 5d | 4d | ↓ improving |

### Gate First-Pass Rate
**What**: Percentage of phase gate evaluations that pass on the first attempt.  
**Why**: Measures quality left-shift effectiveness. Low rates → issues found too late.  
**Target**: 80%+ across all gates.

| Gate | Sprint N-3 | Sprint N-2 | Sprint N-1 | Sprint N | Trend |
|------|-----------|-----------|-----------|----------|-------|
| 0→1 Discovery | — | — | 100% | 100% | → stable |
| 1→2 Architecture | — | — | 75% | 100% | ↑ improving |
| 2→3 Foundation | — | — | 100% | 100% | → stable |
| 3→4 Feature | — | — | 80% | 85% | ↑ improving |
| 4→5 Production | — | — | 50% | 67% | ↑ improving |
| 5→6 Launch | — | — | 100% | 100% | → stable |

### Task First-Pass QA Rate
**What**: Percentage of individual tasks that pass QA on the first Dev↔QA attempt.  
**Why**: Measures task clarity and developer-context alignment.  
**Target**: 70%+.

| Metric | Sprint N-3 | Sprint N-2 | Sprint N-1 | Sprint N | Trend |
|--------|-----------|-----------|-----------|----------|-------|
| First-pass QA rate | — | — | 65% | 72% | ↑ improving |
| Average retries per task | — | — | 1.6 | 1.3 | ↓ improving |
| Tasks completed / total | — | — | 18/22 | 20/21 | ↑ improving |

### Escalation Rate
**What**: Percentage of tasks that exceed 3 retries and require escalation.  
**Why**: High escalation rates indicate systemic issues — poor task scoping, unclear acceptance criteria, or architectural problems.  
**Target**: < 5% of total tasks.

| Metric | Sprint N-3 | Sprint N-2 | Sprint N-1 | Sprint N | Trend |
|--------|-----------|-----------|-----------|----------|-------|
| Escalated tasks | — | — | 2 (9%) | 1 (5%) | ↓ improving |
| Reassigned | — | — | 1 | 0 | ↓ improving |
| Decomposed | — | — | 1 | 1 | → stable |
| Deferred | — | — | 0 | 0 | → stable |

### Agent Utilization
**What**: Percentage of activated agents that completed ≥1 task in the sprint.  
**Why**: Identifies over-allocation (agents sitting idle) and under-allocation (bottleneck agents).  
**Target**: 80-95% utilization (not 100% — slack is healthy).

| Division | Agents Activated | Agents with Tasks | Utilization | Bottleneck? |
|----------|-----------------|-------------------|-------------|-------------|
| Engineering | 4 | 4 | 100% | Yes — over-allocated |
| Design | 2 | 2 | 100% | No |
| Marketing | 3 | 1 | 33% | Under-utilized |
| Testing | 3 | 3 | 100% | Monitor |
| Project Management | 2 | 2 | 100% | No |

---

## Quarterly Trend Analysis

Every quarter, the Agents Orchestrator produces a trend report answering:

1. **Are we getting faster?** — Compare Phase Transit Times quarter-over-quarter
2. **Are we getting better?** — Gate First-Pass Rate and Task First-Pass QA Rate trends
3. **Are we getting more predictable?** — Variance in Phase Transit Times
4. **Where are the recurring bottlenecks?** — Highest transit time + lowest first-pass rate combination
5. **Are escalations clustered?** — Same agent, same task type, same phase entry pattern?

---

## Red Flags (Immediate Action)

| Condition | Action |
|-----------|--------|
| Any gate first-pass rate < 40% | Studio Producer reviews gate criteria |
| Escalation rate > 15% for 2 consecutive sprints | Backend Architect reviews task scoping |
| Phase 3 transit time > 2x sprint estimate for 2 sprints | Sprint Prioritizer recalibrates velocity |
| Agent utilization < 30% for a division | Review whether that division should be active |
| Task first-pass QA rate drops >20% from previous sprint | Investigate: new developer? scope creep? unclear architecture? |

---

## Data Collection

| Metric | Collection Method | Frequency |
|--------|------------------|-----------|
| Phase Transit Time | Orchestrator timestamps phase entry/exit | Per phase |
| Gate First-Pass Rate | Gate Keeper records attempt count | Per gate |
| Task First-Pass QA Rate | Evidence Collector records per task | Per task |
| Escalation Rate | Orchestrator tracks failed tasks | Per sprint |
| Agent Utilization | Orchestrator tracks activation vs. task completion | Per sprint |

The Orchestrator appends each sprint's metrics to a `pipeline-health.json` log for trend analysis.

---

## Integration with NEXUS Cycle

Pipeline health metrics feed into [NEXUS Cycle](../nexus-cycle.md) triggers:
- Escalation rate > 15% for 2 sprints → triggers Phase 1 re-entry (Architecture Review)
- Phase transit time increasing for 3 consecutive sprints → triggers workflow review
- Gate first-pass rate declining → triggers quality process review
