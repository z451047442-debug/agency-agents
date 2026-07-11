# Agent Versioning Strategy

## Version format

Agent versions follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

| Bump | When | Example |
|------|------|---------|
| **MAJOR** (2.0.0) | Role/purpose fundamentally changes | Agent renamed or split into two |
| **MINOR** (1.1.0) | New sections, skills, or deliverables added | New workflow, nexus_roles changed |
| **PATCH** (1.0.1) | Typo fixes, description polish, metadata updates | Fixed broken link, updated emoji |

## When to bump

- **Content changes** (>20% body text changed) → MINOR
- **Frontmatter changes** (nexus_roles, depends_on, lifecycle) → MINOR
- **Structural changes** (new/deleted required sections) → MINOR
- **Cosmetic fixes** (typos, formatting) → PATCH
- **Role redefinition** → MAJOR

## How to bump

```bash
python scripts/batch-version.py --dry-run       # preview
python scripts/batch-version.py                  # bump all
python scripts/batch-version.py --category engineering
```

## Tracking

- Every agent carries a `version` field in YAML frontmatter
- `date_added` records when the agent first entered the repo
- `scripts/agent-lifecycle.py` tracks draft → review → published → deprecated
- CI validates version field presence via `lint-agents.py`
