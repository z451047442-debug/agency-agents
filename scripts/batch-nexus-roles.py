#!/usr/bin/env python
"""Batch-assign nexus_roles to agents based on category and name patterns.

Usage:
    python scripts/batch-nexus-roles.py [--dry-run] [--category NAME]
"""

import argparse
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Category-based phase assignments with optional keyword filters
# Format: category -> [(keywords_regex, [phases]), ...]
# First matching rule wins; if no keyword matches, the last entry is the default.
ROLE_RULES = {
    "product": [
        (r"trend|research|analyst", ["phase-0-discovery"]),
        (r"growth|launch", ["phase-5-launch"]),
        (r"manager|operations|technical|b2b", ["phase-0-discovery", "phase-1-strategy", "phase-5-launch"]),
        (None, ["phase-0-discovery", "phase-1-strategy"]),
    ],
    "strategy": [
        (None, ["phase-0-discovery", "phase-1-strategy"]),
    ],
    "design": [
        (r"research|persona", ["phase-0-discovery"]),
        (r"architect|system", ["phase-1-strategy"]),
        (r"brand|visual|creative|injector|storyteller", ["phase-1-strategy", "phase-5-launch"]),
        (None, ["phase-1-strategy", "phase-3-build"]),
    ],
    "marketing": [
        (r"research|trend|analyst|intelligence|audit", ["phase-0-discovery"]),
        (r"strategist|planning|positioning|brand", ["phase-1-strategy", "phase-5-launch"]),
        (r"seo|sem|content|social|email|campaign|ads|ppc|growth", ["phase-5-launch"]),
        (None, ["phase-5-launch"]),
    ],
    "sales": [
        (r"research|analyst|intelligence", ["phase-0-discovery"]),
        (r"strategist|coach|enablement", ["phase-1-strategy"]),
        (None, ["phase-5-launch"]),
    ],
    "engineering": [
        (r"architect|design$|designer|api-designer", ["phase-1-strategy"]),
        (r"devops|platform|sre|release|ci|cicd|build-release", ["phase-2-foundation", "phase-6-operate"]),
        (r"security|appsec|devsecops", ["phase-4-hardening"]),
        (r"ai-engineer|ai-agent|ml|machine-learning|data-engineer|nlp|llm|prompt", ["phase-3-build"]),
        (r"review|code-review|code-simplif|comment-analy|type-design", ["phase-4-hardening"]),
        (r"developer|engineer|fullstack|frontend|backend|mobile|flutter|swift|android|ios|react|next|vue|angular|django|fastapi|laravel|wordpress|drupal", ["phase-3-build"]),
        (None, ["phase-3-build"]),
    ],
    "infrastructure": [
        (r"architect|enterprise", ["phase-1-strategy"]),
        (r"devops|platform|automation|terraform|ansible|jenkins|github-actions|argocd|docker|kubernetes|container", ["phase-2-foundation"]),
        (r"sre|monitoring|observability|incident|alert|zabbix|prometheus|grafana|datadog|splunk|elk|graylog|nagios|cacti", ["phase-6-operate"]),
        (r"backup|disaster|recovery|bcp", ["phase-2-foundation", "phase-6-operate"]),
        (r"director|it-director", ["phase-1-strategy"]),
        (r"cloud-architect|cloud-migration", ["phase-1-strategy", "phase-2-foundation"]),
        (None, ["phase-2-foundation", "phase-6-operate"]),
    ],
    "cybersecurity": [
        (r"architect|csiso|chief|grc|compliance|audit|risk|privacy|dpo", ["phase-1-strategy", "phase-4-hardening"]),
        (r"analyst|soc|threat|detect|monitor|intelligence|forensic|incident|response|malware", ["phase-4-hardening", "phase-6-operate"]),
        (r"pentest|penetration|tester|red-team|bug-bounty|exploit", ["phase-4-hardening"]),
        (r"engineer|appsec|devsecops|security-champion|firmware|hardware|crypto", ["phase-3-build", "phase-4-hardening"]),
        (None, ["phase-4-hardening"]),
    ],
    "security": [
        (r"architect|cloud-security", ["phase-1-strategy", "phase-4-hardening"]),
        (r"incident|respond|forensic", ["phase-4-hardening", "phase-6-operate"]),
        (r"pentest|penetration|tester", ["phase-4-hardening"]),
        (None, ["phase-4-hardening"]),
    ],
    "testing": [
        (r"architect|strateg|manager|director", ["phase-1-strategy"]),
        (r"automation|sdet|playwright|selenium|cypress|test-dev", ["phase-3-build"]),
        (r"performance|benchmark|load|stress", ["phase-4-hardening"]),
        (r"accessibility|a11y|auditor|usability", ["phase-4-hardening"]),
        (r"security|penetration|vulnerability", ["phase-4-hardening"]),
        (None, ["phase-4-hardening"]),
    ],
    "quality": [
        (r"manager|director|qms|iso|auditor", ["phase-1-strategy"]),
        (r"sqa|software|test-automation", ["phase-4-hardening"]),
        (None, ["phase-4-hardening"]),
    ],
    "project-management": [
        (r"pmo|director|portfolio", ["phase-1-strategy"]),
        (r"manager|pmp|senior", ["phase-1-strategy", "phase-6-operate"]),
        (r"scrum|agile|coach", ["phase-3-build"]),
        (r"orchestrat|shepherd", ["phase-1-strategy", "phase-6-operate"]),
        (None, ["phase-1-strategy", "phase-6-operate"]),
    ],
    "data-science": [
        (r"research|scientist|analyst|bi|intelligence|causal|experiment", ["phase-0-discovery"]),
        (r"architect|governance|catalog|lineage", ["phase-1-strategy"]),
        (r"engineer|etl|elt|pipeline|warehouse|lake|platform|mlops", ["phase-2-foundation", "phase-3-build"]),
        (r"monitoring|observability", ["phase-6-operate"]),
        (None, ["phase-3-build"]),
    ],
    "operations": [
        (r"director|manager|analyst", ["phase-1-strategy", "phase-6-operate"]),
        (None, ["phase-6-operate"]),
    ],
    "customer-service": [
        (r"manager|director|strateg|analyst", ["phase-1-strategy"]),
        (None, ["phase-6-operate"]),
    ],
    "finance": [
        (r"analyst|research|audit|risk|compliance|controller|cfo", ["phase-0-discovery"]),
        (r"strateg|advisor|planning|director", ["phase-1-strategy"]),
        (None, ["phase-0-discovery"]),
    ],
    "legal": [
        (None, ["phase-0-discovery", "phase-1-strategy"]),
    ],
    "hr": [
        (r"strateg|director|consultant|partner|hrbp|business-partner", ["phase-1-strategy"]),
        (None, ["phase-6-operate"]),
    ],
    "robotics": [
        (r"architect|director", ["phase-1-strategy"]),
        (r"control|motion|perception|engineer|developer", ["phase-3-build"]),
        (None, ["phase-3-build"]),
    ],
    "iot": [
        (r"architect|director", ["phase-1-strategy"]),
        (None, ["phase-3-build"]),
    ],
    "game-development": [
        (r"designer|director|producer", ["phase-0-discovery", "phase-1-strategy"]),
        (r"developer|engineer|programmer|shader|artist", ["phase-3-build"]),
        (None, ["phase-3-build"]),
    ],
    "web3": [
        (r"analyst|research", ["phase-0-discovery"]),
        (r"architect|director", ["phase-1-strategy"]),
        (r"developer|engineer|solidity|smart-contract", ["phase-3-build"]),
        (r"audit|security", ["phase-4-hardening"]),
        (None, ["phase-3-build"]),
    ],
    "gis": [
        (r"analyst|scientist|research", ["phase-0-discovery"]),
        (r"architect|consultant|strateg", ["phase-1-strategy"]),
        (r"developer|engineer|specialist", ["phase-3-build"]),
        (None, ["phase-3-build"]),
    ],
    "specialized": [
        (r"analyst|research|officer|grant|writer|privacy", ["phase-0-discovery"]),
        (r"strateg|consultant|coach|mentor|advisor|cfo|chief|director", ["phase-1-strategy"]),
        (r"manager|operations|success|customer-success|integration", ["phase-6-operate"]),
        (None, ["phase-1-strategy"]),
    ],
}

