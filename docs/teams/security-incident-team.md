# Security Incident Response Team

## Scenario
Security incident response — intrusion detection, vulnerability triage, attack forensics, and recovery.

- **NEXUS Mode**: Micro (5 agents, hours-to-days)
- **Related Runbook**: [scenario-incident-response.md](../runbooks/scenario-incident-response.md)

## Agent Roster

| Role | Agent | Responsibility |
|------|-------|---------------|
| Commander | `cybersecurity-incident-response` | Overall coordination, decision-making, external communication |
| Analyst | `cybersecurity-soc-analyst` | Log analysis, alert investigation, IOC extraction |
| Engineer | `security-appsec-engineer` | Vulnerability patching, fix deployment |
| Architect | `security-architect` | Architecture hardening, lateral movement blocking |
| Forensics | `cybersecurity-digital-forensics` | Evidence collection, chain of custody, timeline analysis |

## Workflow

```
Detection → Triage → Containment → Eradication → Recovery → Post-Mortem
```

### Phase Details

| Phase | Duration | Actions | Agents |
|-------|----------|---------|--------|
| Detection | Minutes | Alert fires, SOC Analyst begins investigation | Analyst |
| Triage | < 15 min | Determine severity (P0-P3), classify attack type | Commander + Analyst |
| Containment | < 1 hour | Isolate affected systems, block IOCs, rotate credentials | Engineer + Architect |
| Eradication | Hours | Remove root cause, patch vulnerability, harden | Engineer + Architect |
| Recovery | Hours-Days | Restore from clean backups, verify integrity, monitor | Engineer + Analyst |
| Post-Mortem | +24 hours | Root cause analysis, timeline, action items | All |

## Quality Gates

| Gate | Criteria | Gate Keeper |
|------|----------|-------------|
| Severity Classified | Correct P0-P3 assignment within 15 min | Commander |
| Containment Verified | Affected systems isolated, IOCs blocked, no lateral movement | Architect |
| Eradication Confirmed | Root cause removed, patch deployed, vulnerability scan clean | Engineer |
| Recovery Validated | All services restored, monitoring green for 24h | Analyst |
| Post-Mortem Complete | RCA document published, all action items assigned with owners | Commander |

## Critical Rules

1. **Containment before investigation** — stop the bleeding first
2. **Evidence preservation** — volatile order: memory → disk → logs → network captures
3. **Timestamp everything** — all actions logged with UTC timestamps
4. **Chain of custody** — evidence handling documented per forensic standards
5. **Need-to-know communication** — internal comms on secure channel, external via Commander only

## Activation Prompts

**Initial Response**:
```
CRITICAL: Activate Security Incident Response Team. Potential intrusion detected.
Alert source: [SIEM alert / IDS / user report]
Affected systems: [list]
Immediate action: Begin triage. Analyst — investigate logs. Engineer — prepare isolation procedures.
```

**Post-Mortem**:
```
Activate Post-Mortem facilitation. Incident [ID] has been resolved.
Timeline: [start-to-resolution]
Systems affected: [list]
Produce: Root cause analysis, timeline of events, 5-why analysis, action items with owners
```

## Success Metrics

| Metric | Target |
|--------|--------|
| Time to triage | < 15 minutes |
| Time to contain | < 1 hour (P0), < 4 hours (P1) |
| Time to resolve | < 24 hours (P0), < 72 hours (P1) |
| Post-mortem completion | Within 48 hours of resolution |
| Action item closure | 100% within 30 days |
