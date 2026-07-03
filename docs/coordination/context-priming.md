# 🧠 NEXUS Context Priming Protocol

> When an agent is activated in a NEXUS phase, it must consume a **Minimum Context Package** before starting work. This prevents agents from operating with incomplete project understanding — the #2 cause of rework after poor handoffs.

---

## Principle

**No agent starts cold.** Before an agent executes its first task, it must read and internalize the phase-appropriate context package. The Orchestrator is responsible for ensuring the context package is assembled and delivered at activation time.

---

## Minimum Context Package by Phase

### Phase 0 — Discovery
*Agents: Trend Researcher, Feedback Synthesizer, UX Researcher, Analytics Reporter, Legal Compliance Checker, Tool Evaluator*

| Context Item | Source | Required For |
|-------------|--------|-------------|
| Project brief / initial concept | Stakeholder | All agents |
| Target market definition | Stakeholder | Trend Researcher, UX Researcher |
| Existing product/competitor list (if any) | Stakeholder | Trend Researcher, Tool Evaluator |
| Regulatory jurisdiction list | Stakeholder | Legal Compliance Checker |
| Available data sources | Stakeholder | Analytics Reporter |

### Phase 1 — Strategy & Architecture
*Agents: Studio Producer, Senior Project Manager, Sprint Prioritizer, UX Architect, Brand Guardian, Backend Architect, AI Engineer, Finance Tracker*

| Context Item | Source | Required For |
|-------------|--------|-------------|
| **Phase 0 Executive Summary** (GO decision) | Executive Summary Generator | All agents |
| Market Analysis Report | Trend Researcher | Studio Producer, Sprint Prioritizer |
| User Personas + Journey Maps | UX Researcher | UX Architect, Sprint Prioritizer |
| Synthesized Feedback Report | Feedback Synthesizer | Sprint Prioritizer, Senior PM |
| Compliance Requirements Matrix | Legal Compliance Checker | Backend Architect, UX Architect |
| Tech Stack Assessment | Tool Evaluator | Backend Architect, AI Engineer |
| Data Audit Report | Analytics Reporter | Backend Architect, AI Engineer |
| Budget/Resource constraints | Stakeholder | Finance Tracker, Studio Producer |

### Phase 2 — Foundation
*Agents: DevOps Automator, Frontend Developer, Backend Architect, UX Architect, Infrastructure Maintainer, Studio Operations*

| Context Item | Source | Required For |
|-------------|--------|-------------|
| **Architecture Package** (Phase 1 Gate output) | Studio Producer | All agents |
| System Architecture Specification | Backend Architect | All dev agents |
| CSS Design System + Layout Framework | UX Architect | Frontend Developer |
| Brand Foundation Document | Brand Guardian | Frontend Developer, UX Architect |
| Prioritized Sprint Backlog | Sprint Prioritizer | All dev agents |
| Financial Plan | Finance Tracker | DevOps Automator, Infra Maintainer |
| ≥2 ADRs from Phase 1 | Backend Architect / UX Architect | All dev agents |
| Git workflow + branch strategy | Studio Operations | All dev agents |

### Phase 3 — Build
*Agents: Any developer agent entering mid-phase*