# Default assignment for categories not in ROLE_RULES
DEFAULT_BY_CATEGORY = {
    # Build-focused domains — add hardening so experts validate their own output
    "healthcare": ["phase-3-build", "phase-4-hardening"],
    "pharma-biotech": ["phase-3-build", "phase-4-hardening"],
    "media-entertainment": ["phase-3-build", "phase-4-hardening"],
    "education": ["phase-3-build", "phase-4-hardening"],
    "spatial-computing": ["phase-3-build", "phase-4-hardening"],
    "environmental": ["phase-3-build", "phase-4-hardening"],
    "agriculture": ["phase-3-build", "phase-4-hardening"],
    "energy": ["phase-3-build", "phase-4-hardening"],
    "manufacturing": ["phase-3-build", "phase-4-hardening"],
    "automotive": ["phase-3-build", "phase-4-hardening"],
    "aerospace": ["phase-3-build", "phase-4-hardening"],
    "construction": ["phase-3-build", "phase-4-hardening"],
    "logistics": ["phase-3-build", "phase-4-hardening"],
    "insurance": ["phase-3-build", "phase-4-hardening"],
    "food-beverage": ["phase-3-build", "phase-4-hardening"],
    "mining": ["phase-3-build", "phase-4-hardening"],
    "forestry": ["phase-3-build", "phase-4-hardening"],
    "museums": ["phase-3-build", "phase-4-hardening"],
    "localization": ["phase-3-build", "phase-4-hardening"],
    "hr-tech": ["phase-3-build", "phase-4-hardening"],
    "securities": ["phase-3-build", "phase-4-hardening"],
    # Launch-focused domains — add hardening for pre-launch quality
    "retail": ["phase-5-launch", "phase-4-hardening"],
    "real-estate": ["phase-5-launch", "phase-4-hardening"],
    "tourism": ["phase-5-launch", "phase-4-hardening"],
    "sports": ["phase-5-launch", "phase-4-hardening"],
    "fashion": ["phase-5-launch", "phase-4-hardening"],
    "publishing": ["phase-5-launch", "phase-4-hardening"],
    "events": ["phase-5-launch", "phase-4-hardening"],
    "beauty": ["phase-5-launch", "phase-4-hardening"],
    "lottery": ["phase-5-launch", "phase-4-hardening"],
    # Foundation/Infra domains — add hardening + operate for full lifecycle
    "network-engineering": ["phase-2-foundation", "phase-4-hardening", "phase-6-operate"],
    "telecom": ["phase-2-foundation", "phase-4-hardening", "phase-6-operate"],
    # Operate-focused domains — add hardening for quality sustainment
    "nonprofit": ["phase-6-operate", "phase-4-hardening"],
    "emergency": ["phase-6-operate", "phase-4-hardening"],
    "pets": ["phase-6-operate", "phase-4-hardening"],
    "administration": ["phase-6-operate", "phase-4-hardening"],
    # Strategy/Discovery domains — add hardening for architectural validation
    "government": ["phase-1-strategy", "phase-4-hardening"],
    "libraries": ["phase-0-discovery", "phase-4-hardening"],
}


