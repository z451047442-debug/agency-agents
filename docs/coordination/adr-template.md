# 📐 NEXUS Architecture Decision Records

> Template and index for recording significant architectural decisions. ADRs capture *why* a decision was made, not just *what* was decided. This context is critical when decisions are revisited in later phases.

---

## ADR Template

```markdown
# ADR-[NNN]: [Short Title]

**Status**: [Proposed / Accepted / Deprecated / Superseded by ADR-XXX]
**Date**: [YYYY-MM-DD]
**Deciders**: [Agent Name(s)]
**Phase**: Phase [N] — [Phase Name]

---

## Context

[Describe the problem, constraint, or forces at play. What is the current state? What requirement or goal is driving this decision? Include any relevant technical, business, or organizational constraints.]

## Decision

[What did we decide to do? Be specific and actionable. Include the concrete change, technology choice, pattern, or approach.]

## Consequences

### Positive
- [What becomes easier, faster, or better as a result]

### Negative
- [What trade-offs, costs, or limitations does this introduce]
- [What risks are we accepting]

### Neutral
- [What operational or organizational impacts should we anticipate]

## Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|-------------|
| [Option A] | [...] | [...] | [Reason] |
| [Option B] | [...] | [...] | [Reason] |
| [Status Quo] | [...] | [...] | [Reason] |

## References

- [Link to relevant specs, discussions, or previous ADRs]
```

---

## When to Write an ADR

Write an ADR when the decision is:

| Criterion | Write ADR | Skip |
|-----------|-----------|------|
| **Reversible?** | Hard to reverse | Easy to reverse |
| **Impact scope?** | Affects multiple phases/agents | Local to one task |
| **Cost to change?** | High (weeks of rework) | Low (hours of rework) |
| **Precedent?** | Sets a pattern others will follow | One-off decision |
| **Controversial?** | Multiple viable alternatives exist | Obvious right answer |

### Typical ADR Triggers
- Choosing between monolith / modular monolith / microservices
- Selecting a database technology (PostgreSQL vs MongoDB vs both)
- Deciding on an API paradigm (REST vs GraphQL vs gRPC)
- Authentication/authorization architecture
- State management strategy (frontend)
- Caching strategy
- Deployment strategy (monorepo vs polyrepo)
- Observability stack selection

---

## Minimum ADR Requirements per Phase

| Phase | Who Produces | Minimum ADRs | Typical Topics |
|-------|-------------|--------------|----------------|
| Phase 1 — Strategy | Backend Architect | ≥2 | System architecture, database choice, API paradigm |
| Phase 1 — Strategy | UX Architect | ≥1 | Design system approach, CSS methodology |
| Phase 1 — Strategy | AI Engineer (if active) | ≥1 | Model selection, inference architecture |
| Phase 2 — Foundation | DevOps Automator | ≥1 | CI/CD tooling, infrastructure choices |
| Phase 3 — Build | Any developer agent | As needed | Significant refactors, pattern changes |

---

## ADR Index

> Maintain a running index of all ADRs for this project in this file (below this paragraph). The index lives at docs/coordination/adr-template.md to keep all ADR documentation in one place. Add entries as ADRs are created.

| ADR # | Title | Status | Date | Deciders |
|-------|-------|--------|------|----------|
| — | (Example) ADR-001: PostgreSQL as Primary Database | Accepted | 2026-XX-XX | Backend Architect |
| — | (Example) ADR-002: REST over GraphQL for Public API | Superseded by ADR-005 | 2026-XX-XX | Backend Architect |

---

## Lifecycle

```
Proposed ──▶ Accepted ──▶ Deprecated ──▶ [archived]
                 │              │
                 └──▶ Superseded by ADR-XXX
```

- **Proposed**: Under discussion, not yet binding
- **Accepted**: Approved and active — implementation must follow this decision
- **Deprecated**: No longer relevant (project scope changed, technology evolved)
- **Superseded**: Replaced by a newer ADR (always reference which one)

---

## Review Cadence

- **Phase 1-2**: ADRs reviewed at Architecture Gate (Phase 1 → 2 transition)
- **Phase 3-4**: ADRs reviewed if a task escalates 3 times — check if the original decision was flawed
- **Phase 6**: Quarterly ADR audit — are any Accepted ADRs now outdated?

---

*ADRs are living documents. If you're revisiting a decision and the old ADR doesn't capture the full context, write a new one that supersedes it rather than editing the old one in place.*
