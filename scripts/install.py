#!/usr/bin/env python3
"""Cross-platform Python installer for The Agency agents.

Reads AGENTS.json and installs agent .md files into AI coding tools.
No bash dependency — works on Windows, macOS, and Linux.

Usage:
    python scripts/install.py --tool claude-code           # all agents
    python scripts/install.py --tool claude-code --division engineering
    python scripts/install.py --list-installed --tool claude-code
    python scripts/install.py --verify --tool claude-code
    python scripts/install.py --uninstall --tool claude-code
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, cast

from _shared import REPO

INDEX_PATH = REPO / "AGENTS.json"
TOOLS_PATH = REPO / "tools.json"


def load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    return s.strip("-")


def get_tool_cfg(tool: str) -> dict[str, Any]:
    tools = load_json(TOOLS_PATH).get("tools", {})
    if tool not in tools:
        print(f"Unknown tool: {tool}. Available: {', '.join(sorted(tools))}", file=sys.stderr)
        sys.exit(1)
    return cast(dict[str, Any], tools[tool])


def resolve_dest(tool: str, scope: str) -> list[tuple[Path, str]]:
    """Return list of (base_dir, filename_template)."""
    cfg = get_tool_cfg(tool)
    home = Path.home()
    results = []
    TEMPLATES = [
        "/{slug}.md", "/{slug}.toml", "/{slug}.yaml",
        "/{slug}/SKILL.md", "/{slug}/SOUL.md", "/{slug}/agent.yaml",
    ]
    for tmpl in cfg.get("dest", {}).get(scope, []):
        matched = False
        for pattern in TEMPLATES:
            if tmpl.endswith(pattern):
                base = tmpl[:-len(pattern)]
                resolved = home / base if scope == "user" else Path.cwd() / base
                results.append((resolved, pattern.lstrip("/")))
                matched = True
                break
        if not matched:
            base = tmpl.rsplit("/", 1)[0] if "/" in tmpl else ""
            fname = tmpl.rsplit("/", 1)[-1] if "/" in tmpl else tmpl
            resolved = home / base if scope == "user" else Path.cwd() / base
            results.append((resolved, fname))
    return results


def install_agent(agent: dict, tool_cfg: dict, dest_dirs: list[tuple[Path, str]]) -> int:
    """Copy one agent to all destinations. Returns count of successful copies."""
    source = REPO / agent["path"]
    if not source.exists():
        return 0

    fmt = tool_cfg.get("format", "identity")
    slug_from = tool_cfg.get("slugFrom", "source")
    slug = agent["id"] if slug_from == "source" else slugify(agent["name"])

    count = 0
    for dest_dir, name_tmpl in dest_dirs:
        dest = dest_dir / name_tmpl.replace("{slug}", slug)

        if fmt == "identity":
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            count += 1
        else:
            # Non-identity: look for converted file in integrations/
            integ = REPO / "integrations" / tool_cfg["kebab"]
            if not integ.exists():
                print(f"  Run convert first: python scripts/convert.py --tool {tool_cfg['kebab']}",
                      file=sys.stderr)
                return 0
            # Prefer the exact source path implied by the dest template
            # (e.g. "{slug}/agent.yaml" -> integrations/kimi/{id}/agent.yaml),
            # which also copies the right file for multi-file formats.
            rel_tmpl = name_tmpl.replace("{slug}", slug)
            src = integ / rel_tmpl
            if not src.exists():
                src = None
                # Fallback: exact id match — stem for single-file formats,
                # parent dir for multi-file formats. Never substring-match,
                # which could pick up a different agent's file.
                for candidate in integ.rglob("*"):
                    if not candidate.is_file():
                        continue
                    if agent["id"] == candidate.stem or agent["id"] == candidate.parent.name:
                        src = candidate
                        break
            if src is not None:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                count += 1
    return count


def install_tool(tool: str, divisions: set[str] | None,
                 agent_id: str | None, scope: str = "user") -> int:
    cfg = get_tool_cfg(tool)

    if cfg.get("installKind") == "plugin":
        print(f"{tool}: plugin type, use convert.py")
        return 0

    # Resolve destinations for each scope that is enabled in tools.json
    scopes_to_use = ["user", "project"] if scope == "both" else [scope]
    all_dest_dirs = []
    for s in scopes_to_use:
        if cfg.get("scope", {}).get(s):
            all_dest_dirs.extend(resolve_dest(tool, s))

    if not all_dest_dirs:
        print(f"{tool}: no destinations for scope={scope}", file=sys.stderr)
        return 0

    agents = load_json(INDEX_PATH).get("agents", [])
    installed = 0

    for agent in agents:
        if divisions and agent["category"] not in divisions:
            continue
        if agent_id and agent["id"] != agent_id:
            continue
        installed += install_agent(agent, cfg, all_dest_dirs)

    cwd = str(Path.cwd())
    print(f"{tool}: {installed} agents -> {str(all_dest_dirs[0][0]).replace(cwd, '.')}")
    return installed


def list_installed(tool: str) -> None:
    dest_dirs = resolve_dest(tool, "user")
    for dest_dir, _ in dest_dirs:
        if not dest_dir.exists():
            print(f"{tool}: not installed")
            continue
        # Count files (single-file formats) and dirs (multi-file formats
        # like kimi/openclaw install one directory per agent).
        entries = sorted(dest_dir.iterdir())
        print(f"{tool}: {len(entries)} agents at ~/{dest_dir.relative_to(Path.home())}")


def verify_install(tool: str) -> bool:
    dest_dirs = resolve_dest(tool, "user")
    if not dest_dirs or not dest_dirs[0][0].exists():
        print(f"FAIL: {tool} not installed")
        return False

    agents = load_json(INDEX_PATH).get("agents", [])
    dest_dir = dest_dirs[0][0]
    installed = {p.stem for p in dest_dir.iterdir()}
    expected = {a["id"] for a in agents}
    missing = expected - installed
    extra = installed - expected

    ok = True
    if missing:
        print(f"  Missing: {len(missing)} agents")
        ok = False
    if extra:
        print(f"  Extra:   {len(extra)} unrecognized")
        ok = False
    if ok:
        print(f"OK: {len(installed)} agents verified for {tool}")
    return ok


def uninstall_tool(tool: str, agent_id: str | None) -> int:
    dest_dirs = resolve_dest(tool, "user")
    count = 0
    for dest_dir, _ in dest_dirs:
        if not dest_dir.exists():
            continue
        if agent_id:
            for p in dest_dir.iterdir():
                if p.stem == agent_id:
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
                    count += 1
                    print(f"  removed: {agent_id}")
        else:
            for f in dest_dir.glob("*.md"):
                f.unlink()
                count += 1
    print(f"{tool}: {count} agents removed")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Install The Agency agents")
    parser.add_argument("--tool", default="claude-code", help="Target tool")
    parser.add_argument("--division", help="Comma-separated division filter")
    parser.add_argument("--agent", help="Single agent ID")
    parser.add_argument("--scope", default="user", choices=["user", "project", "both"],
                        help="Install scope: user, project, or both (default: user)")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--list-installed", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.list_installed:
        list_installed(args.tool)
        return
    if args.verify:
        ok = verify_install(args.tool)
        sys.exit(0 if ok else 1)
    if args.uninstall:
        uninstall_tool(args.tool, args.agent)
        return

    divisions = {d.strip() for d in args.division.split(",")} if args.division else None
    n = install_tool(args.tool, divisions, args.agent, scope=args.scope)
    print(f"Done. {n} agents installed.")


if __name__ == "__main__":
    main()
