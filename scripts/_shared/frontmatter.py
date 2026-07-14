"""YAML frontmatter parsing utilities for agent .md files."""

import re


def get_frontmatter_text(content: str) -> str:
    parts = content.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""


def get_body(content: str) -> str:
    parts = content.split("---", 2)
    return parts[2] if len(parts) >= 3 else content


def get_field(field: str, fm_text: str) -> str:
    m = re.search(rf"^{re.escape(field)}:\s*(.+)$", fm_text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def get_list_field(field: str, fm_text: str) -> list[str]:
    """Extract YAML list items under a field (e.g., nexus_roles, depends_on).

    Supports both block format:
        nexus_roles:
          - phase-0-discovery
          - phase-1-strategy

    and inline format:
        nexus_roles: [phase-0-discovery, phase-1-strategy]
    """
    # Try inline format first: field: [item1, item2]
    m_inline = re.search(rf"^{re.escape(field)}:\s*\[(.+)\]", fm_text, re.MULTILINE)
    if m_inline:
        return [s.strip().strip('"').strip("'") for s in m_inline.group(1).split(",") if s.strip()]

    # Block format
    items: list[str] = []
    in_block = False
    for line in fm_text.split("\n"):
        if re.match(rf"^{re.escape(field)}:", line):
            in_block = True
            continue
        if in_block:
            m = re.match(r"^\s+-\s+(.+)$", line)
            if m:
                items.append(m.group(1).strip().strip('"').strip("'"))
            elif re.match(r"^\S", line):
                break
    return items
