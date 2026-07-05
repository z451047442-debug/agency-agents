# Smart Factory Construction Team

## Scenario
Greenfield factory or brownfield retrofit — from civil works to MEP to intelligent systems to production launch.

- **NEXUS Mode**: Full (9 agents, 18-36 months)
- **Industry**: Manufacturing / Construction

## Agent Roster

| Role | Agent | Responsibility |
|------|-------|---------------|
| Architect | `construction-architectural-designer` | Facility design, spatial planning, code compliance |
| Construction PM | `construction-project-manager` | Schedule, budget, subcontractor coordination, safety |
| HVAC | `construction-hvac` | Climate control, cleanroom design, dust extraction |
| Electrical | `construction-electrical` | Power distribution, lighting, lightning protection |
| Plumbing | `construction-plumbing` | Water supply, drainage, fire water systems |
| Low Voltage | `construction-low-voltage` | Structured cabling, security, BAS/BMS integration |
| Fire Protection | `construction-fire-protection` | Fire alarm, sprinkler, smoke control, regulatory approval |
| Production Planner | `manufacturing-production-planner` | Line layout, capacity planning, production scheduling |
| Quality | `manufacturing-quality-manager` | Quality management system, ISO certification |

## Workflow

```
Feasibility → Schematic Design → Construction Docs → Bidding → Civil → MEP → Commissioning → Fire Inspection → Production Launch
```

### Phase Timeline

| Phase | Duration | Activities | Agents |
|-------|----------|-----------|--------|
| Feasibility | Month 1-2 | Site evaluation, capacity planning, budget | Architect, Construction PM, Production Planner |
| Schematic Design | Month 2-4 | Floor plans, elevations, system sizing | Architect, All Engineers |
| Construction Docs | Month 4-6 | Detailed drawings, specs, permit applications | All Engineers |
| Bidding | Month 6-7 | RFQ, bid evaluation, contract award | Construction PM |
| Civil/Structural | Month 7-12 | Foundation, steel structure, enclosure | Construction PM |
| MEP Installation | Month 10-16 | HVAC, electrical, plumbing, fire protection | HVAC, Electrical, Plumbing, Fire, Low Voltage |
| Commissioning | Month 15-17 | System testing, integration, balancing | All Engineers |
| Fire Inspection | Month 17-18 | Fire department approval, occupancy permit | Fire Protection, Construction PM |
| Production Ramp | Month 18-20 | Equipment installation, trial runs, QC setup | Production Planner, Quality |

## Quality Gates

| Gate | When | Criteria | Gate Keeper |
|------|------|----------|-------------|
| Design Review | Month 4 | All disciplines coordinated, no BIM clashes | Architect |
| Permit Issued | Month 6 | Building permit + fire permit approved | Construction PM |
| Structural Complete | Month 12 | Steel erected, roof on, weathertight | Construction PM |
| MEP Rough-in | Month 14 | All rough-in inspected and approved | Each Engineer |
| Commissioning Pass | Month 17 | All systems tested, BMS operational | All Engineers |
| Fire Approval | Month 18 | Fire inspection passed, occupancy certificate | Fire Protection |
| Production Trial | Month 19 | 3 consecutive days at > 85% target OEE | Production Planner |

## Critical Rules

1. **Fire inspection is the final gate** — no production before fire department sign-off
2. **MEP coordination is the highest risk** — water, power, air, and low-voltage routing must be clash-free in BIM
3. **Change orders cascade** — a single discipline change may impact all others; always re-coordinate
4. **Commissioning is not testing** — commissioning verifies integrated system performance, not just individual equipment
5. **Safety during construction** — HSE manager must be on-site full-time during civil and MEP phases

## Activation Prompts

**Schematic Design**:
```
Activate Architectural Designer and all engineering disciplines. Begin schematic design.
Site: [address / plot dimensions]
Requirements: [production capacity, cleanroom class, office space, warehouse]
Deliverable: Coordinated schematic design package with floor plans and system sizing
```

**Commissioning**:
```
Activate all engineering disciplines for integrated commissioning.
Scope: HVAC balancing, electrical load testing, fire alarm verification, BMS integration
Method: Test each system individually, then test integrated scenarios
Deliverable: Commissioning report with test results and punch list
```

## Success Metrics

| Metric | Target |
|--------|--------|
| Design clash count (BIM) | Zero at CD issue |
| Schedule variance | < 5% at each phase gate |
| Budget variance | < 10% at project completion |
| Fire inspection | Pass on first attempt |
| Production OEE at launch | >= 85% |
| ISO certification | Within 3 months of launch |
