# The Agency — Agent Tier Classification

> Generated 2026-07-24 by v7 scoring engine (scripts/score-agents.py --v7).
> ⚠️ Snapshot — run `python scripts/score-agents.py --v7 --json` to refresh.
> Part of Project Renaissance — Quality Shrink Plan.

## Summary

| Tier | Count | Categories | Criteria | Maintenance |
|------|-------|-----------|----------|-------------|
| **Gold** | 133 | 28 | ≥8pts, ≥2 tools, ≤3 boilerplate, ≥500 words | Active: depth enhancement to 2000+ words |
| **Silver** | 43 | 43 | Best remaining per category, ≥5pts | Active: 1-per-category coverage, needs enhancement |
| **Community** | 1,190 | 66 | Everything else | Community-maintained, no SLA |

## Tier 1 Gold

Criteria: score ≥8, tool/methodology references ≥2, boilerplate ≤3, words ≥500.
These agents demonstrate genuine domain expertise.

```
specialized-operations-manager       10/A  12 tools  52 cases  0 boiler  3256 words
product-b2b-manager                   9/A   8 tools  12 cases  1 boiler  5831 words
specialized-data-privacy-officer      9/A   6 tools  58 cases  0 boiler  3302 words
engineering-it-service-manager        9/A   5 tools  19 cases  1 boiler  2147 words
infrastructure-aws-architect          8/B  10 tools   4 cases  1 boiler  5014 words
infrastructure-graylog-expert         8/B   9 tools   6 cases  1 boiler  6782 words
infrastructure-github-actions-expert  8/B   7 tools   3 cases  1 boiler  4611 words
infrastructure-ansible-expert         8/B   6 tools   7 cases  1 boiler  5052 words
infrastructure-terraform-expert       8/B   6 tools   4 cases  1 boiler  4933 words
infrastructure-jumpserver-expert      8/B   7 tools   4 cases  1 boiler  3718 words
marketing-performance-analyst         8/B   7 tools   5 cases  1 boiler  5810 words
marketing-global-ua-manager           8/B   3 tools   2 cases  1 boiler  6791 words
customer-service-ticketing            8/B   4 tools   6 cases  1 boiler  3951 words
customer-service-complaints           8/B   2 tools  22 cases  1 boiler  3474 words
nonprofit-fundraiser                  8/B   3 tools   6 cases  2 boiler  3696 words
insurance-insurtech                   8/B   4 tools   6 cases  2 boiler  3923 words
network-engineering-operations        9/A   5 tools   6 cases  2 boiler  2269 words
network-engineering-architect         8/B   2 tools  15 cases  2 boiler  1969 words
data-science-ml-engineer              9/A   4 tools   5 cases  1 boiler  1931 words
data-science-bi-analyst               8/B   7 tools   2 cases  0 boiler  1015 words
data-science-huggingface-expert       8/B   2 tools   3 cases  0 boiler  2353 words
engineering-frontend-developer        8/B   4 tools   3 cases  2 boiler  1189 words
engineering-backend-architect         8/B   3 tools   3 cases  2 boiler  1255 words
engineering-software-architect        8/B   2 tools  17 cases  1 boiler  1166 words
engineering-mobile-app-builder        8/B   2 tools   6 cases  2 boiler  1474 words
engineering-cms-developer             9/A   3 tools  27 cases  1 boiler  1950 words
engineering-codebase-onboarding       9/A   3 tools   3 cases  1 boiler  1377 words
engineering-sqlserver-dba             9/A   5 tools   7 cases  1 boiler   794 words
engineering-build-release-engineer    9/A   7 tools   1 cases  1 boiler   640 words
engineering-cloud-dw-architect        9/A   3 tools   6 cases  0 boiler   718 words
engineering-wechat-mini-program       9/A   2 tools   5 cases  1 boiler  1436 words
... (103 more — see scripts/score-agents.py --json for full list)
```

## Tier 1 Silver

Best remaining agent from each of 43 categories not represented in Gold.
Criteria: highest score in category, ≥5pts minimum.
These agents provide baseline category coverage but need depth enhancement.

```
_solution-compliance-audit            8/B    tools=0  cases=0  words=486   (needs methodology)
agriculture-iot-engineer             9/A    tools=1  cases=18 words=1995   (add 1-2 named tools)
construction-surveyor                8/B    tools=1  cases=1  words=720
design-motion-designer               8/B    tools=1  cases=2  words=882
education-vocational-trade-teaching  9/A    tools=1  cases=6  words=749
energy-nuclear-fusion                9/A    tools=0  cases=8  words=700
environmental-sustainability-strategy 9/A   tools=0  cases=6  words=659
finance-fpa-analyst                  9/A    tools=1  cases=4  words=2439
game-development-game-designer       9/A    tools=1  cases=4  words=1200
government-urban-resilience          9/A    tools=0  cases=8  words=636
healthcare-engineering-regulatory    9/A    tools=1  cases=6  words=749
hr-onboarding                        9/A    tools=0  cases=20 words=2253
legal-document-review                9/A    tools=3  cases=16 words=2169
lottery-risk-compliance              7/B    tools=5  cases=10 words=2059
project-management-meeting-notes     8/B    tools=0  cases=2  words=874
real-estate-buyer-seller             9/A    tools=0  cases=23 words=2485
retail-category-manager              8/B    tools=1  cases=11 words=7998
sales-outreach                       9/A    tools=0  cases=20 words=2107
cybersecurity-cloud-security-architect    8/B    tools=7  cases=4  words=2913  (high tools but boiler=4)
thinking-models-ai-paradigms         7/B    tools=2  cases=0  words=837
web3-engineering-blockchain-architect 8/B   tools=1  cases=3  words=578
... (22 more)
```

## Tier 2 — Community

All remaining 1,190 agents. These are marked as community-maintained.

## Enhancement Priority (A4.1-A4.3 in WBS)

1. **P0**: 133 Gold agents → enhance to ≥2000 words with ≥3 domain cases each
2. **P1**: Top 10 Silver agents with highest upgrade potential (tools=1, words≥1000)
3. **P2**: Remaining Silver agents → ensure ≥1 named methodology per agent

## NEXUS Coverage After Shrink

With 133 Gold + 43 Silver = 176 maintained agents across all 62 categories,
NEXUS phase coverage is preserved. The depth improvement makes orchestration viable.
