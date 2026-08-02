# Quickstart: 5 minutes to your first AI specialist

## 1. Install (30 seconds)

```bash
./scripts/install.sh --tool claude-code
```

## 2. Find the right specialist (60 seconds)

```bash
python scripts/search-agents.py "mobile app"
python scripts/search-agents.py --scenario "security audit"
python scripts/search-agents.py --categories
```

## 3. Use it (3 minutes)

In Claude Code, type `/agents` to see installed specialists.

**Pattern that works**:
> "Act as the Frontend Developer. I need to build a responsive dashboard. Context: REST API at /api/metrics, real-time charts, must work on mobile."

## 4. Rate it (10 seconds)

```bash
python scripts/feedback.py --agent engineering-frontend-developer --rate 4
```

Your rating helps others find the best specialists.

## What's next?

- `python scripts/search-agents.py --stats` — see what's trending
- `docs/nexus-strategy.md` — combine agents for complex projects
- `python scripts/feedback.py --prompt` — rate agents you've used
