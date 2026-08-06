#!/usr/bin/env python3
"""Add phase-6-operate to strategy, thinking-models, and key game-development agents."""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
data = json.loads((REPO / "AGENTS.json").read_text(encoding="utf-8"))
agents = data["agents"]

ADD_ALL = {"strategy", "thinking-models"}
ADD_GAME = {
    "game-development-game-producer", "game-development-game-quality-assurance",
    "game-development-game-designer", "game-development-game-monetization-designer",
    "game-development-engineering-video-game-backend", "game-development-game-psychology",
    "game-development-narrative-design",
}

updated = 0
for a in agents:
    c = a["category"]
    aid = a["id"]
    roles = a.get("nexus_roles") or []
    if "phase-6-operate" in roles:
        continue
    if c not in ADD_ALL and not (c == "game-development" and aid in ADD_GAME):
        continue

    fpath = REPO / a["path"]
    content = fpath.read_text(encoding="utf-8")

    def append_role(m):
        block = m.group()
        return block.rstrip("\n") + "\n- phase-6-operate\n"

    new_content, n = re.subn(
        r"nexus_roles:\n(?:- .*\n?)+",
        append_role,
        content,
        count=1,
    )
    if n == 0:
        print(f"  WARNING: no nexus_roles in {aid}")
        continue
    fpath.write_text(new_content, encoding="utf-8")
    updated += 1

print(f"Updated {updated} agents")
