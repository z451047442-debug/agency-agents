## Summary

<!-- Brief description of the changes -->

## Type

- [ ] New agent(s)
- [ ] Agent content update
- [ ] Tooling / script change
- [ ] CI / infrastructure
- [ ] Bug fix
- [ ] Documentation

## Checklist

- [ ] Ran `python scripts/lint-agents.py --all --no-freshness` (for agent changes)
- [ ] Ran `python scripts/validate-index.py` (for agent add/move/delete)
- [ ] Ran `python -m pytest tests/` and all pass
- [ ] Ran `python -m ruff check scripts/` (for Python changes)
- [ ] Updated CHANGELOG.md if applicable