def parse_frontmatter(content):
    """Return (fm_text, body) or None if no valid frontmatter."""
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    return parts[1], parts[2]


def has_nexus_roles(fm_text):
    return bool(re.search(r"^nexus_roles:", fm_text, re.MULTILINE))


def add_nexus_roles(fm_text, roles):
    """Insert nexus_roles YAML into frontmatter after date_added."""
    lines = fm_text.split("\n")
    result = []
    inserted = False
    for line in lines:
        result.append(line)
        if not inserted and re.match(r"^date_added:", line):
            result.append("nexus_roles:")
            for role in roles:
                result.append(f"  - {role}")
            inserted = True
    if not inserted:
        result.append("nexus_roles:")
        for role in roles:
            result.append(f"  - {role}")
    return "\n".join(result)


def replace_nexus_roles(fm_text, roles):
    """Strip existing nexus_roles block, then insert new one."""
    fm_text = fm_text.lstrip("\n")
    lines = fm_text.split("\n")
    cleaned = []
    skip = False
    for line in lines:
        if re.match(r"^nexus_roles:", line):
            skip = True
            continue
        if skip:
            if re.match(r"^\s+-", line):
                continue
            skip = False
            cleaned.append(line)
            continue
        cleaned.append(line)
    return add_nexus_roles("\n".join(cleaned), roles)


