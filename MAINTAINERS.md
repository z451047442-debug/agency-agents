# Maintainers

This document describes the governance model for The Agency project.

## Maintainer Ladder

| Level | Role | Commit Access | Review Authority |
|-------|------|---------------|------------------|
| 1 | Casual Contributor | No | None (PR required) |
| 2 | Category Maintainer | To assigned categories | Within assigned categories |
| 3 | Core Maintainer | Full | Cross-category, CI, scripts |

### Level 2 — Category Maintainer

A Category Maintainer owns one or more agent categories. Responsibilities:

- Review and merge PRs within their categories
- Ensure agents in their categories meet quality standards (score >= 8, matching the CI `--threshold 8` gate)
- Keep agents up to date with domain knowledge
- Flag stale or low-quality agents for review

Prerequisites:
- At least 5 merged PRs in the target category
- Demonstrated domain expertise in the category's field
- Nominated by an existing Core Maintainer

### Level 3 — Core Maintainer

Core Maintainers oversee the project as a whole:

- Review and merge PRs across all categories
- Maintain CI/CD pipelines, tooling scripts, and NEXUS orchestration
- Manage releases and the CHANGELOG
- Nominate and onboard Category Maintainers
- Make architectural decisions (taxonomy, tooling, integrations)

Prerequisites:
- Served as a Category Maintainer for at least 3 months
- Significant contributions to tooling scripts, CI, or NEXUS
- Unanimous approval from existing Core Maintainers

## Current Maintainers

| Name | Role | GitHub |
|------|------|--------|
| @z451047442-debug | Core Maintainer | @z451047442-debug |

> The Agency is actively seeking Category Maintainers. See
> [CONTRIBUTING.md](CONTRIBUTING.md) for how to get started.

## Decision Making

1. **Agent content changes**: approval from one Category or Core Maintainer
2. **Tooling changes** (scripts/, CI, NEXUS): approval from one Core Maintainer
3. **Category creation**: discussion in an issue + Core Maintainer approval
4. **Breaking changes** (format, required fields): majority Core Maintainer approval

## Nomination Process

1. Open an issue titled "Nominate @username as [category] maintainer"
2. Link to the contributor's merged PRs
3. Core Maintainers vote (+1/-1)
4. If approved, added to this file with write access

## Emertis Status

Maintainers unresponsive for 3+ months may be moved to emeritus status at
the discretion of active Core Maintainers.
