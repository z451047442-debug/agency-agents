# Agile Development Team

## Scenario
Sprint-based development — from backlog item to shippable increment.

- **NEXUS Mode**: Sprint
- **Team Size**: 5-7 agents
- **Sprint Duration**: 2 weeks

## Agent Roster

| Role | Agent | Responsibility |
|------|-------|---------------|
| Scrum Master | `project-management-scrum-master` | Standups, retrospectives, impediment removal |
| Frontend | `engineering-frontend-developer` | UI implementation, component development |
| Backend | `engineering-backend-architect` | APIs, database, server-side logic |
| QA | `testing-automation-architect` | Test automation, defect verification |
| PM | `product-manager` | Requirements, acceptance criteria |

## Workflow

```
Sprint Planning → Daily Standup → Dev → Code Review → QA → Sprint Review → Retro
```

### Sprint Schedule

| Day | Activity | Agents |
|-----|----------|--------|
| Day 1 | Sprint Planning: PM presents prioritized backlog, team estimates | PM, Scrum Master, All |
| Daily | 15-min standup: what was done, what's next, blockers | All |
| Day 1-8 | Development + code review (Dev↔QA loop per task) | Frontend, Backend |
| Day 3,6,9 | QA regression pass | QA |
| Day 9-10 | Bug fixes, polish | Frontend, Backend |
| Day 10 | Sprint Review: demo to stakeholders | All + PM |
| Day 10 | Retrospective: what went well, what to improve | All |

## Quality Gates

| Gate | When | Criteria | Gate Keeper |
|------|------|----------|-------------|
| Sprint Ready | Day 1 | All stories have acceptance criteria, estimates ≤ 1 day | PM |
| Code Review | Per PR | PR approved by another dev, no lint errors | Backend/Frontend |
| QA Pass | Day 3,6,9 | All acceptance criteria verified, no P0/P1 bugs | QA |
| Sprint Complete | Day 10 | All committed stories DONE, demo passed | Scrum Master |

## Activation Prompts

**Sprint Planning**:
```
Activate Sprint Prioritizer and Scrum Master. Review backlog for next sprint.
Context: [current sprint status, velocity data]
Deliverable: Prioritized sprint backlog with estimates
```

**Development Task**:
```
Activate Frontend Developer. Implement task [TASK-ID] per acceptance criteria.
Architecture: [link to architecture spec]
Design system: [link to component library]
When complete, hand off to QA for verification.
```

## Success Metrics

| Metric | Target |
|--------|--------|
| Sprint velocity stability | ±15% of rolling 3-sprint average |
| First-pass QA rate | ≥ 70% |
| Code review turnaround | < 4 hours |
| Sprint completion rate | ≥ 85% of committed stories |
| Defect escape rate | < 5% of stories per sprint |