def assign_roles(agent_id, category):
    """Assign nexus_roles based on agent id and category rules."""
    LEADERSHIP_PATTERN = (
        r"director|chief|head-of|vp-|ceo|coo|cto|ciso|cfo"
        r"|president|general-manager|gm-"
    )
    is_leader = bool(re.search(LEADERSHIP_PATTERN, agent_id, re.IGNORECASE))

    # Get category-based roles first
    rules = ROLE_RULES.get(category)
    if rules:
        for pattern, roles in rules:
            if pattern is None:
                base_roles = roles
                break
            if re.search(pattern, agent_id, re.IGNORECASE):
                base_roles = roles
                break
        else:
            base_roles = []
    else:
        base_roles = DEFAULT_BY_CATEGORY.get(category)

    if base_roles is None:
        return None

    # Post-processing: universal hardening coverage
    # Agents in build/launch/operate/discovery should also validate quality
    HARDENABLE = {"phase-3-build", "phase-5-launch", "phase-6-operate", "phase-0-discovery"}
    if base_roles and any(r in HARDENABLE for r in base_roles):
        if "phase-4-hardening" not in base_roles:
            base_roles = list(base_roles) + ["phase-4-hardening"]

    # Leadership agents get strategy as primary role, plus their domain roles
    if is_leader and "phase-1-strategy" not in base_roles:
        return ["phase-1-strategy"] + base_roles

    return base_roles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--category", help="Only process one category")
    parser.add_argument("--force", action="store_true",
                        help="Re-assign nexus_roles even if agent already has them")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    EXCLUDE = {
        ".git", ".github", ".vs", ".vscode", ".claude", ".pytest_cache",
        "examples", "integrations", "scripts", "docs", "schemas", "tests",
        "env", "node_modules", "__pycache__",
    }

    assigned = 0
    skipped = 0
    already = 0

    for cat_dir in sorted(REPO.iterdir()):
        if not cat_dir.is_dir() or cat_dir.name.startswith("."):
            continue
        if cat_dir.name in EXCLUDE:
            continue
        if args.category and cat_dir.name != args.category:
            continue

        for md_file in sorted(cat_dir.rglob("*.md")):
            content = md_file.read_text(encoding="utf-8")

            parsed = parse_frontmatter(content)
            if parsed is None:
                continue

            fm_text, body = parsed

            if has_nexus_roles(fm_text):
                if not args.force:
                    already += 1
                    continue
                already += 1

            roles = assign_roles(md_file.stem, cat_dir.name)
            if roles is None:
                skipped += 1
                continue

            if has_nexus_roles(fm_text) and args.force:
                new_fm = replace_nexus_roles(fm_text, roles)
            else:
                new_fm = add_nexus_roles(fm_text, roles)
            new_content = "---\n" + new_fm + "---" + body

            if args.dry_run:
                if args.verbose:
                    rel = md_file.relative_to(REPO)
                    print(f"  WOULD UPDATE {rel} -> {roles}")
                assigned += 1
            else:
                md_file.write_text(new_content, encoding="utf-8", newline="\n")
                if args.verbose:
                    rel = md_file.relative_to(REPO)
                    print(f"  UPDATED {rel} -> {roles}")
                assigned += 1

    print(f"\nAssigned: {assigned}  Already had: {already}  Skipped: {skipped}")
    if args.dry_run:
        print("DRY RUN — no files modified")


if __name__ == "__main__":
    main()
