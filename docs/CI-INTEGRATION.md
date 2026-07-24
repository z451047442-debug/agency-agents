# CI Integration & Quality Gates

## Pipeline Overview

Multi-stage quality pipeline on every PR and nightly. All gates must pass before merge.

```
PR opened → [Lint] → [Score] → [Deps] → [Security] → [Regression] → Merge
```

## Quality Gates

### 1. Agent Lint (`lint-agents.yml`)
- **Trigger**: PR with `.md` file changes
- **Check**: YAML validity, required sections, line endings (LF), file size, word count
- **Gate**: **0 errors**

### 2. Quality Scoring (`quality-gate.yml`)
- **Tiered thresholds**:
  - **New agents**: score ≥ 9 (A-grade)
  - **Modified agents**: score ≥ 7 (B-grade), no regression
- **Cross-dependency**: new agents without cross-category `depends_on` → CI warning

### 3. Dependency Validation
- **Check**: All `depends_on` references resolve to existing agent IDs
- **Gate**: **0 broken references**

### 4. Security Scan (Bandit)
- **Check**: Python security lint on `scripts/`
- **Gate**: **0 high/medium** findings

### 5. Score Regression
- **Check**: No agent score decreases vs base branch
- **Gate**: **0 regressions**

### 6. Tests + Coverage
- **Framework**: pytest, target 90%+ coverage
- **Gate**: All tests pass

## Adding a New Agent — PR Checklist

1. Create `<category>/<category>-<name>.md` with valid YAML frontmatter
2. Set `name`, `description`, `emoji`, `color`; include all 7 core sections
3. Add ≥ 2 cross-category `depends_on`
4. `python scripts/lint-agents.py <file>` — must pass
5. `python scripts/score-agents.py --file <file> --threshold 9` — must pass
6. `python scripts/generate-index.py` — update AGENTS.json

## Local Commands

```bash
python scripts/quality.py              # full pipeline
python scripts/lint-agents.py --all     # lint all agents
python scripts/score-agents.py          # score report
python scripts/analyze-deps.py --validate  # dep check
python -m pytest tests/ --cov=scripts   # tests + coverage
```

## Workflow Files

| File | Purpose |
|------|---------|
| `quality-gate.yml` | PR scoring + security + deps |
| `lint-agents.yml` | PR YAML/structure validation |
| `ci.yml` | Test + coverage |
| `nightly-full-audit.yml` | Daily quality report |
| `release.yml` | Versioned releases |
