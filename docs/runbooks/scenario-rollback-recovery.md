# ⏪ Runbook: Rollback & Recovery

> **Mode**: NEXUS-Micro | **Duration**: Minutes to hours | **Agents**: 3-5

---

## Scenario

A deployment has gone wrong — the new version introduced a regression, a performance degradation, or a breaking change. You need to roll back safely while minimizing user impact and preserving evidence for root cause analysis.

---

## Pre-Deployment Rollback Readiness (Phase 5 Prerequisite)

Before any production deployment, the DevOps Automator must produce and validate:

- [ ] Rollback command/script tested in staging (not just documented)
- [ ] Rollback time measured: target < 5 minutes
- [ ] Database migration rollback tested (if schema changes included)
- [ ] Feature flags in place for high-risk changes (enable/disable without deploy)
- [ ] Error rate alert threshold set (e.g., >1% 5xx in 5 minutes)
- [ ] P95 latency alert threshold set (e.g., >2x baseline)
- [ ] Business metric alert set (e.g., checkout completion rate drop >10%)
- [ ] Incident channel identified
- [ ] Stakeholder notification template prepared
- [ ] Status page update process documented
- [ ] Decision authority defined (DevOps Automator — P0 autonomous, Studio Producer — P1/P2)

---

## Agent Roster

| Agent | Role |
|-------|------|
| **DevOps Automator** | Rollback execution, deployment verification |
| **Infrastructure Maintainer** | System monitoring, health verification post-rollback |
| **Analytics Reporter** | Real-time metric comparison (before/after rollback) |
| **Support Responder** | User communication, status updates |
| **Executive Summary Generator** | Stakeholder communication, post-mortem summary |

---

## Rollback Decision Tree

```
Deployment complete (Phase 5 Launch)
    │
    ▼
┌─────────────────────────────┐
│ Monitoring: first 30 minutes │
│ (DevOps + Infra Maintainer)  │
└──────────────┬──────────────┘
               │
    ┌──────────▼──────────┐
    │ Any alert triggered? │
    └──────┬──────────┬───┘
           │          │
          YES         NO
           │          │
           │          └──▶ Continue monitoring (standard Phase 5)
           │
    ┌──────▼──────────────────────┐
    │ Classify Severity           │
    │ (Infrastructure Maintainer) │
    └──────┬──────────────────────┘
           │
    ┌──────▼──────┬──────────┬──────────┐
    │    P0       │    P1    │   P2/P3  │
    │ Critical    │  High    │  Med/Low │
    └──────┬──────┴────┬─────┴────┬─────┘
           │           │          │
           ▼           ▼          ▼
    ┌──────────┐ ┌──────────┐ ┌──────────────┐
    │ IMMEDIATE│ │ ROLLBACK │ │ MONITOR &    │
    │ ROLLBACK │ │ within   │ │ fix-forward   │
    │ No       │ │ 4 hours  │ │ (next sprint) │
    │ approval │ │ w/Studio │ │               │
    │ needed   │ │ Producer │ │               │
    └──────────┘ └──────────┘ └──────────────┘
```

---

## Rollback Execution Protocol

### Step 1: Trigger Rollback (DevOps Automator)

1. Announce in incident channel: "ROLLBACK INITIATED: [service] to version [previous]. Reason: [brief]"
2. Execute rollback (revert deployment, down migration if needed, invalidate caches)
3. Verify: health checks green, smoke test critical paths, error rate returning to baseline

### Step 2: Verify Recovery (Infrastructure Maintainer + Analytics Reporter)

- Monitor error rate for 15 minutes post-rollback
- Verify all service health checks green
- Compare real-time metrics vs. pre-deployment baseline
- Report: "Systems stable" or "Issues persist"

### Step 3: Communicate (Support Responder + Executive Summary Generator)

- Update status page: "Investigating" → "Monitoring" → "Resolved"
- Respond to user reports with templated acknowledgment
- Draft stakeholder notification after 30 min stable

### Step 4: Preserve Evidence (All agents)

- Preserve deployment logs, error logs, monitoring dashboards (screenshots at time of incident)
- Preserve user reports
- Create incident ticket with all evidence attached

---

## Post-Rollback: Root Cause Analysis

After systems are stable (not during the incident):

1. DevOps Automator → Deployment diff analysis (what changed?)
2. Infrastructure Maintainer → System behavior analysis (what broke?)
3. Backend Architect → Architectural review (design flaw or implementation bug?)
4. Test Results Analyzer → Test gap analysis (why didn't tests catch this?)

Output: Incident Post-Mortem (see Definition of Done for standards)

---

## Rollback Runbook Template

Every service should have a filled copy of this template before Phase 5:

```markdown
# Rollback Runbook: [SERVICE NAME]

## Rollback Command
[exact command to execute rollback]
Estimated execution time: [N] minutes

## Pre-Rollback Checks
- [ ] Confirm alert is not a false positive (check [dashboard URL])
- [ ] Check if database migration was part of deploy

## Rollback Steps
1. [Step 1 with exact command]
2. [Step 2 with exact command]
3. [Step 3 with exact command]

## Post-Rollback Verification
- [ ] Health check: [URL] → expect 200
- [ ] Smoke test: [critical user flow]
- [ ] Error rate: [dashboard URL] → expect < [threshold]

## If Rollback Fails
- Escalate to: [Backup contact]
- Manual recovery procedure: [documented steps]

## Decision Matrix
| Severity | Who Decides | Max Decision Time |
|----------|------------|-------------------|
| P0 | DevOps Automator (autonomous) | Immediate |
| P1 | Studio Producer | < 4 hours |
| P2/P3 | Sprint Prioritizer | Next sprint |

## Communication Templates

### Status Page: Incident Open
"We are investigating elevated error rates affecting [feature]. Impact: [users affected]. Next update in 30 minutes."

### Status Page: Monitoring
"Rollback complete. Systems are recovering. We are monitoring closely."

### Status Page: Resolved
"Service restored. [Brief root cause summary]. A full post-mortem will follow."

### Stakeholder Email
"Today at [time], a deployment to [service] caused [impact]. The deployment was rolled back within [N] minutes. All systems are now stable. A root cause analysis is underway and will be shared within 48 hours."
```

---

## Common Pitfalls

| Pitfall | Mitigation |
|---------|-----------|
| Rolling back without preserving logs | Evidence preservation is mandatory before any fix |
| DB migration rollback not tested | Must be tested in staging as part of rollback readiness |
| Fixing forward without understanding root cause | RCA team activated before any re-deploy attempt |
| No decision authority defined for P1 | Studio Producer pre-authorized DevOps Automator for P0 only |
| Rollback takes > 30 minutes | Time-box: if rollback exceeds 30 min, escalate to manual recovery |
