#!/usr/bin/env python3
"""Expand thin agents (1-3 substantive sections) by generating missing sections.

Thin agents are those with < 4 of 7 substantive sections (Identity, Core Mission,
Critical Rules, Deliverables, Workflow, Success Metrics, Communication). This
script detects which sections are missing and generates template-based content
for each, inserting new sections before the last existing heading.

Usage:
    python scripts/expand-thin-agents.py --dry-run              # preview
    python scripts/expand-thin-agents.py --agent <id>           # single agent
    python scripts/expand-thin-agents.py --category testing     # one category
    python scripts/expand-thin-agents.py --all                  # all thin agents
"""

import argparse
import re
import sys
from pathlib import Path

from _shared import (
    BOLD,
    GREEN,
    RED,
    RESET,
    YELLOW,
    atomic_write,
)
from _shared.discovery import discover_agents
from _shared.frontmatter import get_body, get_field, get_frontmatter_text
from _shared.validators import (
    CORE_SECTIONS,
    count_substantive_sections,
)

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Section templates — one per CORE_SECTIONS key
# Each template uses {name}, {category}, {description} as Python format args.
# Bracketed [text] is literal placeholder for the user to customize.
# ---------------------------------------------------------------------------

SECTION_TEMPLATES = {
    "Identity": (
        "## \U0001f9e0 Your Identity & Memory\n\n"
        "You are an expert {name} with deep experience in {category}. "
        "You have spent years mastering your craft and bring practical "
        "knowledge to every engagement.\n\n"
        "**You think in terms of**:\n"
        "- [Domain-specific principle]\n"
        "- [Proven methodology]\n"
        "- [Industry best practice]\n\n"
        "**You carry forward:**\n"
        "- Lessons learned from past projects\n"
        "- Proven methodologies that deliver results\n"
        "- An ever-growing understanding of what works"
    ),
    "Core Mission": (
        "## \U0001f3af Your Core Mission\n\n"
        "As a {name}, your mission is to {description}. You deliver value through:\n\n"
        "- **[Core competency 1]**: [What this means in practice]\n"
        "- **[Core competency 2]**: [How you apply this skill]\n"
        "- **[Core competency 3]**: [The outcome you drive]\n\n"
        "Your work directly impacts project success and team effectiveness."
    ),
    "Critical Rules": (
        "## \U0001f6a8 Critical Rules You Must Follow\n\n"
        "1. **Stay in your lane.** Provide advice only within your domain of expertise.\n"
        "2. **Be specific and actionable.** Every recommendation must include concrete steps.\n"
        "3. **Know your limits.** When uncertain, acknowledge it and suggest next steps.\n"
        "4. **Ground in standards.** Base recommendations on established methodologies.\n"
        "5. **Think safety-first.** Consider risks before recommending actions."
    ),
    "Deliverables": (
        "## \U0001f4e6 Your Deliverables\n\n"
        "For every engagement, you produce:\n\n"
        "1. **Assessment Report**: Current state analysis with gap identification\n"
        "2. **Strategic Recommendations**: Prioritized, actionable guidance\n"
        "3. **Technical Specifications**: Detailed implementation requirements\n"
        "4. **Risk Evaluation**: Structured threat and mitigation analysis\n"
        "5. **Implementation Support**: Hands-on execution guidance\n\n"
        "Each deliverable follows industry quality standards."
    ),
    "Workflow": (
        "## \U0001f504 Your Workflow\n\n"
        "Your standard process follows these phases:\n\n"
        "1. **Understand**: Review context and gather requirements\n"
        "2. **Analyze**: Apply your domain expertise to evaluate the situation\n"
        "3. **Design**: Create solutions tailored to the specific context\n"
        "4. **Validate**: Self-review against quality criteria\n"
        "5. **Iterate**: Incorporate feedback and refine deliverables"
    ),
    "Success Metrics": (
        "## \U0001f3af Your Success Metrics\n\n"
        "- **Quality**: All deliverables meet or exceed industry standards\n"
        "- **Clarity**: Recommendations are clear, actionable, and well-structured\n"
        "- **Timeliness**: Work is completed within agreed timelines\n"
        "- **Accuracy**: All advice is factually correct and current\n"
        "- **Impact**: Your guidance leads to measurable improvements"
    ),
    "Communication": (
        "## \U0001f4ac Your Communication Style\n\n"
        "- **Clear and direct**: Lead with the conclusion, then provide evidence\n"
        "- **Context-aware**: Adapt depth and terminology to the audience\n"
        "- **Specific**: Use concrete examples over abstract principles\n"
        "- **Honest**: Acknowledge uncertainty and limitations openly\n"
        "- **Structured**: Organize information for quick comprehension"
    ),
}


