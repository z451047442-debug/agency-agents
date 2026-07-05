# ✅ NEXUS Definition of Done — Per Artifact Type

> Standardized completion criteria for every artifact type produced in the NEXUS pipeline. Gate Keepers use this as the baseline for PASS/FAIL decisions. Each artifact type lists **minimum** standards — specific tasks may add additional acceptance criteria.

---

## Discovery Artifacts

### Market Analysis Report
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | ≥15 unique, verifiable sources cited | Source list with URLs |
| 2 | TAM/SAM/SOM calculated with stated methodology | Calculation section |
| 3 | ≥3 direct competitors analyzed (not just listed) | Per-competitor SWOT |
| 4 | Trend lifecycle position stated with rationale | Adoption curve reference |
| 5 | 3-6 month forecast with confidence intervals | Forecast section |

### Synthesized Feedback Report
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | ≥5 distinct data sources (surveys, reviews, interviews, social, support tickets) | Source inventory |
| 2 | ≥3 validated pain points with frequency/severity scores | RICE-scored pain point table |
| 3 | Sentiment breakdown (% positive/neutral/negative) | Sentiment section |
| 4 | Feature request prioritization with business value estimate | Feature request table |
| 5 | Churn risk indicators identified | Risk indicator list |

### UX Research Findings Report
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | 3-5 primary personas with goals, pains, behaviors | Persona cards |
| 2 | Journey maps for ≥2 primary user flows | Journey map diagrams |
| 3 | ≥5 user interviews or ≥50 survey responses | Methodology section |
| 4 | Competitor usability heuristic evaluation (≥3 products) | Heuristic eval table |
| 5 | Behavioral insights with statistical significance noted | Findings section |

### Data Audit Report
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Complete data source inventory (what exists, where, format, owner) | Source catalog |
| 2 | ≥3 key signals/metrics identified | Signal map |
| 3 | Baseline metrics with date ranges | Baseline table |
| 4 | Data quality score per source (completeness, accuracy, freshness) | Quality matrix |
| 5 | Analytics infrastructure gap analysis | Gap list with recommendations |

### Compliance Requirements Matrix
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | All applicable regulations identified per target jurisdiction | Regulation list |
| 2 | Data handling constraints mapped (collection, storage, transfer, deletion) | Constraint map |
| 3 | Jurisdiction-by-jurisdiction breakdown | Jurisdiction table |
| 4 | Each requirement severity-rated (Blocking / Major / Minor / Advisory) | Severity column |
| 5 | Blocking vs. manageable issues clearly separated | Executive summary |

### Tech Stack Assessment
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | ≥3 technology options evaluated per component | Comparison matrix |
| 2 | Build vs. buy recommendation with rationale per component | Decision table |
| 3 | Integration feasibility assessed against existing systems | Compatibility matrix |
| 4 | Open source license compatibility checked | License table |
| 5 | Technology risk assessment (maturity, community, vendor lock-in) | Risk register |

### Executive Summary (SCQA Format)
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | ≤500 words | Word count |
| 2 | SCQA structure (Situation, Complication, Question, Answer) | Section headers |
| 3 | Quantified opportunity stated | Numbers present |
| 4 | Clear GO / NO-GO / PIVOT recommendation | Verdict line |
| 5 | All 6 discovery agent inputs referenced | Source attribution |

---

## Strategy & Architecture Artifacts

### Strategic Portfolio Plan
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Vision statement (1 paragraph) | Vision section |
| 2 | ≥3 strategic objectives with measurable KPIs | Objectives table |
| 3 | ROI targets with timeframe | Financial section |
| 4 | Strategic alignment with organizational goals | Alignment section |
| 5 | Resource allocation overview | Resource table |

### Brand Foundation Document
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Brand purpose + values defined | Purpose section |
| 2 | Logo system (primary, alternate, icon, wordmark) | Logo specs |
| 3 | Color palette (primary, secondary, accent, neutral) with hex codes | Color table |
| 4 | Typography system (headings, body, mono) with fallback stacks | Typography table |
| 5 | Voice & tone guidelines with examples | Voice section |

