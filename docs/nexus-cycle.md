# 🔄 NEXUS Cycle — Closed-Loop Feedback from Operate to Discovery

> The NEXUS pipeline is drawn as a linear sequence (0→1→2→3→4→5→6), but real product development is cyclical. This document defines the feedback loops that connect Phase 6 (Operate) back to earlier phases — turning the pipeline into a continuous improvement engine.

---

## The Full Cycle

```
                    ┌──────────────────────────────────────┐
                    │                                      │
                    ▼                                      │
    ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
    │ Phase 0  │ Phase 1  │ Phase 2  │ Phase 3  │ Phase 4  │ Phase 5  │ Phase 6  │
    │ DISCOVER │ STRATEGY │FOUNDATION│  BUILD   │ HARDEN   │ LAUNCH   │ OPERATE  │
    └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴─────┬────┘
         ▲          ▲          ▲          ▲          ▲                       │
         │          │          │          │          │                       │
         └──────────┴──────────┴──────────┴──────────┴───────────────────────┘
                               Feedback Triggers (see below)
```

---

## Feedback Triggers — Operate → Earlier Phases

### Trigger: User Signal Degradation → Phase 0 (Re-Discovery)

| Attribute | Value |
|-----------|-------|
| **Condition** | Day-30 retention drops below target for 2 consecutive months |
| **Detected by** | Analytics Reporter |
| **Decision maker** | Studio Producer |
| **Re-entry mode** | NEXUS-Sprint (Discovery-focused) |
| **Agents activated** | UX Researcher, Feedback Synthesizer, Trend Researcher |

### Trigger: Recurring P0 Incidents → Phase 1 (Architecture Review)

| Attribute | Value |
|-----------|-------|
| **Condition** | ≥3 P0 incidents in a 30-day window, or same root cause twice |
| **Detected by** | Infrastructure Maintainer |
| **Decision maker** | Studio Producer + Backend Architect |
| **Re-entry mode** | NEXUS-Sprint (Architecture-focused) |
| **Agents activated** | Backend Architect, DevOps Automator, Infra Maintainer, Performance Benchmarker |

### Trigger: User Feedback Pattern → Phase 3 (Feature Build)

| Attribute | Value |
|-----------|-------|
| **Condition** | ≥20 user requests for the same feature OR a pain point dominates feedback for 2 consecutive bi-weekly reports |
| **Detected by** | Feedback Synthesizer |
| **Decision maker** | Sprint Prioritizer |
| **Re-entry mode** | NEXUS-Sprint |
| **Agents activated** | Sprint Prioritizer, Backend Architect, Frontend Developer, Evidence Collector |

### Trigger: Performance Degradation → Phase 4 (Targeted Hardening)

| Attribute | Value |
|-----------|-------|
| **Condition** | P95 latency increases >20% over 4 weeks, or Lighthouse score drops below 80 |
| **Detected by** | Performance Benchmarker |
| **Decision maker** | Backend Architect |
| **Re-entry mode** | NEXUS-Micro |
| **Agents activated** | Performance Benchmarker, Backend Architect, Frontend Developer |

### Trigger: Regulatory Change → Phase 1 (Compliance Re-Architecture)

| Attribute | Value |
|-----------|-------|
| **Condition** | New regulation announced that affects current architecture |
| **Detected by** | Legal Compliance Checker (monthly scan) |
| **Decision maker** | Studio Producer |
| **Re-entry mode** | NEXUS-Sprint or Full (depending on scope) |
| **Agents activated** | Legal Compliance Checker, Backend Architect, Reality Checker |

### Trigger: Growth Plateau → Phase 0 + Phase 5 (Go-to-Market Pivot)

| Attribute | Value |
|-----------|-------|
| **Condition** | MoM acquisition growth < 5% for 3 consecutive months |
| **Detected by** | Growth Hacker |
| **Decision maker** | Studio Producer |
| **Re-entry mode** | NEXUS-Sprint (Growth-focused) |
| **Agents activated** | Trend Researcher, Growth Hacker, Content Creator, Social Media Strategist, Experiment Tracker |

### Trigger: Quarterly Strategic Review → Phase 0 (Scheduled)

| Attribute | Value |
|-----------|-------|
| **Condition** | Calendar-based: every 90 days |
| **Detected by** | Agents Orchestrator (scheduled) |
| **Decision maker** | Studio Producer |
| **Re-entry mode** | NEXUS-Sprint |
| **Agents activated** | Trend Researcher, Analytics Reporter, Feedback Synthesizer, Finance Tracker, Executive Summary Generator |

---

## Re-Entry Decision Protocol

```
1. CONFIRM the signal is real (not a data anomaly)
   └── Analytics Reporter validates the data

2. ASSESS the blast radius
   ├── Which phases/agents are affected?
   ├── What's the rollback cost if we're wrong?
   └── What's the cost of NOT acting?

3. CHOOSE re-entry mode
   ├── NEXUS-Micro: targeted fix, 1-5 days, 5-10 agents
   ├── NEXUS-Sprint: feature/improvement cycle, 2-6 weeks, 15-25 agents
   └── NEXUS-Full: major pivot, 12-24 weeks, all agents

4. SCAFFOLD the re-entry
   ├── Agents Orchestrator activates the required agents
   ├── Context priming: deliver relevant Phase 6 data to entering agents
   └── Set re-entry scope boundaries (what NOT to touch)

5. EXECUTE with quality gates
   └── Standard NEXUS gates still apply within the re-entry scope
```

---

## Cycle Governance

| Role | Responsibility |
|------|---------------|
| **Agents Orchestrator** | Monitor trigger conditions, alert decision makers, manage re-entry activation |
| **Studio Producer** | Approve/disapprove re-entry for P0 triggers and strategic reviews |
| **Analytics Reporter** | Validate trigger data before escalation |
| **Sprint Prioritizer** | Adjust backlog when a re-entry cycle begins — pause lower-priority work |

---

## Anti-Patterns

| Anti-Pattern | Why It's Harmful | Mitigation |
|-------------|-----------------|------------|
| Re-entering Phase 0 for every minor signal | Thrashing — constant re-discovery prevents execution | Minimum signal threshold before trigger fires |
| Skipping quality gates on re-entry | "It's just a small fix" leads to regression | Gates are non-negotiable regardless of re-entry size |
| Re-entering without context from Phase 6 | New agents start cold, repeat old mistakes | Context priming protocol is mandatory on re-entry |
| Running multiple overlapping re-entry cycles | Resource contention, conflicting priorities | Only one re-entry cycle active at a time |
