#!/usr/bin/env python
"""Cross-platform Python implementation for scripts/convert.sh (canonical).

Converts agency agent .md files into tool-specific formats under integrations/.

Usage:
    python scripts/convert.py                      # all tools
    python scripts/convert.py --tool cursor        # single tool
    python scripts/convert.py --check              # verify integrations/ is in sync
    python scripts/convert.py --parallel           # run independent tools in parallel
    python scripts/convert.py --parallel --jobs 4
    python scripts/convert.py --incremental        # skip agents whose output is fresh
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

from _shared import (
    BOLD,
    GREEN,
    RED,
    REPO,
    RESET,
    YELLOW,
    get_body,
    get_field,
    get_frontmatter_text,
    get_list_field,
)
from _shared.discovery import discover_agents

OUT = REPO / "integrations"
ANTIGRAVITY_DATE = "2026-03-08"

def info(msg):    print(f"{GREEN}[OK]{RESET}  {msg}")
def warn(msg):    print(f"{YELLOW}[!!]{RESET}  {msg}")
def error(msg):   print(f"{RED}[ERR]{RESET} {msg}", file=sys.stderr)
def header(msg):  print(f"\n{BOLD}{msg}{RESET}")


# ── helpers ──────────────────────────────────────────────────────────────────

def slugify(name):
    """Convert display name to kebab-case slug."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    return s.strip("-")

def progress_bar(current, total, width=20):
    """Draw a single-line progress bar to stderr (TTY-aware)."""
    if total <= 0:
        return
    filled = width * current // total
    empty = width - filled
    bar = "=" * filled
    if filled < width:
        bar += ">"
        empty -= 1
    bar += " " * max(0, empty)
    end = "\n" if not sys.stderr.isatty() else ""
    sys.stderr.write(f"\r  [{bar}] {current}/{total}{end}")
    sys.stderr.flush()


# ── content validation ───────────────────────────────────────────────────────

_PROMPT_INJECTION_RE = re.compile(
    r"\b(?:ignore|forget|disregard)\s+(?:all|everything)\s+(?:previous|above)\s+instructions?\b|"
    r"\b(?:reveal|output)\s+(?:your\s+)?system\s+(?:prompt|message)\b|"
    r"\bDAN\s*(?:mode|prompt)\b|"
    r"\bdo\s+anything\s+now\b",
    re.IGNORECASE,
)