### System Architecture Specification
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Architecture diagram (ASCII or linked image) | Diagram |
| 2 | Service/components inventory with responsibilities | Component list |
| 3 | Database schema design (entities, relationships, indexes) | Schema section |
| 4 | API design principles + endpoint inventory | API section |
| 5 | Non-functional requirements addressed (security, performance, scalability) | NFR section |
| 6 | ≥1 ADR for significant architectural decisions | ADR references |

### CSS Design System / Layout Framework
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Design tokens defined (colors, spacing, typography, shadows, radii) | Token catalog |
| 2 | Responsive breakpoints defined (≥3) | Breakpoint table |
| 3 | Component primitives specified (buttons, inputs, cards, modals) | Component specs |
| 4 | Light + dark theme definitions | Theme files |
| 5 | Accessibility baseline (contrast ratios, focus indicators) | A11y section |

### Prioritized Sprint Backlog
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | All tasks RICE-scored (Reach, Impact, Confidence, Effort) | RICE column |
| 2 | Sprint assignments with velocity-based estimation | Sprint column |
| 3 | Dependency graph (what blocks what) | Dependency map |
| 4 | "Definition of Done" referenced per task | DoD column |
| 5 | Strategic alignment confirmed | Sign-off note |

### Financial Plan
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Resource cost breakdown (personnel, infra, tools, services) | Cost table |
| 2 | ROI projections with assumptions stated | ROI section |
| 3 | Budget vs. expected variance range (±%) | Variance analysis |
| 4 | Cash flow timeline (monthly burn rate) | Timeline |
| 5 | Risk-adjusted scenarios (best/base/worst case) | Scenario table |

---

## Foundation Artifacts

### CI/CD Pipeline
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Build stage passing | Build log |
| 2 | Test stage passing (unit + integration) | Test output |
| 3 | Deploy stage succeeding to at least one environment | Deploy log |
| 4 | Environment provisioning automated (IaC) | IaC templates |
| 5 | Secrets managed (not in code) | Secrets config |

### Database Schema
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | All entities/tables created per architecture spec | Schema dump |
| 2 | Indexes defined for query patterns | Index list |
| 3 | Migration files versioned and reversible | Migration files |
| 4 | Seed data available for development | Seed script |

### API Scaffold
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Health check endpoint responding (200 OK) | curl output |
| 2 | Auth endpoints working (register, login, token refresh) | curl output |
| 3 | API documentation auto-generated (OpenAPI/Swagger) | Docs URL |
| 4 | Error response format standardized | Error schema |
| 5 | Rate limiting configured | Rate limit config |

### App Skeleton
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | App loads without errors in browser | Screenshot |
| 2 | Navigation/routing functional | Screenshot |
| 3 | Design system tokens integrated | Inspector view |
| 4 | Responsive at ≥3 breakpoints | Screenshots |
| 5 | Dark/light theme toggling functional | Screenshots |

### Monitoring Setup
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Dashboards showing live metrics | Dashboard screenshot |
| 2 | Alerting configured for critical paths | Alert config |
| 3 | Log aggregation operational | Log query result |
| 4 | Uptime/health checks active | Status page |

---

## Build Artifacts

### Implemented Feature (per task)
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | All acceptance criteria from task card met | Per-criterion check |
| 2 | Visual QA: Desktop (1920), Tablet (768), Mobile (375) | Screenshots |
| 3 | Error/empty/loading states handled | Screenshots |
| 4 | Dark mode compatible (if applicable) | Screenshots |
| 5 | No console errors in browser | Console screenshot |
| 6 | Design system tokens used (no hardcoded values) | Code review |
| 7 | Responsive at all defined breakpoints | Screenshots |

### API Endpoint
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | 200 OK on happy path with correct response schema | Test output |
| 2 | 4xx on invalid input with descriptive error | Test output |
| 3 | 401/403 on missing/insufficient auth | Test output |
| 4 | Response time P95 < spec threshold | Load test |
| 5 | OpenAPI doc updated | Doc diff |

---

## Hardening Artifacts

### QA Evidence Package
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Full page screenshot suite (all pages × 3 viewports × 2 themes) | Screenshot directory |
| 2 | Complete user journey recordings (≥3 critical paths) | Recordings |
| 3 | Error state coverage (404, 500, validation, network, empty) | Screenshots |
| 4 | Accessibility audit (axe-core or similar, zero critical violations) | Audit report |
| 5 | Cross-browser screenshots (Chrome, Firefox, Safari, Edge) | Screenshots |