def _header_pattern(raw_pattern: str) -> str:
    """Wrap a CORE_SECTIONS pattern so it only matches on a ``## `` header line."""
    return r"^##\s+.*?" + raw_pattern


def identify_missing_sections(filepath: Path) -> list[str]:
    """Return list of core section names whose header does not appear in the body.

    Uses regex matching against CORE_SECTIONS patterns restricted to ``## ``
    header lines. Only sections that are entirely absent (no header match at all)
    are returned.
    """
    body = get_body(filepath.read_text(encoding="utf-8"))
    missing = []
    for section_name, raw_pattern in CORE_SECTIONS.items():
        if not re.search(
            _header_pattern(raw_pattern), body, re.IGNORECASE | re.MULTILINE,
        ):
            missing.append(section_name)
    return missing


def generate_section_template(agent_info: dict, section_name: str) -> str:
    """Generate a section template populated with agent context.

    Args:
        agent_info: dict with keys 'name', 'category', 'description'
        section_name: one of the CORE_SECTIONS keys

    Returns:
        Template string with placeholders resolved, or empty string if unknown.
    """
    template_text = SECTION_TEMPLATES.get(section_name, "")
    if not template_text:
        return ""
    return template_text.format(
        name=agent_info.get("name", "expert"),
        category=agent_info.get("category", "your domain"),
        description=agent_info.get("description", "delivering expert results"),
    )


def _strip_header(template_text: str) -> str:
    """Remove the first ``##`` header line from a full section template.

    Returns the body-only content (header stripped), suitable for appending
    into an existing short section.
    """
    lines = template_text.split("\n", 1)
    if len(lines) == 2:
        return lines[1]
    return template_text


def find_insertion_point(body: str) -> int:
    """Find position to insert new sections (before the last ``##`` heading).

    Returns the character index in *body* where new content should be
    inserted. Falls back to the end of body if no ``##`` headings exist.
    """
    matches = list(re.finditer(r"^##\s+\S", body, re.MULTILINE))
    if not matches:
        return len(body)
    return matches[-1].start()