def validate_agent_content(filepath):
    """Check an agent file for potential prompt injection patterns.

    Returns a list of matched pattern descriptions, or empty list if clean.
    Call this independently to audit agents before conversion.
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    matches = _PROMPT_INJECTION_RE.findall(content)
    return matches


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


def convert_antigravity(name, desc, body, agent_id, out_dir):
    slug = f"agency-{agent_id}"
    _write_frontmatter(out_dir / slug / "SKILL.md", {
        "name": slug,
        "description": desc,
        "risk": "low",
        "source": "community",
        "date_added": f"'{ANTIGRAVITY_DATE}'",
    }, body)


def convert_osaurus(name, desc, body, agent_id, out_dir):
    slug = f"agency-{agent_id}"
    _write_frontmatter(out_dir / slug / "SKILL.md", {
        "name": slug,
        "description": desc,
    }, body)


def _toml_escape(text):
    """Escape a string for a TOML basic string, including all control characters.

    Mirrors the perl-based escaping in the shell version: backslash, double-quote,
    newline, carriage-return, tab, form-feed, backspace, and any other C0 control
    character or DEL are escaped.
    """
    result = []
    for ch in text:
        cp = ord(ch)
        if ch == "\\":
            result.append("\\\\")
        elif ch == '"':
            result.append('\\"')
        elif ch == "\n":
            result.append("\\n")
        elif ch == "\r":
            result.append("\\r")
        elif ch == "\t":
            result.append("\\t")
        elif ch == "\f":
            result.append("\\f")
        elif cp == 0x08:  # backspace
            result.append("\\b")
        elif cp < 0x20 or cp == 0x7F:  # other control chars + DEL
            result.append(f"\\u{cp:04X}")
        else:
            result.append(ch)
    return "".join(result)


def convert_codex(name, desc, body, agent_id, out_dir):
    agents_dir = out_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    escaped_body = _toml_escape(body)
    escaped_name = _toml_escape(name)
    escaped_desc = _toml_escape(desc)
    with open(agents_dir / f"{agent_id}.toml", "w", encoding="utf-8") as f:
        f.write(f'name = "{escaped_name}"\n')
        f.write(f'description = "{escaped_desc}"\n')
        f.write(f'developer_instructions = "{escaped_body}"\n')


def convert_gemini_cli(name, desc, body, agent_id, out_dir):
    _write_frontmatter(out_dir / "agents" / f"{agent_id}.md", {
        "name": agent_id,
        "description": desc,
    }, body)


# ── OpenCode colour resolution ──────────────────────────────────────────────

# Map named CSS colours to #RRGGBB hex for OpenCode agent frontmatter.
# Mirrors resolve_opencode_color() in the original shell convert.sh.
OPENCODE_COLOR_MAP = {
    "cyan":          "#00FFFF",
    "blue":          "#3498DB",
    "green":         "#2ECC71",
    "red":           "#E74C3C",
    "purple":        "#9B59B6",
    "orange":        "#F39C12",
    "teal":          "#008080",
    "indigo":        "#6366F1",
    "pink":          "#E84393",
    "gold":          "#FFD700",
    "amber":         "#F59E0B",
    "neon-green":    "#10B981",
    "neon-cyan":     "#06B6D4",
    "metallic-blue": "#3B82F6",
    "yellow":        "#EAB308",
    "violet":        "#8B5CF6",
    "rose":          "#F43F5E",
    "lime":          "#84CC16",
    "gray":          "#6B7280",
    "fuchsia":       "#D946EF",
}

DEFAULT_OPENCODE_COLOR = "#6B7280"


def resolve_opencode_color(color_name):
    """Resolve a named colour to its #RRGGBB hex value for OpenCode.

    Recognises 20 common CSS colour names.  Already-hex values are normalised
    to uppercase.  Unrecognised names fall back to gray (#6B7280).
    """
    if not color_name:
        return DEFAULT_OPENCODE_COLOR
    c = color_name.strip().lower()
    # Already a hex value like "#a1b2c3" or "a1b2c3"?
    if re.match(r"^#[0-9a-fA-F]{6}$", c):
        return c.upper()
    if re.match(r"^[0-9a-fA-F]{6}$", c):
        return f"#{c.upper()}"
    return OPENCODE_COLOR_MAP.get(c, DEFAULT_OPENCODE_COLOR)


def convert_opencode(name, desc, body, agent_id, out_dir, fm_text=None):
    color_name = get_field("color", fm_text) if fm_text else ""
    color = resolve_opencode_color(color_name)
    agents_dir = out_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    with open(agents_dir / f"{agent_id}.md", "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(f"name: {name}\n")
        f.write(f"description: {desc}\n")
        f.write("mode: subagent\n")
        f.write(f"color: '{color}'\n")
        f.write("---\n")
        f.write(body)


def convert_cursor(name, desc, body, agent_id, out_dir):
    rules_dir = out_dir / "rules"
    _write_frontmatter(rules_dir / f"{agent_id}.mdc", {
        "description": desc,
        "globs": '""',
        "alwaysApply": "false",
    }, body)


def convert_openclaw(name, desc, body, agent_id, out_dir, fm_text):
    """Split body into SOUL.md (persona/rules) and AGENTS.md (mission/workflow)."""
    agent_dir = out_dir / agent_id
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


def convert_qwen(name, desc, body, agent_id, out_dir, fm_text):
    agents_dir = out_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    tools = get_field("tools", fm_text)
    with open(agents_dir / f"{agent_id}.md", "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(f"name: {agent_id}\n")
        f.write(f"description: {desc}\n")
        if tools:
            f.write(f"tools: {tools}\n")
        f.write("---\n")
        f.write(body)


def convert_kimi(name, desc, body, agent_id, out_dir):
    agent_dir = out_dir / agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    with open(agent_dir / "agent.yaml", "w", encoding="utf-8") as f:
        f.write("version: 1\n")
        f.write("agent:\n")
        f.write(f"  name: {agent_id}\n")
        f.write("  extend: default\n")
        f.write("  system_prompt_path: ./system.md\n")
    with open(agent_dir / "system.md", "w", encoding="utf-8") as f:
        f.write(f"# {name}\n\n{desc}\n\n{body}\n")


def run_hermes(out_dir):
    """Delegate to build-hermes-plugin.py (existing Python script)."""
    script = REPO / "scripts" / "build-hermes-plugin.py"
    try:
        subprocess.run([sys.executable, str(script), "--repo-root", str(REPO),
                        "--out", str(out_dir / "hermes")], check=True)
    except subprocess.CalledProcessError as e:
        print(f"WARNING: Hermes plugin build failed (exit {e.returncode}), skipping",
              file=sys.stderr)
    except FileNotFoundError:
        print("WARNING: build-hermes-plugin.py not found, skipping Hermes",
              file=sys.stderr)


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


# ── depends_on manifest ─────────────────────────────────────────────────────

def build_depends_manifest(agents, out_dir):
    """Extract depends_on from all agent frontmatter and write depends_on.json.

    Handles both YAML list format and single-line comma-separated format.
    Mirrors build_depends_manifest() + extract_depends_on() from convert.sh.
    """
    manifest = {}
    for _category, filepath, fm_text, _body in agents:
        deps = get_list_field("depends_on", fm_text)
        if not deps:
            # Also check raw field value for inline single-line format that
            # get_list_field might have missed (e.g. depends_on: id1, id2).
            raw = get_field("depends_on", fm_text)
            if raw:
                deps = [d.strip().strip('"').strip("'")
                        for d in raw.split(",") if d.strip()]
        if deps:
            agent_id = filepath.stem
            manifest[agent_id] = deps

    if manifest:
        dest = out_dir / "depends_on.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")
        info(f"Depends-on manifest: {dest} ({len(manifest)} agents with dependencies)")
    else:
        info("No agent dependencies found")


# ── OMC converter (plugin-type: generates skills, routing, hooks) ─────────────

_OMC_OUT = REPO / "integrations" / "oh-my-claudecode"


def convert_oh_my_claudecode(name, description, body, out_dir, fm_text=None):
    """Delegate to dedicated OMC generator scripts.

    Each script reads AGENTS.json independently to produce its artifact:
      - generate-nexus-skills.py  → skills/nexus-*/SKILL.md
      - generate-omc-model-routing.py → model-routing.json
      - generate-omc-hooks.py → hooks.json
    """
    import subprocess

    scripts = [
        ("generate-nexus-skills.py", []),
        ("generate-omc-model-routing.py", []),
        ("generate-omc-hooks.py", []),
        ("generate-omc-team-config.py", []),
    ]
    for script, extra_args in scripts:
        script_path = REPO / "scripts" / script
        if not script_path.exists():
            warn(f"OMC: {script} not found, skipping")
            continue
        result = subprocess.run(
            [sys.executable, str(script_path)] + extra_args,
            capture_output=True, text=True, cwd=str(REPO),
        )
        if result.returncode != 0:
            warn(f"OMC: {script} failed: {result.stderr.strip()}")


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
    "oh-my-claudecode": convert_oh_my_claudecode,
}

# Complete set of convertible tools (excludes install-only tools like
# claude-code / copilot that read agent source .md files directly).
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
    """Convert all agents for a single tool. Returns agent count."""
    clean_tool_output(tool, out_dir)
    if tool == "hermes":
        run_hermes(out_dir)
        return len(agents)

    if tool == "oh-my-claudecode":
        convert_oh_my_claudecode("", "", "", out_dir)
        return len(agents)

    if tool in ("aider", "windsurf"):
        buf = [(get_field("name", fm), get_field("description", fm), body)
               for _, _, fm, body in agents
               if get_field("name", fm) and get_field("description", fm)]
        build_aider_windsurf(buf, out_dir, tool)
        return len(buf)

    count = 0
    for _category, file_path, fm_text, body in agents:
        name = get_field("name", fm_text)
        desc = get_field("description", fm_text)
        if not name or not desc:
            continue
        agent_id = file_path.stem

        d = out_dir / tool
        if tool in ("openclaw", "qwen", "opencode"):
            CONVERTERS[tool](name, desc, body, agent_id, d, fm_text)
        else:
            CONVERTERS[tool](name, desc, body, agent_id, d)
        count += 1

    return count


# ── incremental mode ─────────────────────────────────────────────────────────

# Primary output file per tool, used for mtime-based freshness checks.
# d is the tool's output dir (out_dir / tool).
_PRIMARY_OUTPUT = {
    "antigravity": lambda agent_id, d: d / f"agency-{agent_id}" / "SKILL.md",
    "osaurus":     lambda agent_id, d: d / f"agency-{agent_id}" / "SKILL.md",
    "gemini-cli":  lambda agent_id, d: d / "agents" / f"{agent_id}.md",
    "opencode":    lambda agent_id, d: d / "agents" / f"{agent_id}.md",
    "cursor":      lambda agent_id, d: d / "rules" / f"{agent_id}.mdc",
    "openclaw":    lambda agent_id, d: d / agent_id / "SOUL.md",
    "qwen":        lambda agent_id, d: d / "agents" / f"{agent_id}.md",
    "kimi":        lambda agent_id, d: d / agent_id / "agent.yaml",
    "codex":       lambda agent_id, d: d / "agents" / f"{agent_id}.toml",
}


def _agent_fresh(file_path, agent_id, tool, out_dir):
    """True if the agent's primary output is strictly newer than its source."""
    primary = _PRIMARY_OUTPUT[tool](agent_id, out_dir / tool)
    if not primary.exists():
        return False
    return primary.stat().st_mtime > file_path.stat().st_mtime


# Generator scripts whose code changes should also trigger an aggregate rebuild.
_AGGREGATE_SCRIPTS = {
    "hermes": ["scripts/build-hermes-plugin.py"],
    "oh-my-claudecode": [
        "scripts/generate-nexus-skills.py",
        "scripts/generate-omc-hooks.py",
        "scripts/generate-omc-model-routing.py",
        "scripts/generate-omc-team-config.py",
    ],
}


def _aggregate_fresh(agents, tool, out_dir):
    """True if every aggregate output for tool is newer than every source.

    hermes and oh-my-claudecode each produce whole-roster artifacts (one
    plugin / a few JSONs), so freshness is all-or-nothing. A missing output
    counts as stale, which also self-heals partial generator failures.
    """
    mtimes = [fp.stat().st_mtime for _, fp, _, _ in agents]
    index = REPO / "AGENTS.json"
    if index.exists():
        mtimes.append(index.stat().st_mtime)
    for rel in _AGGREGATE_SCRIPTS[tool]:
        p = REPO / rel
        if p.exists():
            mtimes.append(p.stat().st_mtime)
    newest_source = max(mtimes, default=0)

    if tool == "hermes":
        outputs = [out_dir / "hermes" / "agency-agents-router" / "data" / "agents.json"]
    else:
        outputs = [
            _OMC_OUT / "hooks.json",
            _OMC_OUT / "team-config.json",
            _OMC_OUT / "model-routing.json",
        ]
        outputs.extend(_OMC_OUT.glob("skills/nexus-*/SKILL.md"))
    return all(p.exists() and p.stat().st_mtime > newest_source for p in outputs)


def run_tool_incremental(tool, agents, out_dir):
    """Convert only agents whose source is newer than their existing output.

    Skips clean_tool_output(), so output for deleted agents is left behind —
    run a full (non-incremental) conversion periodically to clean up.
    Returns (written_count, skipped_count).
    """
    if tool in ("hermes", "oh-my-claudecode"):
        if _aggregate_fresh(agents, tool, out_dir):
            return 0, len(agents)
        if tool == "hermes":
            run_hermes(out_dir)
        else:
            convert_oh_my_claudecode("", "", "", out_dir)
        return len(agents), 0

    if tool in ("aider", "windsurf"):
        # Single accumulated file — rebuild only if some source is newer.
        buf = [(get_field("name", fm), get_field("description", fm), body)
               for _, _, fm, body in agents
               if get_field("name", fm) and get_field("description", fm)]
        dest = (out_dir / "aider" / "CONVENTIONS.md") if tool == "aider" \
            else (out_dir / "windsurf" / ".windsurfrules")
        if dest.exists():
            newest_source = max((fp.stat().st_mtime for _, fp, _, _ in agents), default=0)
            if dest.stat().st_mtime > newest_source:
                return 0, len(buf)
        build_aider_windsurf(buf, out_dir, tool)
        return len(buf), 0

    written = skipped = 0
    for _category, file_path, fm_text, body in agents:
        name = get_field("name", fm_text)
        desc = get_field("description", fm_text)
        if not name or not desc:
            continue
        agent_id = file_path.stem
        if _agent_fresh(file_path, agent_id, tool, out_dir):
            skipped += 1
            continue
        d = out_dir / tool
        if tool in ("openclaw", "qwen", "opencode"):
            CONVERTERS[tool](name, desc, body, agent_id, d, fm_text)
        else:
            CONVERTERS[tool](name, desc, body, agent_id, d)
        written += 1
    return written, skipped


def main():
    parser = argparse.ArgumentParser(
        description="Convert agency agents to tool-specific formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Tools:
  antigravity  — Antigravity skill files (~/.gemini/antigravity/skills/)
  gemini-cli   — Gemini CLI subagent files (~/.gemini/agents/*.md)
  opencode     — OpenCode agent files (.opencode/agents/*.md)
  cursor       — Cursor rule files (.cursor/rules/*.mdc)
  aider        — Single CONVENTIONS.md for Aider
  windsurf     — Single .windsurfrules for Windsurf
  openclaw     — OpenClaw workspaces (SOUL.md + AGENTS.md + IDENTITY.md)
  qwen         — Qwen Code SubAgent files (~/.qwen/agents/*.md)
  kimi         — Kimi Code CLI agent files (~/.config/kimi/agents/)
  codex        — Codex custom agent TOML files (~/.codex/agents/*.toml)
  osaurus      — Osaurus skill files (~/.osaurus/skills/<name>/SKILL.md)
  hermes       — Hermes lazy-router plugin (one plugin + on-disk agent index)
  all          — All tools (default)""",
    )
    parser.add_argument("--tool", default="all",
                        help="Tool to convert (default: all)")
    parser.add_argument("--out", default=str(OUT),
                        help="Output directory")
    parser.add_argument("--check", action="store_true",
                        help="Verify integrations/ is in sync")
    parser.add_argument("--parallel", action="store_true",
                        help="Run independent tools in parallel (--tool all only)")
    parser.add_argument("--jobs", type=int, default=None,
                        help="Max parallel jobs (default: CPU count)")
    parser.add_argument("--incremental", action="store_true",
                        help="Skip agents whose converted output is newer than their "
                             "source. Faster for repeated local runs; stale output for "
                             "deleted agents is not cleaned (run without --incremental "
                             "periodically). Ignored in --check mode.")
    args = parser.parse_args()

    if args.tool not in ALL_TOOLS + ["all"]:
        error(f"Unknown tool: {args.tool}. Valid: {ALL_TOOLS + ['all']}")
        sys.exit(1)

    out_dir = Path(args.out)

    # Collect all agents once (uses shared discover_agents, reads + validates)
    raw = list(discover_agents())
    agents = []
    for category, _rel, file_path in raw:
        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if not content.startswith("---"):
            continue
        fm_text = get_frontmatter_text(content)
        name = get_field("name", fm_text)
        if not name:
            continue
        body = get_body(content).lstrip("\n")
        agents.append((category, file_path, fm_text, body))

    # --check mode: regenerate to a temp dir and compare
    if args.check:
        import filecmp
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        try:
            tools_to_run = ALL_TOOLS if args.tool == "all" else [args.tool]
            for tool in tools_to_run:
                run_tool(tool, agents, tmp)

            # Build depends_on manifest (also done in normal mode)
            build_depends_manifest(agents, tmp)

            # Files/dirs not generated by convert.py — skip in comparison
            _CONVERT_EXTERNAL = frozenset({
                "claude-code", "github-copilot", "mcp-memory",
                "by-category", "oh-my-claudecode",
            })

            # Compare tmp vs real integrations/ — full recursive diff.
            # dircmp is shallow, and walking only the tmp side misses nested
            # additions/removals, so snapshot both trees completely.
            def _tree_files(root):
                files = set()
                for base, _dirs, names in os.walk(str(root)):
                    rel_base = os.path.relpath(base, str(root))
                    for f in names:
                        rel = os.path.normpath(os.path.join(rel_base, f))
                        files.add(rel)
                return files

            tmp_files = _tree_files(tmp)
            real_files = _tree_files(out_dir)

            diffs = []
            for rel in sorted(tmp_files | real_files):
                a = os.path.join(str(tmp), rel)
                b = os.path.join(str(out_dir), rel)
                if rel in tmp_files and rel in real_files:
                    if not filecmp.cmp(a, b, shallow=False):
                        diffs.append(rel)
                elif rel in tmp_files:
                    diffs.append(rel)  # generated but missing in integrations/
                else:
                    diffs.append(rel)  # extra file in integrations/
            # Exclude files/dirs not managed by convert.py. README.md and
            # depends_on.json are excluded by basename — each tool dir has
            # its own committed README that convert never generates.
            diffs = [d for d in diffs if d.split(os.sep)[0] not in _CONVERT_EXTERNAL
                     and os.path.basename(d) != "README.md"
                     and os.path.basename(d) != "depends_on.json"]
            if diffs:
                error(f"integrations/ is stale ({len(diffs)} files differ).")
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
    n_tools = len(tools_to_run)

    header("The Agency — Converting agents to tool-specific formats")
    print(f"  Repo:   {REPO}")
    print(f"  Output: {out_dir}")
    print(f"  Tool:   {args.tool}")
    print(f"  Date:   {date.today().isoformat()}")
    if args.parallel and args.tool == "all":
        jobs = args.jobs or os.cpu_count() or 4
        info(f"Parallel mode: up to {jobs} concurrent tool conversions")
    print()

    total = 0

    if args.parallel and args.tool == "all":
        # Run all tools concurrently via thread pool.  Converters are
        # independent (each writes to a separate subdirectory of out_dir)
        # and the pre-loaded agents list is read-only, so this is safe.
        import threading
        jobs = args.jobs or os.cpu_count() or 4
        results = {}        # tool -> count
        results_lock = threading.Lock()
        completed = [0]     # mutable counter for the closure

        def _run_one(tool):
            if args.incremental:
                written, _skipped = run_tool_incremental(tool, agents, out_dir)
                return tool, written
            return tool, run_tool(tool, agents, out_dir)

        with ThreadPoolExecutor(max_workers=jobs) as pool:
            future_map = {pool.submit(_run_one, t): t for t in tools_to_run}
            for future in as_completed(future_map):
                tool, count = future.result()
                with results_lock:
                    results[tool] = count
                    completed[0] += 1
                # Print completion as it happens so the user sees activity
                print(f"  [{completed[0]}/{n_tools}] {tool}: {count} agents")

        # Print ordered summary
        print()
        for i, tool in enumerate(tools_to_run, 1):
            count = results.get(tool, 0)
            total += count
            header(f"Converting: {tool} ({i}/{n_tools})")
            info(f"Converted {count} agents for {tool}")
    else:
        # Sequential mode with progress bar
        for i, tool in enumerate(tools_to_run, 1):
            progress_bar(i, n_tools)
            print()
            header(f"Converting: {tool} ({i}/{n_tools})")
            if args.incremental:
                written, skipped = run_tool_incremental(tool, agents, out_dir)
                count = written
                info(f"Converted {written} agents for {tool} ({skipped} fresh, skipped)")
            else:
                count = run_tool(tool, agents, out_dir)
                info(f"Converted {count} agents for {tool}")
            total += count

    # Build depends_on manifest for install-time dependency warnings
    header("Building dependency manifest")
    build_depends_manifest(agents, out_dir)

    print()
    if args.parallel and args.tool == "all":
        info(f"Done. {n_tools} tools (parallel; total agent conversions: {total}).")
    else:
        info(f"Done. Total conversions: {total}")
    print(f"Output: {out_dir}")


if __name__ == "__main__":
    main()
