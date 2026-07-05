# 📑 NEXUS Document Index

> Complete navigational map of all NEXUS documentation. Use this to find the right document for any pipeline task.

---

## Strategy & Pipeline

| Document | Purpose | Scope |
|----------|---------|-------|
| [nexus-strategy.md](../nexus-strategy.md) | Complete NEXUS orchestration strategy | All phases, all divisions |
| [nexus-cycle.md](../nexus-cycle.md) | Closed-loop Operate→Discovery feedback triggers | Phase 6 → earlier phases |

## Per-Phase Playbooks

| Phase | Document | Gate Keeper | Duration |
|-------|----------|-------------|----------|
| 0 — Discovery | [phase-0-discovery.md](../playbooks/phase-0-discovery.md) | Executive Summary Generator | 3-7 days |
| 1 — Strategy | [phase-1-strategy.md](../playbooks/phase-1-strategy.md) | Studio Producer + Reality Checker | 5-10 days |
| 2 — Foundation | [phase-2-foundation.md](../playbooks/phase-2-foundation.md) | DevOps Automator + Evidence Collector | 3-5 days |
| 3 — Build | [phase-3-build.md](../playbooks/phase-3-build.md) | Agents Orchestrator | 2-12 weeks |
| 4 — Hardening | [phase-4-hardening.md](../playbooks/phase-4-hardening.md) | Reality Checker (sole authority) | 3-7 days |
| 5 — Launch | [phase-5-launch.md](../playbooks/phase-5-launch.md) | Studio Producer + Analytics Reporter | 2-4 weeks |
| 6 — Operate | [phase-6-operate.md](../playbooks/phase-6-operate.md) | Studio Producer | Ongoing |

## Scenario Runbooks

| Scenario | Document | Mode | Duration |
|----------|----------|------|----------|
| Startup MVP | [scenario-startup-mvp.md](../runbooks/scenario-startup-mvp.md) | NEXUS-Sprint | 4-6 weeks |
| Enterprise Feature | [scenario-enterprise-feature.md](../runbooks/scenario-enterprise-feature.md) | NEXUS-Full | 8-12 weeks |
| Marketing Campaign | [scenario-marketing-campaign.md](../runbooks/scenario-marketing-campaign.md) | NEXUS-Sprint | 2-4 weeks |
| Incident Response | [scenario-incident-response.md](../runbooks/scenario-incident-response.md) | NEXUS-Micro | Hours |
| Rollback & Recovery | [scenario-rollback-recovery.md](../runbooks/scenario-rollback-recovery.md) | NEXUS-Micro | Minutes-Hours |

## Team Templates

| Team | Document | Agents | Scenario |
|------|----------|--------|----------|
| Agile Dev | [agile-dev-team.md](../teams/agile-dev-team.md) | 5-7 | Sprint development |
| Ecommerce Launch | [ecommerce-launch-team.md](../teams/ecommerce-launch-team.md) | 10-14 | Ecommerce platform |
| Mobile App | [mobile-app-team.md](../teams/mobile-app-team.md) | 8-12 | iOS + Android app |
| Data Platform | [data-platform-team.md](../teams/data-platform-team.md) | 9-13 | Enterprise data platform |
| AI Product | [ai-product-team.md](../teams/ai-product-team.md) | 9-13 | AI-driven product |
| Compliance Audit | [compliance-audit-team.md](../teams/compliance-audit-team.md) | 7-10 | SOC2/ISO/HIPAA certification |
| Content Marketing | [content-marketing-team.md](../teams/content-marketing-team.md) | 8-12 | Omnichannel content |
| Security Incident | [security-incident-team.md](../teams/security-incident-team.md) | 4-5 | Security incident |
| IPO Preparation | [ipo-preparation-team.md](../teams/ipo-preparation-team.md) | 5-6 | IPO readiness |
| Smart Factory | [smart-factory-team.md](../teams/smart-factory-team.md) | 7-9 | Smart factory |

## Coordination & Governance

| Document | Purpose | Key Audience |
|----------|---------|-------------|
| [handoff-templates.md](handoff-templates.md) | 7 agent-to-agent handoff templates | All agents |
| [agent-activation-prompts.md](agent-activation-prompts.md) | Ready-to-use activation prompt templates | Agents Orchestrator |
| [definition-of-done.md](definition-of-done.md) | Completion criteria for 20+ artifact types | Gate Keepers |
| [adr-template.md](adr-template.md) | Architecture Decision Record template | Backend Architect, UX Architect |
| [context-priming.md](context-priming.md) | Minimum Context Package per phase | Agents Orchestrator |
| [cross-cutting-concerns.md](cross-cutting-concerns.md) | 12 concerns with ownership + checklists | Gate Keepers |
| [pipeline-health-metrics.md](pipeline-health-metrics.md) | Pipeline self-measurement | Orchestrator, Studio Producer |
| [document-index.md](document-index.md) | This index — navigational map | Everyone |
| [DEVELOPMENT.md](../DEVELOPMENT.md) | Development environment setup, testing, CI | Contributors |
| [SCRIPT-ARCHITECTURE.md](../SCRIPT-ARCHITECTURE.md) | Scripts system overview and module map | Contributors, maintainers |
| [CONTRIBUTING-I18N.md](../CONTRIBUTING-I18N.md) | Translation/i18n contribution guide | Translators, contributors |

## Quick Finder — By Role

| I need to... | Read this |
|-------------|----------|
| Start a new project with NEXUS | nexus-strategy.md §15 (Quick-Start) |
| Activate an agent in a specific phase | context-priming.md + agent-activation-prompts.md |
| Hand off work to another agent | handoff-templates.md |
| Validate a deliverable is complete | definition-of-done.md |
| Make an architectural decision | adr-template.md |
| Check if quality concerns are tracked | cross-cutting-concerns.md |
| Know if the pipeline is healthy | pipeline-health-metrics.md |
| Respond to a production incident | scenario-incident-response.md + scenario-rollback-recovery.md |
| Know when to re-enter earlier phases | nexus-cycle.md |
| Find a pre-built agent team | teams/ directory |
| Set up a local dev environment | DEVELOPMENT.md |
| Understand the scripts system | SCRIPT-ARCHITECTURE.md |
| Contribute translations | CONTRIBUTING-I18N.md |

## Quick Finder — By Phase

| Phase | Primary Doc | Playbook | Key Coordination Docs |
|-------|-----------|----------|----------------------|
| 0 — Discovery | nexus-strategy.md §3 | phase-0-discovery.md | definition-of-done.md |
| 1 — Strategy | nexus-strategy.md §4 | phase-1-strategy.md | adr-template.md, cross-cutting-concerns.md |
| 2 — Foundation | nexus-strategy.md §5 | phase-2-foundation.md | cross-cutting-concerns.md |
| 3 — Build | nexus-strategy.md §6 | phase-3-build.md | handoff-templates.md, definition-of-done.md |
| 4 — Hardening | nexus-strategy.md §7 | phase-4-hardening.md | definition-of-done.md, cross-cutting-concerns.md |
| 5 — Launch | nexus-strategy.md §8 | phase-5-launch.md | scenario-rollback-recovery.md |
| 6 — Operate | nexus-strategy.md §9 | phase-6-operate.md | nexus-cycle.md, pipeline-health-metrics.md |
