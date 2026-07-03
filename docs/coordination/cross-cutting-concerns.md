# 🔀 NEXUS Cross-Cutting Concerns Register

> Cross-cutting concerns (CCC) are quality attributes that span multiple phases and agent divisions. They cannot be verified by a single agent in a single phase — they require ongoing attention throughout the pipeline. This register defines ownership, entry points, and verification cadence for each concern.

---

## Concern Ownership Matrix

| Concern | Primary Owner | Start Phase | Verify Phases | Blocking at Gate | Standard/Framework |
|---------|--------------|-------------|---------------|------------------|-------------------|
| **Security** | Legal Compliance Checker → Infra Maintainer | Phase 1 | 2, 3, 4, 6 | Every gate | OWASP Top 10, threat model |
| **Performance** | Performance Benchmarker | Phase 2 | 3, 4, 6 | Phase 4 gate | Core Web Vitals, P95 < 200ms |
| **Accessibility (A11y)** | Evidence Collector | Phase 2 | 3, 4 | Phase 4 gate | WCAG 2.1 AA, axe-core |
| **Privacy & Data Protection** | Legal Compliance Checker | Phase 1 | 2, 4, 6 | Phase 4 gate | GDPR, CCPA, PIPL |
| **Internationalization (i18n)** | UX Architect | Phase 1 | 3, 4 | Phase 4 gate (if multi-locale) | Unicode CLDR, ICU |
| **Localization (L10n)** | Content Creator | Phase 3 | 4, 5 | Phase 4 gate (if multi-locale) | Per-locale review |
| **Observability** | Infrastructure Maintainer | Phase 2 | 3, 4, 6 | Phase 2 gate | OpenTelemetry, SLO/SLI |
| **Brand Consistency** | Brand Guardian | Phase 1 | 3, 4, 5 | Phase 4 gate | Brand guidelines |
| **Technical Debt** | Workflow Optimizer | Phase 3 | 4, 6 | Phase 4 gate (warning only) | Debt register |
| **Cost Efficiency** | Finance Tracker | Phase 1 | 3, 6 | None (advisory) | Budget vs. actual |
| **Resilience / DR** | Infrastructure Maintainer | Phase 2 | 4, 6 | Phase 4 gate | RPO/RTO targets |
| **SEO / Discoverability** | Growth Hacker | Phase 3 | 4, 5 | Phase 4 gate (if public-facing) | Lighthouse SEO, Core Web Vitals |

---

## Per-Concern Verification Checklists

### Security
- [ ] **Phase 1**: Threat model produced (STRIDE or similar). Security requirements in architecture spec
- [ ] **Phase 2**: Auth system implemented. Secrets management in place. Dependency scan configured in CI
- [ ] **Phase 3**: Per-task security review for auth-adjacent features. SAST in CI pipeline
- [ ] **Phase 4**: Full security scan (SAST + DAST + dependency). Zero critical findings required
- [ ] **Phase 6**: Monthly vulnerability scan. Dependency updates applied within SLA

### Performance
- [ ] **Phase 2**: Performance baseline established. CI includes Lighthouse/LCP budget
- [ ] **Phase 3**: Per-task performance check (no regression > 10% from baseline)
- [ ] **Phase 4**: Load test at 10x traffic. P95 < 200ms. LCP < 2.5s. Lighthouse ≥ 90
- [ ] **Phase 6**: Weekly performance trend report. Alert on degradation

### Accessibility
- [ ] **Phase 2**: Design system includes focus indicators, contrast ratios, semantic HTML spec
- [ ] **Phase 3**: Per-component axe-core audit. Keyboard navigation verified per task
- [ ] **Phase 4**: Full a11y audit — zero critical, zero serious violations. Screen reader test
- [ ] **Phase 6**: Quarterly a11y re-audit

### Privacy & Data Protection
- [ ] **Phase 1**: Data flow diagram with PII identified. DPIA if required. Consent requirements mapped
- [ ] **Phase 2**: Encryption at rest + in transit. Data retention policies configured
- [ ] **Phase 4**: Privacy audit. Cookie consent operational. DSAR process documented
- [ ] **Phase 6**: Monthly privacy review. Data subject request handling verified

### Internationalization (i18n)
- [ ] **Phase 1**: Locale list defined. i18n library chosen. Date/number/currency format requirements
- [ ] **Phase 3**: All user-facing strings externalized. RTL layout tested for ≥1 RTL locale
- [ ] **Phase 4**: Pseudo-localization test. Locale-specific format verification

### Observability
- [ ] **Phase 2**: Monitoring dashboards live. Alerting configured. Log aggregation operational
- [ ] **Phase 3**: Per-service metrics exposed. Trace propagation configured
- [ ] **Phase 4**: SLOs defined. Alert thresholds tuned. Runbooks documented
- [ ] **Phase 6**: Weekly SLO review. Alert fatigue monitored

### Brand Consistency
- [ ] **Phase 1**: Brand Foundation Document complete
- [ ] **Phase 3**: Per-sprint brand audit (spot-check 5 random views)
- [ ] **Phase 4**: Full brand audit — 95%+ adherence required
- [ ] **Phase 5**: Launch content brand review

### Technical Debt
- [ ] **Phase 3**: Debt items logged with severity and estimated remediation cost
- [ ] **Phase 4**: Debt register reviewed. Critical/High items must be resolved pre-launch
- [ ] **Phase 6**: Quarterly debt review. 20% of sprint capacity allocated to debt reduction

### Resilience / Disaster Recovery
- [ ] **Phase 2**: RPO/RTO targets defined. Backup strategy implemented
- [ ] **Phase 4**: DR runbook documented. Recovery tested (at least tabletop)
- [ ] **Phase 6**: Quarterly DR test. RPO/RTO compliance verified

---

## Escalation Rules

| Concern | Trigger | Escalate To | Action |
|---------|---------|------------|--------|
| Security | Critical vulnerability found | Studio Producer | Stop pipeline, fix immediately |
| Performance | P95 > 2x threshold | Backend Architect | Dedicated performance sprint |
| Accessibility | >5 serious violations | UX Architect | Fix before Phase 4 gate |
| Privacy | Unauthorized data access | Legal Compliance Checker | Incident response protocol |
| Brand | <80% adherence | Brand Guardian | Fix before launch |
| Observability | No Production metrics | Infrastructure Maintainer | Block Phase 5 launch |

---

## Phase Gate Integration

Each Quality Gate must explicitly check the CCCs that are "Blocking at Gate" for that phase. The Gate Keeper references this register to determine which concerns to verify.

Gate Keepers: if a concern is marked "Blocking at Gate" for your phase and it fails, the gate **must** return FAIL — no exceptions, no waivers without Studio Producer sign-off.
