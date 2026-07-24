from .discovery import EXCLUDE_DIRS, REPO, discover_agents
from .frontmatter import get_body, get_field, get_frontmatter_text, get_list_field
from .terminal import BOLD, CYAN, GREEN, MAGENTA, RED, RESET, YELLOW, supports_color
from .validators import (
    CORE_SECTIONS,
    CRITICAL_RISK_CATEGORIES,
    HIGH_RISK_CATEGORIES,
    count_domain_signals,
    count_substantive_sections,
    find_broken_links,
    git_last_modified,
    section_body_words,
)


def load_module(name, filepath):
    """Load a Python module from a file path (handles hyphenated filenames).

    Deprecated: prefer importing specific functions from _shared. Use the
    centralized get_score_agent() or get_lint_file() lazy loaders instead.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, str(filepath))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _get_script_function(script_name, func_name):
    """Centralized lazy loader for cross-script function access."""
    import importlib.util
    from pathlib import Path

    _scripts = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        script_name, str(_scripts / f"{script_name}.py")
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {_scripts / f'{script_name}.py'}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, func_name)


def get_score_agent():
    """Return the score_agent function (centralized, replaces load_module)."""
    return _get_script_function("score-agents", "score_agent")


def get_lint_file():
    """Return the lint_file function (centralized, replaces load_module)."""
    return _get_script_function("lint-agents", "lint_file")


__all__ = [
    "BOLD", "CYAN", "GREEN", "MAGENTA", "RED", "RESET", "YELLOW",
    "supports_color",
    "get_body", "get_field", "get_frontmatter_text", "get_list_field",
    "EXCLUDE_DIRS", "REPO", "discover_agents",
    "CORE_SECTIONS", "CRITICAL_RISK_CATEGORIES", "HIGH_RISK_CATEGORIES",
    "count_domain_signals", "count_substantive_sections",
    "find_broken_links", "git_last_modified", "section_body_words",
    "load_module", "get_score_agent", "get_lint_file",
]
