#!/usr/bin/env python
"""Rebalance NEXUS phase assignments — reduce Phase 4 overcrowding (1136→~300).

Usage:
    python scripts/rebalance-nexus-phases.py --dry-run   # preview only
    python scripts/rebalance-nexus-phases.py --apply      # write changes
"""

import argparse
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {"docs", "scripts", "examples", "integrations", "schemas", ".git", ".github"}

# Agents that SHOULD keep Phase 4
KEEP_P4 = [
    r"test", r"tester", r"testing", r"qa", r"quality",
    r"security", r"pentest", r"penetration", r"bug-bounty",
    r"compliance", r"audit", r"risk", r"governance",
    r"code-review", r"code-simplif", r"review",
    r"sre", r"reliability", r"resilience",
    r"incident", r"forensic", r"monitoring", r"observability",
    r"backup", r"disaster", r"recovery",
    r"accessibility", r"a11y",
    r"reality-checker", r"evidence",
]

# Agents that SHOULD get Phase 0
ADD_P0 = [
    r"research", r"researcher", r"analyst", r"analytics",
    r"trend", r"intelligence", r"discovery", r"explor",
    r"investigat", r"survey", r"market-research",
    r"data-scien", r"statistician",
    r"consultant", r"advisor", r"strategist",
    r"scientist", r"academic",
    r"evaluat", r"assess", r"audit",
]

# Agents that SHOULD get Phase 2
ADD_P2 = [
    r"infrastructure", r"platform",
    r"devops", r"devsecops",
    r"docker", r"kubernetes", r"container",
    r"terraform", r"ansible", r"iac",
    r"ci", r"cicd", r"pipeline",
    r"jenkins", r"github-actions", r"gitlab",
    r"setup", r"foundation", r"scaffold",
    r"database", r"dba",
    r"network", r"cloud", r"data-center",
]


def matches(agent_id: str, patterns: list[str]) -> bool:
    return any(re.search(p, agent_id, re.IGNORECASE) for p in patterns)


def rebalance(dry_run: bool = True):
    agent_files = [
        f for f in sorted(REPO.rglob("*.md"))
        if f.parts[len(REPO.parts):][0] not in EXCLUDE_DIRS
    ]
    stats = {"removed_p4": 0, "added_p0": 0, "added_p2": 0, "skipped": 0}

    for filepath in agent_files:
        content = filepath.read_text(encoding="utf-8")
        agent_id = filepath.stem
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        fm = parts[1]
        lines = fm.split("\n")
        new_lines = []
        in_nexus = False
        roles: list[str] = []
        changed = False

        for line in lines:
            if line.strip().startswith("nexus_roles:"):
                in_nexus = True
                new_lines.append(line)
                continue
            if in_nexus:
                m = re.match(r"^(\s+)-\s+(phase-\d-\w+)", line)
                if m:
                    roles.append(m.group(2))
                    new_lines.append(line)
                    continue
                elif re.match(r"^\S", line):
                    in_nexus = False
            new_lines.append(line)

        if not roles:
            stats["skipped"] += 1
            continue

        new_roles = list(roles)

        # 1. Remove Phase 4 from non-security/testing/QA agents
        if "phase-4-hardening" in new_roles and not matches(agent_id, KEEP_P4):
            new_roles.remove("phase-4-hardening")
            stats["removed_p4"] += 1
            changed = True

        # 2. Add Phase 0 to research/analysis agents
        if "phase-0-discovery" not in new_roles and matches(agent_id, ADD_P0):
            new_roles.append("phase-0-discovery")
            stats["added_p0"] += 1
            changed = True

        # 3. Add Phase 2 to infrastructure/platform agents
        if "phase-2-foundation" not in new_roles and matches(agent_id, ADD_P2):
            new_roles.append("phase-2-foundation")
            stats["added_p2"] += 1
            changed = True

        if not changed:
            stats["skipped"] += 1
            continue

        if dry_run and stats["removed_p4"] + stats["added_p0"] + stats["added_p2"] <= 3:
            new_roles.sort()
            print(f"  {agent_id}: {roles} -> {new_roles}")

        if dry_run:
            continue

        new_roles.sort()
        # Rebuild nexus_roles block in frontmatter
        indent = ""
        fm_lines = fm.split("\n")
        nexus_start = -1
        for i, line in enumerate(fm_lines):
            if line.strip().startswith("nexus_roles:"):
                nexus_start = i
                indent = line[:len(line) - len(line.lstrip())]
                break

        if nexus_start < 0:
            continue

        # Find end of nexus_roles block
        nexus_end = nexus_start + 1
        while nexus_end < len(fm_lines):
            if re.match(rf"^{indent}  - ", fm_lines[nexus_end]):
                nexus_end += 1
            else:
                break

        # Build new nexus_roles block
        role_lines = [f"{indent}nexus_roles:"]
        for role in new_roles:
            role_lines.append(f"{indent}  - {role}")

        new_fm = fm_lines[:nexus_start] + role_lines + fm_lines[nexus_end:]
        new_content = f"---\n{"\n".join(new_fm)}\n---{parts[2]}"
        filepath.write_text(new_content, encoding="utf-8")

    print(f"\n{'DRY RUN — ' if dry_run else ''}Rebalance results:")
    print(f"  Phase 4 removed:  {stats['removed_p4']}")
    print(f"  Phase 0 added:    {stats['added_p0']}")
    print(f"  Phase 2 added:    {stats['added_p2']}")
    print(f"  Skipped:          {stats['skipped']}")


def main():
    parser = argparse.ArgumentParser(description="Rebalance NEXUS phase assignments")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", dest="dry_run", action="store_false")
    args = parser.parse_args()
    rebalance(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
