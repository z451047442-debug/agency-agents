#!/usr/bin/env python
"""Cross-platform Python replacement for scripts/convert.sh.

Converts agency agent .md files into tool-specific formats under integrations/.

Usage:
    python scripts/convert.py                    # all tools
    python scripts/convert.py --tool cursor      # single tool
    python scripts/convert.py --check            # verify integrations/ is in sync
"""

import argparse, json, os, re, shutil, subprocess, sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "integrations"
EXCLUDE_DIRS = {".git", ".github", ".vs", "examples", "integrations",
                "scripts", "docs", "schemas", "__pycache__"}
ANTIGRAVITY_DATE = "2026-03-08"

# ── helpers ──────────────────────────────────────────────────────────────────

def get_field(field, text):
    """Extract a YAML frontmatter field value (multi-line safe)."""
    m = re.search(rf'^{re.escape(field)}:\s*(.*?)$', text, re.MULTILINE)
    return m.group(1).strip() if m else ""

def get_frontmatter_text(content):
    """Return just the frontmatter block (between first two --- fences)."""
    parts = content.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""

def get_body(content):
    """Strip YAML frontmatter, return body text."""
    parts = content.split("---", 2)
    return parts[2] if len(parts) >= 3 else content

def slugify(name):
    """Convert display name to kebab-case slug."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    return s.strip("-")


# ── agent discovery ──────────────────────────────────────────────────────────

def discover_agents():
    """Yield (category, file_path, frontmatter_text, body_text) for every agent."""
    for entry in sorted(REPO.iterdir()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name.startswith("_"):
            continue
        if entry.name in EXCLUDE_DIRS:
            continue
        for md in sorted(entry.rglob("*.md")):
            content = md.read_text(encoding="utf-8")
            if not content.startswith("---"):
                continue
            fm_text = get_frontmatter_text(content)
            name = get_field("name", fm_text)
            if not name:
                continue
            body = get_body(content).lstrip("\n")
            yield entry.name, md, fm_text, body


# ── tool converters ──────────────────────────────────────────────────────────

def _write_frontmatter(path, fields, body):
    """Write a markdown file with YAML frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        for k, v in fields.items():
            f.write(f"{k}: {v}\n")
        f.write("---\n")
        if body:
            f.write(body)
            if not body.endswith("\n"):
                f.write("\n")


def convert_antigravity(name, desc, body, out_dir):
    slug = f"agency-{slugify(name)}"
    _write_frontmatter(out_dir / slug / "SKILL.md", {
        "name": slug,
        "description": desc,
        "risk": "low",
        "source": "community",
        "date_added": f"'{ANTIGRAVITY_DATE}'",
    }, body)


def convert_osaurus(name, desc, body, out_dir):
    slug = f"agency-{slugify(name)}"
    _write_frontmatter(out_dir / slug / "SKILL.md", {
        "name": slug,
        "description": desc,
    }, body)


def convert_codex(name, desc, body, out_dir):
    slug = slugify(name)
    agents_dir = out_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    # TOML basic string escape
    escaped_body = body.replace("\\", "\\\\").replace('"', '\\"')
    escaped_body = escaped_body.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    with open(agents_dir / f"{slug}.toml", "w", encoding="utf-8") as f:
        f.write(f'name = "{name}"\n')
        f.write(f'description = "{desc}"\n')
        f.write(f'developer_instructions = "{escaped_body}"\n')


def convert_gemini_cli(name, desc, body, out_dir):
    _write_frontmatter(out_dir / "agents" / f"{slugify(name)}.md", {
        "name": slugify(name),
        "description": desc,
    }, body)