| Context Item | Source | Required For |
|-------------|--------|-------------|
| **Foundation Gate result** (Phase 2 Gate output) | DevOps Automator + Evidence Collector | All agents |
| Current sprint backlog (this sprint's tasks) | Sprint Prioritizer | All agents |
| Architecture spec + ADRs | Backend Architect / UX Architect | All agents |
| Design system tokens + component library | Frontend Developer | All frontend/UI agents |
| API spec (OpenAPI doc) | Backend Architect | All backend/integration agents |
| CI/CD pipeline docs | DevOps Automator | All dev agents |
| Previous task QA results (for context on patterns) | Agents Orchestrator | All dev agents |

### Phase 4 — Hardening
*Agents: Reality Checker, Evidence Collector, Performance Benchmarker, API Tester, Test Results Analyzer, Legal Compliance Checker, Infrastructure Maintainer, Workflow Optimizer*

| Context Item | Source | Required For |
|-------------|--------|-------------|
| **Phase 3 Gate result** (all tasks QA'd, metrics) | Agents Orchestrator | All agents |
| Complete task list with QA history | Agents Orchestrator | Reality Checker, Test Results Analyzer |
| Specification (original, not implementation) | Senior Project Manager | Reality Checker |
| Architecture spec | Backend Architect | Performance Benchmarker, Infra Maintainer |
| Compliance matrix | Legal Compliance Checker | Legal Compliance Checker (update) |
| All previous QA packages | Evidence Collector | Reality Checker |
| Brand guidelines | Brand Guardian | Evidence Collector |

### Phase 5 — Launch
*Agents: Growth Hacker, Content Creator, Social Media Strategist, Twitter Engager, TikTok Strategist, Instagram Curator, Reddit Community Builder, App Store Optimizer, Executive Summary Generator, Project Shepherd, DevOps Automator, Infrastructure Maintainer*

| Context Item | Source | Required For |
|-------------|--------|-------------|
| **Phase 4 Gate result** (READY verdict) | Reality Checker | All agents |
| Product summary (what was built, key features) | Studio Producer | All marketing agents |
| Brand Foundation Document | Brand Guardian | All marketing/content agents |
| Target audience personas | UX Researcher | All marketing agents |
| Deployment architecture | DevOps Automator | Infra Maintainer |
| Rollback runbook | DevOps Automator | DevOps Automator, Infra Maintainer |
| Launch timeline (T-7 through T+7) | Project Shepherd | All agents |

### Phase 6 — Operate
*Agents: Any agent entering the ongoing operations phase*

| Context Item | Source | Required For |
|-------------|--------|-------------|
| **Phase 5 Gate result** (Launch metrics) | Studio Producer + Analytics Reporter | All agents |
| System architecture + runbooks | DevOps Automator + Infra Maintainer | Infra Maintainer, Support Responder |
| Monitoring dashboards | Infra Maintainer | All ops agents |
| Incident response protocol | Infra Maintainer | Support Responder |
| Current sprint backlog | Sprint Prioritizer | Sprint Prioritizer, Dev agents |
| Last month's Executive Summary | Executive Summary Generator | Executive Summary Generator |

---

## Activation Prompt Template

When the Orchestrator activates an agent, include a context section:

```
You are [AGENT NAME] activated in NEXUS Phase [N] — [Phase Name].
Project: [PROJECT NAME]

## Required Context (read before starting)
1. [Context item 1] — [path or summary]
2. [Context item 2] — [path or summary]
3. [Context item 3] — [path or summary]

## Your Role in This Phase
[Specific responsibilities and expected outputs]

## Current State
[What's been completed, what's pending, what's blocked]

## First Task
[Task ID and description]
```

---

## Orchestrator Responsibility

The Agents Orchestrator is responsible for:
1. Assembling the Minimum Context Package before agent activation
2. Verifying that context documents exist (flag missing ones to Studio Producer)
3. Delivering context in the activation prompt
4. Tracking which agents have consumed which context (for audit)


---
## Handling Missing Context Items

When a required context item is unavailable at phase start, follow this protocol:

| Situation | Action | Decision Maker |
|-----------|--------|---------------|
| Item not yet produced by prior phase | Wait up to 1 business day; escalate if still missing | Orchestrator |
| Item produced but quality gate not passed | Proceed with draft flagged as "UNVERIFIED"; re-validate at next gate | Gate Keeper |
| Item skipped deliberately (NEXUS-Sprint/Micro) | Document the gap in the phase kickoff note; accept reduced quality gate scope | Studio Producer |
| Item from external source (3rd party audit, vendor) | Proceed with placeholder assumptions; flag in risk register | Orchestrator |

**Rule**: Never block a phase indefinitely for a single missing item. Escalate to Studio Producer for a GO/NO-GO decision within 24 hours.
