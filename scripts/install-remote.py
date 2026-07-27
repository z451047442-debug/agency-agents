#!/usr/bin/env python3
"""Remote installer — install agents directly from GitHub without cloning.

Usage:
    curl -sSL https://raw.githubusercontent.com/z451047442-debug/agency-agents/main/scripts/install-remote.py | python - --tool claude-code
    python install-remote.py --tool claude-code --division engineering
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.request import urlopen

DEFAULT_REPO = "z451047442-debug/agency-agents"
DEFAULT_BRANCH = "main"


def log(msg: str) -> None:
    print(f"  {msg}")


def slugify(name: str) -> str:
    import re
    s = name.lower()
    s = re.sub(r"[^a-z0-9]", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    return s.strip("-")


def install_agents(raw_base: str, tool: str, divisions: set[str] | None,
                   agent_filter: str | None) -> int:
    dest = Path.home() / ".claude" / "agents"
    dest.mkdir(parents=True, exist_ok=True)

    # Fetch AGENTS.json
    log(f"Fetching {raw_base}/AGENTS.json")
    with urlopen(f"{raw_base}/AGENTS.json") as resp:
        data = json.loads(resp.read().decode())
    agents = data.get("agents", [])
    log(f"{len(agents)} agents in index")

    # For claude-code: download and save each agent
    count = 0
    for agent in agents:
        aid = agent["id"]
        cat = agent["category"]

        if divisions and cat not in divisions:
            continue
        if agent_filter and agent_filter != aid:
            continue

        url = f"{raw_base}/{agent['path']}"
        dest_file = dest / f"{aid}.md"

        try:
            with urlopen(url) as resp:
                dest_file.write_bytes(resp.read())
            count += 1
            if count % 500 == 0:
                log(f"  {count}/{len(agents)}...")
        except Exception as e:
            log(f"  skip {aid}: {e}")

    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Install agency agents remotely")
    parser.add_argument("--tool", default="claude-code")
    parser.add_argument("--division", help="Comma-separated divisions")
    parser.add_argument("--agent", help="Single agent ID")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    args = parser.parse_args()

    raw_base = f"https://raw.githubusercontent.com/{args.repo}/{args.branch}"
    divisions = {d.strip() for d in args.division.split(",")} if args.division else None

    print(f"The Agency — Remote Install")
    print(f"  Source: github.com/{args.repo}")

    n = install_agents(raw_base, args.tool, divisions, args.agent)
    print(f"\nDone. {n} agents -> ~/.claude/agents/")


if __name__ == "__main__":
    main()
