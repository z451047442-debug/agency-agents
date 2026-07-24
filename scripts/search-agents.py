#!/usr/bin/env python
"""Search The Agency's agents by keyword, category, or field.

Canonical Python implementation replacing the shell-based search-agents.sh.

Usage:
    python scripts/search-agents.py "kubernetes"              # keyword search
    python scripts/search-agents.py --category cybersecurity  # category filter
    python scripts/search-agents.py "security" --category engineering
    python scripts/search-agents.py --list-categories         # list all categories
    python scripts/search-agents.py --categories              # alias
    python scripts/search-agents.py --stats                   # summary statistics
    python scripts/search-agents.py --scenario "mobile app"   # find agents for a task
    python scripts/search-agents.py --field name "Architect"  # search in specific field
    python scripts/search-agents.py --regex "ML|AI|machine learning"
    python scripts/search-agents.py --json "security"         # machine-readable output
    python scripts/search-agents.py --page 2 "engineer"       # paginated results
"""

import argparse
import json
import re
import sys
from collections import Counter

from _shared import BOLD, CYAN, REPO, RESET

INDEX_PATH = REPO / "AGENTS.json"

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]


def load_index():
    """Load AGENTS.json. Returns dict or exits with error."""
    if not INDEX_PATH.exists():
        print(f"ERROR: AGENTS.json not found at {INDEX_PATH}", file=sys.stderr)
        print("Run: ./scripts/generate-index.sh", file=sys.stderr)
        sys.exit(1)
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def search_agents(data, query=None, category=None, field=None, regex=False):
    """Search agents. Returns list of matching agent dicts."""
    results = []
    query_lower = (query or "").lower()

    for agent in data["agents"]:
        # Category filter
        if category and agent.get("category", "").lower() != category.lower():
            continue

        if not query:
            results.append(agent)
            continue

        # Field-specific search
        if field:
            haystack = (agent.get(field, "") or "").lower()
            if regex:
                if re.search(query, haystack, re.IGNORECASE):
                    results.append(agent)
            elif query_lower in haystack:
                results.append(agent)
            continue

        # Full-text search across name + description + id
        haystack = (
            (agent.get("name", "") or "") + " " +
            (agent.get("description", "") or "") + " " +
            agent.get("id", "")
        ).lower()

        if regex:
            if re.search(query, haystack, re.IGNORECASE):
                results.append(agent)
        else:
            # All query words must match (AND search)
            words = query_lower.split()
            if all(w in haystack for w in words):
                results.append(agent)

    return results


