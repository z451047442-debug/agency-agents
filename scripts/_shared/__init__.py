from .discovery import EXCLUDE_DIRS, REPO, discover_agents
from .frontmatter import get_body, get_field, get_frontmatter_text, get_list_field
from .terminal import BOLD, CYAN, GREEN, MAGENTA, RED, RESET, YELLOW, supports_color


def load_module(name, filepath):
    """Load a Python module from a file path (handles hyphenated filenames)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(filepath))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


__all__ = [
    "BOLD", "CYAN", "GREEN", "MAGENTA", "RED", "RESET", "YELLOW",
    "supports_color",
    "get_body", "get_field", "get_frontmatter_text", "get_list_field",
    "EXCLUDE_DIRS", "REPO", "discover_agents",
    "load_module",
]
