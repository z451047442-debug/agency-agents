#!/usr/bin/env python
"""Analyze and suggest depends_on relationships between agents.

Scans agent content to discover implicit dependencies — when agent A's body
mentions concepts that are agent B's domain expertise. Also validates existing
depends_on references for broken links.

Usage:
    python scripts/analyze-deps.py --report                    # dependency health dashboard
    python scripts/analyze-deps.py --suggest --agent <id>      # suggest deps for one agent
    python scripts/analyze-deps.py --suggest --category engineering  # suggest for a category
    python scripts/analyze-deps.py --suggest --all --min-confidence 0.7  # suggest for all
    python scripts/analyze-deps.py --validate                  # check existing depends_on
    python scripts/analyze-deps.py --graph --agent <id>        # dependency graph for an agent
    python scripts/analyze-deps.py --orphans                   # agents with no deps at all
    python scripts/analyze-deps.py --json                      # machine-readable output
"""

import argparse
import json
import re
import sys
from collections import defaultdict

from _shared import (
    BOLD,
    CYAN,
    GREEN,
    RED,
    RESET,
    discover_agents,
    get_body,
    get_field,
    get_frontmatter_text,
    get_list_field,
)

# Generic terms that produce too many false positives in dependency matching
STOP_TERMS = {
    "data", "center", "systems", "network", "architect", "expert",
    "engineer", "manager", "director", "specialist", "analyst",
    "developer", "consultant", "designer", "advisor", "officer",
    "coordinator", "administrator", "operator", "technician",
    "engine", "system", "service", "solution", "platform",
    "advanced", "senior", "lead", "principal", "chief", "head",
    "management", "operations", "development", "engineering",
    "design", "support", "strategy", "planning", "analysis",
    "professional", "technical", "business", "enterprise",
    "digital", "cloud", "security", "quality", "compliance",
    "process", "project", "product", "program", "portfolio",
    "software", "hardware", "application", "infrastructure",
    "technology", "information", "communication", "integration",
    "implementation", "optimization", "automation", "monitoring",
    "testing", "deployment", "maintenance", "governance",
    "架构", "管理", "系统", "技术", "开发", "设计", "服务",
    "专家", "工程", "安全", "数据", "分析", "运营",
}

TERM_MIN_LEN = 4  # minimum length for a term to be considered specific enough