def print_stats(data):
    """Print summary statistics."""
    cats = Counter(a["category"] for a in data["agents"])
    with_nexus = sum(1 for a in data["agents"] if a.get("nexus_roles"))
    with_deps = sum(1 for a in data["agents"] if a.get("depends_on"))

    print(f"\n{BOLD}The Agency — Statistics{RESET}\n")
    print(f"  Total agents:      {data['total_agents']}")
    print(f"  Categories:        {data.get('total_categories', len(cats))}")
    print(f"  Generated:         {data['generated']}")
    print(f"  With nexus_roles:  {with_nexus} ({with_nexus * 100 // max(1, data['total_agents'])}%)")
    print(f"  With depends_on:   {with_deps} ({with_deps * 100 // max(1, data['total_agents'])}%)")
    print(f"\n{BOLD}Top 15 Categories:{RESET}")
    for cat, count in cats.most_common(15):
        bar = "█" * (count // 5)
        print(f"  {cat:<28} {count:>4} {bar}")

    # Emoji diversity
    emojis = Counter(a.get("emoji", "?") for a in data["agents"])
    print(f"\n{BOLD}Top 10 Emojis:{RESET}")
    for emoji, count in emojis.most_common(10):
        print(f"  {emoji} ({count})", end="  ")
    print("\n")


def print_categories(data):
    """List all categories with agent counts."""
    cats = Counter(a["category"] for a in data["agents"])
    print(f"\n{BOLD}{len(cats)} categories, {data['total_agents']} agents{RESET}\n")
    for cat, count in cats.most_common():
        print(f"  {cat:<30} {count:>4}")
    print()


SCENARIO_CATEGORIES = {
    "mobile app": ["engineering", "design", "testing", "product"],
    "web app": ["engineering", "design", "testing", "product"],
    "saas": ["engineering", "marketing", "sales", "product", "finance"],
    "security audit": ["cybersecurity", "security", "infrastructure", "testing"],
    "startup": ["strategy", "engineering", "marketing", "finance", "legal"],
    "api": ["engineering", "testing", "infrastructure"],
    "devops": ["infrastructure", "engineering", "testing"],
    "data pipeline": ["data-science", "engineering", "infrastructure"],
    "marketing campaign": ["marketing", "design", "sales", "data-science"],
    "content creation": ["marketing", "design", "media-entertainment", "publishing"],
    "game": ["game-development", "design", "media-entertainment", "engineering"],
    "blockchain": ["web3", "engineering", "legal", "finance"],
    "cloud migration": ["infrastructure", "engineering", "data-science"],
    "compliance": ["legal", "cybersecurity", "finance", "insurance"],
    "hiring": ["hr", "hr-tech", "operations"],
    "construction project": ["construction", "project-management", "real-estate"],
    "healthcare it": ["healthcare", "engineering", "data-science", "cybersecurity"],
    "financial model": ["finance", "securities", "insurance", "data-science"],
    "supply chain": ["logistics", "manufacturing", "retail", "agriculture"],
    "customer support": ["customer-service", "operations", "product"],
    "ar/vr": ["spatial-computing", "design", "engineering"],
    "iot": ["iot", "engineering", "manufacturing", "energy"],
}


def scenario_search(data, scenario):
    """Map a scenario string to relevant categories and search within them."""
    scenario_lower = scenario.lower()
    matched = []
    for key, cats in SCENARIO_CATEGORIES.items():
        if key in scenario_lower or any(w in scenario_lower for w in key.split()):
            matched.extend(cats)
    if not matched:
        # Fallback: search all categories with the scenario as keywords
        return search_agents(data, query=scenario)
    matched = list(dict.fromkeys(matched))  # deduplicate, keep order
    results = []
    for cat in matched:
        cat_results = search_agents(data, category=cat)
        results.extend(cat_results)
    return results


def print_results(results, page=1, per_page=25):
    """Print search results with pagination."""
    total = len(results)
    if total == 0:
        print("\nNo agents found.")
        print("Try: python scripts/search-agents.py --list-categories\n")
        return

    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = min(start + per_page, total)
    paginated = results[start:end]

    # Header
    if total_pages > 1:
        print(f"\n  Page {page}/{total_pages} ({total} total, showing {start + 1}-{end})")
    else:
        print(f"\n  {total} agent(s) found\n")

    # Column headers
    print(f"  {'EMOJI':<6s} {'NAME':<32s} {'CATEGORY':<22s} {'DESCRIPTION'}")
    print(f"  {'-'*6:<6s} {'-'*32:<32s} {'-'*22:<22s} {'-'*60}")

    for a in paginated:
        emoji = a.get("emoji", "")
        name = (a.get("name", "") or "")[:31]
        cat = a.get("category", "")[:21]
        desc = (a.get("description", "") or "")[:60]
        print(f"  {emoji:<6s} {name:<32s} {cat:<22s} {desc}")

    if total_pages > 1 and page < total_pages:
        print(f"\n  {CYAN}Next: --page {page + 1}{RESET}")
    print()


def print_json_results(results):
    """Print results as JSON."""
    output = {
        "total": len(results),
        "results": results,
    }
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Search The Agency's agent definitions")
    parser.add_argument("query", nargs="?",
                        help="Search query (keywords, space-separated for AND search)")
    parser.add_argument("--category", "-c",
                        help="Filter by category")
    parser.add_argument("--field", "-f",
                        help="Search only in this field (e.g., 'name', 'description')")
    parser.add_argument("--regex", "-r", action="store_true",
                        help="Treat query as a regular expression")
    parser.add_argument("--list-categories", "-l", action="store_true",
                        help="List all categories with agent counts")
    parser.add_argument("--categories", action="store_true",
                        help="Alias for --list-categories")
    parser.add_argument("--scenario",
                        help="Find agents for a task scenario (e.g. 'mobile app', 'security audit')")
    parser.add_argument("--stats", "-s", action="store_true",
                        help="Show summary statistics")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--page", type=int, default=1,
                        help="Page number for paginated results (default: 1)")
    parser.add_argument("--per-page", type=int, default=25,
                        help="Results per page (default: 25, max: 100)")
    args = parser.parse_args()

    data = load_index()

    # Stats mode
    if args.stats:
        print_stats(data)
        return

    # List categories mode
    if args.list_categories or args.categories:
        print_categories(data)
        return

    # Scenario mode
    if args.scenario:
        results = scenario_search(data, args.scenario)
        if args.json:
            print_json_results(results)
        else:
            print(f"\n  Scenario: {args.scenario}")
            print_results(results)
        return

    # Validate field name
    if args.field and args.field not in ("name", "description", "id", "emoji", "category"):
        print(f"ERROR: Invalid field '{args.field}'. Valid: name, description, id, emoji, category",
              file=sys.stderr)
        sys.exit(1)

    try:
        from telemetry import record_event
        record_event("search", term=args.query, category=args.category)
    except Exception:
        pass

    # Search mode
    results = search_agents(
        data,
        query=args.query,
        category=args.category,
        field=args.field,
        regex=args.regex,
    )

    per_page = max(1, min(args.per_page, 100))

    if args.json:
        print_json_results(results)
    else:
        # Show query context
        if args.query and args.category:
            print(f"\n  '{args.query}' in {args.category}/", end="")
        elif args.query:
            print(f"\n  '{args.query}' —", end="")
        elif args.category:
            print(f"\n  {args.category}/", end="")
        print_results(results, page=args.page, per_page=per_page)


if __name__ == "__main__":
    main()