def convert_opencode(name, desc, body, out_dir):
    agents_dir = out_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    with open(agents_dir / f"{slugify(name)}.md", "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(f"name: {name}\n")
        f.write(f"description: {desc}\n")
        f.write("mode: subagent\n")
        f.write("color: '#6B7280'\n")
        f.write("---\n")
        f.write(body)


def convert_cursor(name, desc, body, out_dir):
    rules_dir = out_dir / "rules"
    _write_frontmatter(rules_dir / f"{slugify(name)}.mdc", {
        "description": desc,
        "globs": '""',
        "alwaysApply": "false",
    }, body)


def convert_openclaw(name, desc, body, out_dir, fm_text):
    """Split body into SOUL.md (persona/rules) and AGENTS.md (mission/workflow)."""
    slug = slugify(name)
    agent_dir = out_dir / slug
    agent_dir.mkdir(parents=True, exist_ok=True)

    soul_keywords = ["identity", "learning", "memory", "communication",
                     "style", "critical rule", "rules you must follow"]
    soul_lines, agents_lines = [], []
    current_target = "agents"
    current_section = []

    for line in body.split("\n"):
        if re.match(r"^##\s", line):
            if current_section:
                target = soul_lines if current_target == "soul" else agents_lines
                target.extend(current_section)
            current_section = []
            header_lower = line.lower()
            current_target = "soul" if any(
                kw in header_lower for kw in soul_keywords) else "agents"
        current_section.append(line)

    if current_section:
        target = soul_lines if current_target == "soul" else agents_lines
        target.extend(current_section)

    (agent_dir / "SOUL.md").write_text("\n".join(soul_lines) + "\n", encoding="utf-8")
    (agent_dir / "AGENTS.md").write_text("\n".join(agents_lines) + "\n", encoding="utf-8")

    emoji = get_field("emoji", fm_text)
    vibe = get_field("vibe", fm_text)
    if emoji and vibe:
        (agent_dir / "IDENTITY.md").write_text(f"# {emoji} {name}\n{vibe}\n", encoding="utf-8")
    else:
        (agent_dir / "IDENTITY.md").write_text(f"# {name}\n{desc}\n", encoding="utf-8")


def convert_qwen(name, desc, body, out_dir, fm_text):
    agents_dir = out_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    tools = get_field("tools", fm_text)
    with open(agents_dir / f"{slugify(name)}.md", "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(f"name: {slugify(name)}\n")
        f.write(f"description: {desc}\n")
        if tools:
            f.write(f"tools: {tools}\n")
        f.write("---\n")
        f.write(body)


def convert_kimi(name, desc, body, out_dir):
    slug = slugify(name)
    agent_dir = out_dir / slug
    agent_dir.mkdir(parents=True, exist_ok=True)
    with open(agent_dir / "agent.yaml", "w", encoding="utf-8") as f:
        f.write("version: 1\n")
        f.write("agent:\n")
        f.write(f"  name: {slug}\n")
        f.write("  extend: default\n")
        f.write("  system_prompt_path: ./system.md\n")
    with open(agent_dir / "system.md", "w", encoding="utf-8") as f:
        f.write(f"# {name}\n\n{desc}\n\n{body}\n")


def run_hermes(out_dir):
    """Delegate to build-hermes-plugin.py (existing Python script)."""
    script = REPO / "scripts" / "build-hermes-plugin.py"
    subprocess.run([sys.executable, str(script), "--repo-root", str(REPO),
                    "--out", str(out_dir / "hermes")], check=True)


# ── single-file accumulators (aider, windsurf) ───────────────────────────────

def build_aider_windsurf(agents, out_dir, tool):
    """Build single accumulated file for aider or windsurf."""
    if tool == "aider":
        dest = out_dir / "aider" / "CONVENTIONS.md"
        header = (
            "# The Agency — AI Agent Conventions\n"
            "#\n"
            "# This file provides Aider with the full roster of specialized AI agents from\n"
            "# The Agency (https://github.com/z451047442-debug/agency-agents).\n"
            "#\n"
            "# To activate an agent, reference it by name in your Aider session prompt, e.g.:\n"
            '#   "Use the Frontend Developer agent to review this component."\n'
            "#\n"
            "# Generated by scripts/convert.py — do not edit manually.\n"
        )
        sep = "\n\n---\n\n"
        agent_fmt = "## {name}\n\n> {desc}\n\n{body}"
    else:
        dest = out_dir / "windsurf" / ".windsurfrules"
        header = (
            "# The Agency — AI Agent Rules for Windsurf\n"
            "#\n"
            "# Full roster of specialized AI agents from The Agency.\n"
            "# To activate an agent, reference it by name in your Windsurf conversation.\n"
            "#\n"
            "# Generated by scripts/convert.py — do not edit manually.\n"
        )
        sep = "\n\n" + "=" * 80 + "\n"
        agent_fmt = "## {name}\n{desc}\n" + "=" * 80 + "\n\n{body}"

    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(header)
        for name, desc, body in agents:
            f.write(sep)
            f.write(agent_fmt.format(name=name, desc=desc, body=body))
        f.write("\n")


# ── main ─────────────────────────────────────────────────────────────────────

CONVERTERS = {
    "antigravity": convert_antigravity,
    "gemini-cli": convert_gemini_cli,
    "opencode":     convert_opencode,
    "cursor":       convert_cursor,
    "openclaw":     convert_openclaw,
    "qwen":         convert_qwen,
    "kimi":         convert_kimi,
    "codex":        convert_codex,
    "osaurus":      convert_osaurus,
}

ALL_TOOLS = list(CONVERTERS.keys()) + ["aider", "windsurf", "hermes"]


def clean_tool_output(tool, out_dir):
    """Remove previous output for a tool, preserving README.md."""
    d = out_dir / tool
    if not d.exists():
        return
    for item in d.iterdir():
        if item.name != "README.md":
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()


def run_tool(tool, agents, out_dir):
    """Convert all agents for a single tool."""
    clean_tool_output(tool, out_dir)
    if tool == "hermes":
        run_hermes(out_dir)
        return len(agents)

    count = 0
    aider_windsurf_buf = []

    for category, filepath, fm_text, body in agents:
        name = get_field("name", fm_text)
        desc = get_field("description", fm_text)
        if not name or not desc:
            continue

        if tool in ("aider", "windsurf"):
            aider_windsurf_buf.append((name, desc, body))
            count += 1
        elif tool in CONVERTERS:
            d = out_dir / tool
            if tool == "openclaw":
                CONVERTERS[tool](name, desc, body, d, fm_text)
            elif tool == "qwen":
                CONVERTERS[tool](name, desc, body, d, fm_text)
            else:
                CONVERTERS[tool](name, desc, body, d)
            count += 1

    if tool == "aider":
        build_aider_windsurf(aider_windsurf_buf, out_dir, "aider")
    elif tool == "windsurf":
        build_aider_windsurf(aider_windsurf_buf, out_dir, "windsurf")

    return count


def main():
    parser = argparse.ArgumentParser(description="Convert agency agents to tool-specific formats")
    parser.add_argument("--tool", default="all", help="Tool to convert (default: all)")
    parser.add_argument("--out", default=str(OUT), help="Output directory")
    parser.add_argument("--check", action="store_true", help="Verify integrations/ is in sync")
    args = parser.parse_args()

    if args.tool not in ALL_TOOLS + ["all"]:
        print(f"Unknown tool: {args.tool}. Valid: {ALL_TOOLS + ['all']}")
        sys.exit(1)

    out_dir = Path(args.out)

    # Collect all agents once
    agents = list(discover_agents())

    if args.check:
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        try:
            tools_to_run = ALL_TOOLS if args.tool == "all" else [args.tool]
            for tool in tools_to_run:
                run_tool(tool, agents, tmp)

            # Compare tmp vs real integrations/
            import filecmp
            result = filecmp.dircmp(str(tmp), str(out_dir))
            diffs = result.diff_files + result.left_only + result.right_only
            for root, dirs, files in os.walk(str(tmp)):
                for f in files:
                    rel = os.path.relpath(os.path.join(root, f), str(tmp))
                    a = os.path.join(str(tmp), rel)
                    b = os.path.join(str(out_dir), rel)
                    if os.path.exists(b) and not filecmp.cmp(a, b, shallow=False):
                        diffs.append(rel)

            diffs = sorted(set(diffs))
            if diffs:
                print(f"ERROR: integrations/ is stale ({len(diffs)} files differ).")
                print("Run: python scripts/convert.py")
                for d in diffs[:20]:
                    print(f"  {d}")
                if len(diffs) > 20:
                    print(f"  ... and {len(diffs) - 20} more")
                sys.exit(1)
            else:
                print(f"OK: integrations/ is up to date ({len(agents)} agents).")
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)
        return

    # Normal conversion
    tools_to_run = ALL_TOOLS if args.tool == "all" else [args.tool]
    total = 0
    print(f"The Agency — Converting agents to tool-specific formats")
    print(f"  Repo:   {REPO}")
    print(f"  Output: {out_dir}")
    print(f"  Tool:   {args.tool}")
    print(f"  Date:   {date.today().isoformat()}")
    print()

    for i, tool in enumerate(tools_to_run, 1):
        print(f"Converting: {tool} ({i}/{len(tools_to_run)})")
        count = run_tool(tool, agents, out_dir)
        total += count
        print(f"  Converted {count} agents for {tool}")

    print(f"\nDone. Total conversions: {total}")
    print(f"Output: {out_dir}")


if __name__ == "__main__":
    main()
