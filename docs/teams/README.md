# Team Templates

Pre-built multi-agent teams with rosters, quality gates, activation prompts, and success metrics. Each template maps to a NEXUS pipeline mode.

## Templates

| Template | Scenario | Mode | Size | Quality Gates |
|----------|----------|------|------|---------------|
| [agile-dev-team](agile-dev-team.md) | Sprint development | Micro | 5-7 | 4 gates |
| [ecommerce-launch-team](ecommerce-launch-team.md) | Ecommerce platform | Full | 10-14 | 5 gates |
| [mobile-app-team](mobile-app-team.md) | iOS + Android app | Full | 8-12 | 6 gates |
| [data-platform-team](data-platform-team.md) | Enterprise data platform | Sprint | 9-13 | 6 gates |
| [ai-product-team](ai-product-team.md) | AI product development | Sprint | 9-13 | Decision points |
| [compliance-audit-team](compliance-audit-team.md) | SOC2/ISO/HIPAA | Full | 7-10 | 4 phases |
| [content-marketing-team](content-marketing-team.md) | Omnichannel content | Sprint | 8-12 | Brand checkpoints |
| [security-incident-team](security-incident-team.md) | Incident response | Micro | 4-5 | 5 gates |
| [ipo-preparation-team](ipo-preparation-team.md) | IPO readiness | Full | 5-6 | 6 gates |
| [smart-factory-team](smart-factory-team.md) | Factory construction | Full | 7-9 | 7 gates |

## How to Use

1. Pick a template matching your scenario and NEXUS mode
2. Review the agent roster and adjust for your project
3. Follow the phase timeline and quality gates
4. Use activation prompts to boot each agent with context
5. Track progress against success metrics

## Custom Teams

To create a new team template:
1. Follow the structure: Scenario → Roster → Workflow → Quality Gates → Activation Prompts → Success Metrics
2. Reference agents by their file ID (e.g. `engineering-backend-architect`)
3. Submit a PR to this directory
