# Changelog

> **Note:** This changelog is now automatically generated and maintained by
> [release-please](https://github.com/googleapis/release-please). It follows
> [Conventional Commits](https://www.conventionalcommits.org/) and is updated
> on each release via the `.github/workflows/release.yml` workflow.
>
> Entries prior to v1.0.0 were maintained manually.

All notable changes to The Agency project will be documented in this file.

## [Unreleased]

### Added
- CLAUDE.md for Claude Code project-level guidance
- CHANGELOG.md to track project history
- `.github/CODEOWNERS` for domain stewardship
- `version` + `date_added` fields to agent frontmatter JSON Schema
- 8 new monitoring/logging/network agents: Zabbix, Nagios, Cacti, OpenNMS, Wireshark, ELK Stack, Graylog, Jump Server

### Changed
- **Architecture**: Moved NEXUS docs from `strategy/` to `docs/` — `strategy/` now pure agent directory
- **Reorganization**: 12 `specialized/` agents re-categorized to proper domain directories
- `engineering/` pruned 411→73 agents (308 moved to domain directories)
- 15 new domain directories created
- `project-delivery/` merged into `project-management/`, `academic/` merged into `education/`
- 58 new agents added (thin categories + new domains + monitoring tools)
- Scripts updated to exclude `docs/`, `generate_slnx.py` paths updated
- AGENTS.json: 1083 agents across 60 categories

---

## Previous Releases

### 2026-06

- Fix opencode global install docs (#249)
- Add Qwen integration guide (#232)
- Align OpenClaw install path docs (#231)
- Align agent linting with OpenClaw section split (#230)
- Post-install hint for Copilot agent path verification (#224)
- 14 new agents added to README roster (#439)

### 2026-05

- **i18n**: Chinese (zh-CN) localization for agent names (#338)
- New agents: loan officer assistant (#424), real estate (#423), legal billing (#422), legal client intake (#421), legal document review (#417), language translator (#416), sales outreach (#414), HR onboarding (#413), customer service (#412), retail returns (#420), hospitality (#419), healthcare customer service (#418)
- Finance category added to scripts, CI, README (#437)
- Contributing template alignment (#436, #433)
- Codebase Onboarding Engineer (#388), Voice AI Integration Engineer (#415)
- Chief of Staff agent (#429)

### Earlier

- Vitest test infrastructure for agent/script validation (#337)
- Promptfoo eval harness for agent quality scoring (#371)
- Agentic Search Optimizer (#398)
- SEO Specialist cannibalization rules (#399)
- Minimal Change Engineer (#430)