if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def extract_terms(filepath):
    """Extract domain-significant terms from an agent file.

    Returns a dict with:
        - id: agent id
        - category: category name
        - name: display name
        - name_terms: words from the agent name
        - desc_terms: key terms from description
        - body_terms: domain keywords from body sections
        - all_terms: union of all terms
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    fm = get_frontmatter_text(content)
    body = get_body(content)

    agent_id = filepath.stem
    category = filepath.parent.name
    name = get_field("name", fm)
    description = get_field("description", fm)

    # Extract terms from agent name (split by common delimiters in Chinese/English)
    name_terms = set()
    # Remove category prefix from id (e.g., "engineering-frontend-developer" → "frontend developer")
    clean_id = agent_id
    if clean_id.startswith(f"{category}-"):
        clean_id = clean_id[len(category) + 1:]
    for part in re.split(r"[-/]", clean_id):
        if len(part) >= 3:
            name_terms.add(part.lower())

    # Chinese characters: extract 2-4 char sequences
    chinese_chars = re.findall(r"[一-鿿]+", name)
    for chunk in chinese_chars:
        for i in range(len(chunk) - 1):
            bigram = chunk[i:i + 2]
            if len(bigram) == 2:
                name_terms.add(bigram)

    # Extract key terms from description
    desc_terms = set()
    # Split on Chinese/English boundaries and punctuation
    desc_words = re.findall(r"[一-鿿]{2,}|[a-zA-Z]{3,}", description)
    for w in desc_words:
        if len(w) >= 3:
            desc_terms.add(w.lower())

    # Extract domain keywords from body — bold terms, section headers, proper nouns
    body_terms = set()
    # Bold terms: **Term**
    for m in re.finditer(r"\*\*([^*]+)\*\*", body):
        term = m.group(1).strip().lower()
        if 3 <= len(term) <= 50:
            body_terms.add(term)
    # ALL_CAPS acronyms
    for m in re.finditer(r"\b([A-Z]{2,6}(?:/[A-Z]{2,6})*)\b", body):
        body_terms.add(m.group(1).lower())
    # Chinese concept terms (4+ chars in headers)
    for m in re.finditer(r"^#{1,3}\s+.*?([一-鿿]{4,})", body, re.MULTILINE):
        body_terms.add(m.group(1))

    all_terms = name_terms | desc_terms | body_terms

    # Filter out stop terms and short terms
    name_terms = {t for t in name_terms if t not in STOP_TERMS and len(t) >= TERM_MIN_LEN}
    desc_terms = {t for t in desc_terms if t not in STOP_TERMS and len(t) >= TERM_MIN_LEN}
    body_terms = {t for t in body_terms if t not in STOP_TERMS and len(t) >= TERM_MIN_LEN}
    all_terms = {t for t in all_terms if t not in STOP_TERMS and len(t) >= TERM_MIN_LEN}

    return {
        "id": agent_id,
        "category": category,
        "name": name,
        "name_terms": name_terms,
        "desc_terms": desc_terms,
        "body_terms": body_terms,
        "all_terms": all_terms,
        "body_text": body.lower(),
    }


def compute_dep_score(source, target):
    """Score how strongly source agent depends on target agent.

    Returns (score, evidence) where score is 0.0-1.0 and evidence lists the
    matching terms found.
    """
    evidence = []
    score = 0.0

    # 1. Direct name mention in body (strongest signal)
    for term in target["name_terms"]:
        if term in source["body_text"] and len(term) >= 4:
            evidence.append(f"body mentions '{term}'")
            score += 0.3

    # 2. Description term overlap
    desc_overlap = source["body_terms"] & target["desc_terms"]
    for term in desc_overlap:
        if len(term) >= 4:
            evidence.append(f"shared domain term '{term}'")
            score += 0.15

    # 3. Body term overlap (conceptual similarity)
    body_overlap = (source["body_terms"] & target["body_terms"]) - desc_overlap
    overlap_count = len(body_overlap)
    if overlap_count >= 3:
        score += 0.2
        evidence.append(f"{overlap_count} shared technical terms")
    elif overlap_count >= 1:
        score += 0.05 * min(overlap_count, 4)

    # 4. Same category bonus (agents in same domain often depend on each other)
    if source["category"] == target["category"]:
        score += 0.05
        evidence.append("same category")

    # 5. Cross-category: infrastructure/engineering are common dependencies
    cross_cat_pairs = {
        ("engineering", "infrastructure"): 0.05,
        ("data-science", "engineering"): 0.05,
        ("cybersecurity", "engineering"): 0.05,
        ("cybersecurity", "infrastructure"): 0.05,
    }
    bonus = cross_cat_pairs.get((source["category"], target["category"]), 0)
    if bonus:
        score += bonus

    # Cap at 1.0
    score = min(score, 1.0)

    return score, evidence


def build_term_index(all_agents):
    """Build a lookup index: term → [agent_ids that own this term]."""
    index = defaultdict(set)
    for agent in all_agents.values():
        for term in agent["all_terms"]:
            if len(term) >= 3:
                index[term].add(agent["id"])
    return index


def suggest_dependencies(all_agents, term_index, min_confidence=0.5, max_suggestions=5):
    """For each agent, suggest depends_on entries based on content analysis.

    Returns dict: agent_id → [(target_id, confidence, evidence), ...]
    """
    suggestions = {}

    for source_id, source in all_agents.items():
        candidates = []

        # Find candidate targets by term overlap
        candidate_ids = set()
        for term in source["body_terms"]:
            if term in term_index:
                candidate_ids.update(term_index[term])
        candidate_ids.discard(source_id)

        # Score each candidate
        for target_id in candidate_ids:
            if target_id not in all_agents:
                continue
            target = all_agents[target_id]
            score, evidence = compute_dep_score(source, target)
            if score >= min_confidence:
                candidates.append((target_id, round(score, 2), evidence[:3]))

        # Sort by confidence and take top N
        candidates.sort(key=lambda x: -x[1])
        suggestions[source_id] = candidates[:max_suggestions]

    return suggestions


def build_agent_index(category_filter=None):
    """Build {agent_id: terms_dict} from all agent files."""
    index = {}
    for _cat, _rel, filepath in discover_agents(category_filter=category_filter):
        terms = extract_terms(filepath)
        if terms:
            index[terms["id"]] = terms
    return index


def validate_depends_on(all_agents):
    """Check all existing depends_on references for validity.

    Returns (valid_refs, broken_refs, missing_from).
    """
    valid = []
    broken = []
    agents_with_deps = 0

    for _cat, _rel, filepath in discover_agents():
        content = filepath.read_text(encoding="utf-8")
        fm = get_frontmatter_text(content)
        deps = get_list_field("depends_on", fm)

        if not deps:
            continue
        agents_with_deps += 1

        for dep_id in deps:
            if dep_id in all_agents:
                valid.append((filepath.stem, dep_id, all_agents[dep_id]["category"]))
            else:
                broken.append((filepath.stem, dep_id))

    return valid, broken, agents_with_deps


def print_dependency_health(all_agents):
    """Print dependency graph health dashboard."""
    total = len(all_agents)
    valid, broken, agents_with_deps = validate_depends_on(all_agents)

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Dependency Graph Health{RESET}")
    print(f"  Total agents: {total}  |  With depends_on: {agents_with_deps}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    print(f"{BOLD}depends_on Usage:{RESET}")
    pct = agents_with_deps / total * 100
    print(f"  Agents with dependencies: {agents_with_deps} ({pct:.1f}%)")
    print(f"  Valid references:         {GREEN}{len(valid)}{RESET}")
    print(f"  Broken references:        {RED}{len(broken)}{RESET}")

    if broken:
        print(f"\n{BOLD}Broken depends_on (target agent not found):{RESET}")
        for source, target in broken:
            print(f"  {RED}✗{RESET} {source} → {target} (not found)")

    if valid:
        print(f"\n{BOLD}Existing Dependency Graph:{RESET}")
        # Group by target (most-depended-on agents)
        dep_counts = defaultdict(list)
        for source, target, _cat in valid:
            dep_counts[target].append(source)
        for target, sources in sorted(dep_counts.items(), key=lambda x: -len(x[1])):
            print(f"  {CYAN}{target}{RESET} ← {', '.join(sources[:3])}"
                  f"{f' ... +{len(sources)-3}' if len(sources) > 3 else ''}")


def print_suggestions(suggestions, agent_filter=None, top_n=10):
    """Print dependency suggestions."""
    if agent_filter:
        suggestions = {k: v for k, v in suggestions.items() if k == agent_filter}

    total_suggestions = sum(len(v) for v in suggestions.values())
    agents_with_suggestions = sum(1 for v in suggestions.values() if v)

    print(f"\n{BOLD}Dependency Suggestions{RESET}")
    print(f"  {agents_with_suggestions} agents have {total_suggestions} potential dependencies\n")

    if agent_filter:
        # Detailed view for single agent
        if agent_filter in suggestions:
            deps = suggestions[agent_filter]
            print(f"{BOLD}{agent_filter}:{RESET}")
            if deps:
                for target_id, confidence, evidence in deps:
                    print(f"  {confidence:.2f} → {CYAN}{target_id}{RESET}")
                    for e in evidence:
                        print(f"        {e}")
            else:
                print("  No suggestions above confidence threshold")
        else:
            print("  Agent not found in index")
    else:
        # Top suggestions across all agents
        ranked = []
        for agent_id, deps in suggestions.items():
            for target_id, confidence, evidence in deps:
                ranked.append((confidence, agent_id, target_id, evidence))
        ranked.sort(key=lambda x: -x[0])

        for confidence, agent_id, target_id, evidence in ranked[:top_n]:
            print(f"  {confidence:.2f}  {agent_id} → {CYAN}{target_id}{RESET}")
            print(f"          {evidence[0] if evidence else ''}")


def print_orphans(all_agents, suggestions):
    """Show agents with no dependencies at all."""
    orphan_ids = []
    for agent_id in all_agents:
        has_suggestion = bool(suggestions.get(agent_id))
        if not has_suggestion:
            orphan_ids.append(agent_id)

    print(f"\n{BOLD}Orphan Agents (no dependencies):{RESET}")
    print(f"  {len(orphan_ids)} agents ({len(orphan_ids) / len(all_agents) * 100:.1f}%) have no dependency relationships\n")

    # Show by category
    by_cat = defaultdict(list)
    for aid in orphan_ids:
        cat = all_agents[aid]["category"]
        by_cat[cat].append(aid)

    for cat in sorted(by_cat.keys(), key=lambda c: -len(by_cat[c]))[:10]:
        agents_in_cat = sum(1 for a in all_agents.values() if a["category"] == cat)
        pct = len(by_cat[cat]) / agents_in_cat * 100
        print(f"  {cat:<28} {len(by_cat[cat]):>4}/{agents_in_cat:<4} orphan ({pct:.0f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze and suggest depends_on relationships between agents")
    parser.add_argument("--report", action="store_true",
                        help="Dependency graph health dashboard")
    parser.add_argument("--suggest", action="store_true",
                        help="Suggest dependencies based on content analysis")
    parser.add_argument("--validate", action="store_true",
                        help="Check existing depends_on for broken references")
    parser.add_argument("--orphans", action="store_true",
                        help="List agents with no dependency relationships")
    parser.add_argument("--agent", "-a",
                        help="Filter to specific agent")
    parser.add_argument("--category", "-c",
                        help="Filter to specific category")
    parser.add_argument("--min-confidence", type=float, default=0.5,
                        help="Minimum confidence for suggestions (default: 0.5)")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable JSON output")
    args = parser.parse_args()

    # Build index (shared across all modes)
    all_agents = build_agent_index(category_filter=args.category)

    # Default to --report if no action specified
    if not any([args.suggest, args.validate, args.orphans]):
        args.report = True

    # --validate mode
    if args.validate:
        valid, broken, count = validate_depends_on(all_agents)
        print(f"\n{BOLD}depends_on Validation{RESET}")
        print(f"  Agents with dependencies: {count}")
        print(f"  Valid references:         {GREEN}{len(valid)}{RESET}")
        print(f"  Broken references:        {RED}{len(broken)}{RESET}")
        if broken:
            for source, target in broken:
                print(f"  {RED}✗{RESET} {source} → {target}")
        return

    # --suggest mode
    if args.suggest:
        term_index = build_term_index(all_agents)
        suggestions = suggest_dependencies(all_agents, term_index,
                                           min_confidence=args.min_confidence)

        if args.json:
            output = {}
            for agent_id, deps in suggestions.items():
                if deps:
                    output[agent_id] = [
                        {"target": t, "confidence": c, "evidence": e}
                        for t, c, e in deps
                    ]
            json.dump({"suggestions": output, "total": len(output)},
                      sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
        else:
            print_suggestions(suggestions, agent_filter=args.agent)
        return

    # --orphans mode
    if args.orphans:
        term_index = build_term_index(all_agents)
        suggestions = suggest_dependencies(all_agents, term_index,
                                           min_confidence=0.3)
        print_orphans(all_agents, suggestions)
        return

    # --report mode (default)
    if args.report:
        if args.json:
            valid, broken, count = validate_depends_on(all_agents)
            json.dump({
                "total_agents": len(all_agents),
                "agents_with_deps": count,
                "valid_refs": len(valid),
                "broken_refs": len(broken),
                "broken_details": [{"source": s, "target": t} for s, t in broken],
                "valid_details": [{"source": s, "target": t, "target_category": c}
                                  for s, t, c in valid],
            }, sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
        else:
            print_dependency_health(all_agents)


if __name__ == "__main__":
    main()