def expand_agent(filepath: Path, dry_run: bool = False) -> list[str]:
    """Expand a thin agent by adding missing sections or expanding short ones.

    Two strategies are used:
      1. **Missing sections** (no header found)  — full template inserted
         before the last ``##`` heading.
      2. **Short sections** (header exists but < 30 words) — template body
         content is appended at the end of the existing section, processed
         bottom-up to keep character positions valid.

    Args:
        filepath: Path to the agent .md file.
        dry_run: If True, only print what would be added; do not write.

    Returns:
        List of section names that were (or would be) modified.
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        print(f"  {RED}Error reading {filepath.name}: {exc}{RESET}")
        return []

    parts = content.split("---", 2)
    if len(parts) < 3:
        print(f"  {RED}No valid frontmatter in {filepath.name}{RESET}")
        return []

    frontmatter = f"---{parts[1]}---"
    body = parts[2]

    fm_text = get_frontmatter_text(content)
    agent_info = {
        "name": get_field("name", fm_text) or filepath.stem,
        "description": get_field("description", fm_text) or "",
        "category": filepath.parent.name,
        "body": body,
    }

    # Collect modifications: (section_name, action, position_or_None, text)
    #   action == "expand"  → append *text* at *position* (section end)
    #   action == "add"     → insert full section (text) before last heading
    modifications: list[tuple[str, str, int | None, str]] = []

    for section_name, raw_pattern in CORE_SECTIONS.items():
        header_pat = re.compile(
            _header_pattern(raw_pattern), re.IGNORECASE | re.MULTILINE,
        )
        m = header_pat.search(body)
        if m:
            # Header exists — find end of the header line and calculate word count
            line_end = body.find("\n", m.start())
            if line_end == -1:
                line_end = len(body)
            start = line_end + 1  # first character of section body
            next_header = re.search(r"^#{1,3}\s", body[start:], re.MULTILINE)
            section_end = start + next_header.start() if next_header else len(body)
            word_count = len(body[start:section_end].split())
            if word_count < 30:
                template = generate_section_template(agent_info, section_name)
                body_only = _strip_header(template)
                if body_only:
                    modifications.append(
                        (section_name, "expand", section_end, "\n\n" + body_only.lstrip("\n") + "\n\n"),
                    )
        else:
            # Header does not exist — add a full new section
            template = generate_section_template(agent_info, section_name)
            if template:
                modifications.append((section_name, "add", None, template))

    if not modifications:
        return []

    if dry_run:
        actions_str = ", ".join(m[0] for m in modifications)
        print(f"  {YELLOW}Would process {filepath.stem}: {actions_str}{RESET}")
        return [m[0] for m in modifications]

    # --- Apply expansions bottom-up (reverse positional order) ----------------
    expansions = [(m[0], m[2], m[3]) for m in modifications if m[1] == "expand"]
    expansions.sort(key=lambda x: -x[1])  # highest position first

    for _section_name, pos, text in expansions:
        body = body[:pos] + text + body[pos:]

    # --- Add new sections before the last heading -----------------------------
    new_sections = [m[3] for m in modifications if m[1] == "add"]
    if new_sections:
        new_content = "\n\n".join(new_sections)
        insertion_point = find_insertion_point(body)
        body = body[:insertion_point] + "\n\n" + new_content + "\n" + body[insertion_point:]

    full_content = frontmatter + body
    atomic_write(filepath, full_content, newline="\n")
    return [m[0] for m in modifications]


def _print_header(text: str) -> None:
    """Print a styled section header."""
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  {text}{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Expand thin agents (1-3 substantive sections) by generating "
            "missing sections from templates."
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview only — no files are modified",
    )
    parser.add_argument(
        "--agent", "-a",
        help="Single agent ID to expand (stem of filename, with or without .md)",
    )
    parser.add_argument(
        "--category", "-c",
        help="Category directory to scan for thin agents",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Scan all categories for thin agents",
    )
    args = parser.parse_args()

    if not any([args.agent, args.category, args.all]):
        parser.print_help()
        sys.exit(1)

    # -- Collect agent files ------------------------------------------------------
    agent_files: list[tuple[str, str, Path]] = []

    if args.agent:
        agent_id = args.agent
        # Strip optional .md extension
        if agent_id.endswith(".md"):
            agent_id = agent_id[:-3]
        # Strip optional category prefix (e.g. "testing/testing-example" -> "testing-example")
        if "/" in agent_id:
            agent_id = agent_id.split("/")[-1]

        found = False
        for cat, rel, fp in discover_agents():
            if fp.stem == agent_id:
                agent_files.append((cat, rel, fp))
                found = True
                break
        if not found:
            print(f"{RED}Agent '{args.agent}' not found.{RESET}")
            sys.exit(1)
    elif args.category:
        agent_files = list(discover_agents(category_filter=args.category))
    else:  # --all
        agent_files = list(discover_agents())

    # -- Filter to thin agents ----------------------------------------------------
    thin_agents: list[tuple[int, str, str, Path]] = []
    for cat, rel, fp in agent_files:
        try:
            body = get_body(fp.read_text(encoding="utf-8"))
            n = count_substantive_sections(body)
            if n < 4:
                thin_agents.append((n, cat, rel, fp))
        except (UnicodeDecodeError, OSError):
            continue

    thin_agents.sort(key=lambda x: (x[0], x[2]))

    if not thin_agents:
        print(f"{GREEN}No thin agents found.{RESET}")
        return

    mode_label = "Dry-run" if args.dry_run else "Expanding"
    _print_header(f"{mode_label}: {len(thin_agents)} thin agents")

    total_added = 0
    for n, cat, rel, fp in thin_agents:
        print(f"  [{n}/7] {rel}")
        added = expand_agent(fp, dry_run=args.dry_run)
        if added:
            total_added += len(added)

    print(
        f"\n{BOLD}Summary: {len(thin_agents)} agents, "
        f"{total_added} section{'s' if total_added != 1 else ''} "
        f"({'would be ' if args.dry_run else ''}added){RESET}"
    )


if __name__ == "__main__":
    main()
