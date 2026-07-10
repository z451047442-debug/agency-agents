"""Agent file discovery utilities."""

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

EXCLUDE_DIRS = frozenset({
    ".git", ".github", ".vs", ".vscode", ".claude",
    ".pytest_cache", "examples", "integrations",
    "scripts", "docs", "schemas", "tests",
    "__pycache__", "env", "node_modules",
})


def discover_agents(category_filter: str | None = None):
    """Yield (category, rel_path, file_path) for every agent .md file."""
    for entry in sorted(REPO.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if entry.name in EXCLUDE_DIRS:
            continue
        if category_filter and entry.name != category_filter:
            continue
        for md in sorted(entry.rglob("*.md")):
            try:
                rel = str(md.relative_to(REPO)).replace("\\", "/")
            except ValueError:
                rel = md.name
            yield entry.name, rel, md
