# IPO Preparation Team

## Scenario
IPO readiness — financial compliance, legal due diligence, prospectus drafting, investor relations.

- **NEXUS Mode**: Full (6 agents, 18-24 months)
- **Related Runbook**: [scenario-incident-response.md](../runbooks/scenario-incident-response.md)  *(IPO-specific runbook not yet created; this team follows NEXUS-Full mode directly)*

## Agent Roster

| Role | Agent | Responsibility |
|------|-------|---------------|
| CFO | `chief-financial-officer` | Financial strategy, equity story, investor narrative |
| IPO Advisor | `finance-ipo-advisor` | IPO process, financial remediation, prospectus financials |
| Controller | `finance-financial-controller` | Audit-ready financials, SOX/internal controls |
| General Counsel | `legal-general-counsel` | Legal DD, regulatory compliance, prospectus legal sections |
| Internal Audit | `finance-internal-auditor` | SOX testing, control validation |
| Strategist | `strategy-business-strategist` | Corporate positioning, competitive landscape analysis |

## Workflow

```
Financial Remediation → Audit → Prospectus → Regulatory Review → Roadshow → Pricing & Listing
```

### Phase Timeline

| Phase | Months | Activities | Agents |
|-------|--------|-----------|--------|
| Gap Assessment | M-24 to M-18 | Assess financial systems, controls, team readiness | CFO, Controller, Internal Audit |
| Remediation | M-18 to M-12 | Upgrade financial systems, implement SOX controls | Controller, Internal Audit |
| Audit | M-12 to M-6 | External auditor review, comfort letters | Controller, IPO Advisor |
| Prospectus | M-6 to M-3 | Draft S-1/F-1, risk factors, MD&A | IPO Advisor, GC, Strategist |
| Regulatory | M-3 to M-1 | SEC/regulator comments, amendments | GC, IPO Advisor |
| Roadshow | M-1 to Listing | Investor presentations, pricing | CFO, IPO Advisor, Strategist |
| Post-IPO | Listing+ | Quiet period compliance, earnings cadence | CFO, Controller |

## Quality Gates

| Gate | When | Criteria | Gate Keeper |
|------|------|----------|-------------|
| Remediation Complete | M-12 | Financial systems auditable, SOX controls designed | Internal Audit |
| Audit Sign-off | M-6 | Unqualified audit opinion, no material weaknesses | External Auditor |
| Prospectus Filed | M-3 | All sections complete, board approved | GC |
| SEC Clearance | M-1 | All comments resolved, effective date set | GC + IPO Advisor |
| Roadshow Ready | M-0.5 | Investor deck finalized, management prepped | CFO |
| Listing | Day 0 | Stock trades, quiet period begins | CFO + GC |

## Activation Prompts

**Gap Assessment**:
```
Activate CFO, Controller, and Internal Audit. Conduct IPO readiness gap assessment.
Review: current financial systems, team structure, SOX readiness, historical financials
Deliverable: Gap analysis report with remediation timeline and cost estimates
```

**Prospectus Drafting**:
```
Activate IPO Advisor and General Counsel. Draft S-1 registration statement.
Context: [gap assessment results, audited financials, corporate governance docs]
Sections: Business overview, risk factors, MD&A, financial statements
Deliverable: Complete S-1 draft for board review
```

## Success Metrics

| Metric | Target |
|--------|--------|
| Audit opinion | Unqualified |
| Material weaknesses | Zero at filing |
| SEC comment rounds | <= 2 rounds |
| Roadshow oversubscription | >= 3x |
| First-day trading | Within +/-15% of pricing |