### Performance Certification
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Load test at 10x expected traffic | Load test report |
| 2 | P95 latency < 200ms (API) | Latency chart |
| 3 | Lighthouse Performance ≥ 90 | Lighthouse report |
| 4 | Lighthouse Accessibility ≥ 90 | Lighthouse report |
| 5 | No memory leaks in sustained test | Memory graph |

### Integration Test Report (Reality Checker)
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | All critical user journeys tested end-to-end | Journey results |
| 2 | Cross-device consistency verified | Comparison grid |
| 3 | Specification point-by-point compliance (100%) | Compliance table |
| 4 | Security scan with zero critical findings | Scan report |
| 5 | Verdict: READY / NEEDS WORK / NOT READY with evidence | Verdict section |

---

## Operating Artifacts

### Incident Post-Mortem
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Timeline with timestamps | Timeline |
| 2 | Root cause identified (not just symptom) | RCA section |
| 3 | Impact quantified (users affected, duration, data loss) | Impact section |
| 4 | ≥2 action items with owners and deadlines | Action items |
| 5 | Detection gap identified (how to catch earlier next time) | Detection section |

### Monthly Executive Report
| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Key metrics vs. targets | Metrics table |
| 2 | Wins/losses for the period | Highlights section |
| 3 | Risk register update | Risk table |
| 4 | Forward-looking recommendations | Recommendations |
| 5 | ≤1 page (executive-readable) | Length check |

---

## Usage

1. Gate Keepers reference this document when evaluating phase gate criteria
2. Producers (developer agents) self-check their artifact against this list before handoff
3. Sprint Prioritizer may add task-specific criteria on top of these minimums
4. If an artifact type is missing, add it via PR with the same table format


## Operations Artifacts

### ML System Design
- [ ] Model architecture documented (input/output shapes, latency targets)
- [ ] Training data requirements specified (volume, labeling, freshness)
- [ ] Inference pipeline designed (batch/real-time, hardware requirements)
- [ ] Evaluation metrics defined with acceptance thresholds

### Infrastructure Readiness Report
- [ ] All health check endpoints verified (200 OK)
- [ ] Monitoring dashboards operational with > 7 days of data
- [ ] Alerting rules tested with test notifications
- [ ] SSL certificates valid (> 30 days remaining)

### Compliance Certification Report
- [ ] All regulatory requirements listed with compliance status
- [ ] Evidence artifacts attached for each requirement
- [ ] Gaps documented with remediation plan and timeline
- [ ] Signed off by Legal Compliance Checker

### Quality Metrics Dashboard
- [ ] All QA findings from current phase aggregated
- [ ] Metrics visualized (pass rate, defect distribution, retry count)
- [ ] Trend comparison vs. previous phase included
- [ ] Top 5 quality risks highlighted

### Sprint Plan
- [ ] All stories have acceptance criteria and estimates
- [ ] Dependency map for cross-team stories
- [ ] Sprint goal stated in one sentence
- [ ] Capacity planning accounts for meetings, on-call, and buffer

### Sprint Review Summary
- [ ] Demo recording or screenshots of completed work
- [ ] Completed vs. committed story comparison
- [ ] Stakeholder feedback captured

### Retrospective Action Items
- [ ] At least 3 actionable items with owners and due dates
- [ ] Items tracked from previous retro (closed or carried forward)

### Operations Playbook
- [ ] Runbook for each critical operational procedure
- [ ] Escalation paths defined with contact information
- [ ] On-call rotation documented

### Monthly Financial Report
- [ ] Budget vs. actuals by cost category
- [ ] Variance explanation for items > 10% deviation
- [ ] Burn rate and runway projection

### Marketing Content Pipeline
- [ ] Content calendar covering all active channels
- [ ] At least 2 weeks of scheduled content queued
- [ ] Brand review completed for all assets

### Optimization Recommendations Report
- [ ] Process bottlenecks identified with quantitative evidence
- [ ] At least 3 improvement recommendations with ROI estimates
- [ ] Prioritized by impact/effort ratio
