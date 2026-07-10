"""Terminal color support and ANSI constants."""

import os
import sys


def supports_color() -> bool:
    return (
        hasattr(sys.stdout, "isatty")
        and sys.stdout.isatty()
        and not os.environ.get("NO_COLOR")
        and os.environ.get("TERM", "") != "dumb"
    )


if supports_color():
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    BOLD = "\033[1m"
    CYAN = "\033[0;36m"
    MAGENTA = "\033[0;35m"
    RESET = "\033[0m"
else:
    GREEN = YELLOW = RED = BOLD = CYAN = MAGENTA = RESET = ""
