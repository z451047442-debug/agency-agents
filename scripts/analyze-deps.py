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
    YELLOW,
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

# Cross-category bonus table: (source_category, target_category) → bonus score.
# These represent real-world knowledge dependencies — e.g., healthcare depends
# on legal (compliance), cybersecurity (HIPAA/HITECH), and data-science (analytics).
# Bonus values: 0.08 = strong cross-domain dependency, 0.05 = moderate,
# 0.03 = weak/incidental. Without this table, the dependency analyzer is blind
# to cross-category relationships and reinforces category silos.
CROSS_CATEGORY_BONUS = {
    # ── engineering consumes infrastructure & security ──
    ("engineering", "infrastructure"):      0.08,
    ("engineering", "cybersecurity"):        0.06,
    ("engineering", "security"):             0.06,
    ("engineering", "data-science"):         0.05,
    ("engineering", "project-management"):   0.05,
    ("engineering", "testing"):              0.05,
    ("engineering", "iot"):                  0.04,
    ("engineering", "web3"):                 0.03,

    # ── infrastructure consumes engineering & security ──
    ("infrastructure", "engineering"):       0.08,
    ("infrastructure", "cybersecurity"):     0.06,
    ("infrastructure", "security"):          0.06,
    ("infrastructure", "network-engineering"): 0.05,
    ("infrastructure", "project-management"): 0.04,

    # ── cybersecurity connects to everything ──
    ("cybersecurity", "engineering"):        0.06,
    ("cybersecurity", "infrastructure"):     0.06,
    ("cybersecurity", "legal"):              0.05,
    ("cybersecurity", "finance"):            0.04,
    ("cybersecurity", "healthcare"):         0.04,
    ("cybersecurity", "government"):         0.04,

    # ── healthcare cross-domain deps ──
    ("healthcare", "legal"):                 0.06,
    ("healthcare", "cybersecurity"):         0.05,
    ("healthcare", "data-science"):          0.05,
    ("healthcare", "pharma-biotech"):        0.05,
    ("healthcare", "insurance"):             0.04,
    ("healthcare", "emergency"):             0.04,

    # ── finance & legal ──
    ("finance", "legal"):                    0.06,
    ("finance", "cybersecurity"):            0.05,
    ("finance", "data-science"):             0.05,
    ("finance", "securities"):               0.05,
    ("finance", "insurance"):                0.04,
    ("legal", "finance"):                    0.05,
    ("legal", "government"):                 0.05,
    ("legal", "cybersecurity"):              0.04,
    ("legal", "real-estate"):                0.03,

    # ── construction & environmental ──
    ("construction", "environmental"):       0.06,
    ("construction", "legal"):               0.05,
    ("construction", "project-management"):  0.05,
    ("construction", "engineering"):         0.05,
    ("environmental", "construction"):       0.05,
    ("environmental", "legal"):              0.05,
    ("environmental", "energy"):             0.05,
    ("environmental", "agriculture"):        0.04,

    # ── aerospace & automotive consume engineering ──
    ("aerospace", "engineering"):            0.06,
    ("aerospace", "cybersecurity"):          0.05,
    ("aerospace", "project-management"):     0.05,
    ("aerospace", "legal"):                  0.04,
    ("automotive", "engineering"):           0.06,
    ("automotive", "cybersecurity"):         0.05,
    ("automotive", "manufacturing"):         0.05,
    ("automotive", "iot"):                   0.04,

    # ── energy cross-domain ──
    ("energy", "environmental"):             0.05,
    ("energy", "engineering"):               0.05,
    ("energy", "legal"):                     0.04,
    ("energy", "finance"):                   0.04,
    ("energy", "project-management"):        0.04,

    # ── manufacturing ──
    ("manufacturing", "engineering"):        0.06,
    ("manufacturing", "supply-chain"):       0.05,
    ("manufacturing", "iot"):                0.04,
    ("manufacturing", "quality"):            0.04,

    # ── logistics & supply chain ──
    ("logistics", "engineering"):            0.04,
    ("logistics", "iot"):                    0.04,
    ("logistics", "retail"):                 0.03,

    # ── data-science serves many ──
    ("data-science", "engineering"):         0.05,
    ("data-science", "finance"):             0.04,
    ("data-science", "healthcare"):          0.04,
    ("data-science", "marketing"):           0.04,

    # ── marketing cross-domain ──
    ("marketing", "data-science"):           0.04,
    ("marketing", "design"):                 0.04,
    ("marketing", "retail"):                 0.03,

    # ── agriculture ──
    ("agriculture", "environmental"):        0.05,
    ("agriculture", "data-science"):         0.04,
    ("agriculture", "logistics"):            0.03,

    # ── government ──
    ("government", "legal"):                 0.05,
    ("government", "cybersecurity"):         0.05,
    ("government", "emergency"):             0.04,

    # ── project-management serves many ──
    ("project-management", "engineering"):   0.04,
    ("project-management", "construction"):  0.04,
    ("project-management", "operations"):    0.03,

    # ── robotics consumes multiple domains ──
    ("robotics", "engineering"):             0.06,
    ("robotics", "iot"):                     0.04,
    ("robotics", "manufacturing"):           0.04,

    # ── education ──
    ("education", "design"):                 0.03,
    ("education", "hr"):                     0.03,

    # ── spatial-computing ──
    ("spatial-computing", "engineering"):    0.05,
    ("spatial-computing", "design"):         0.04,
    ("spatial-computing", "gis"):            0.03,
}

# Build reverse direction automatically so we don't duplicate every pair.
# Most cross-domain relationships are bidirectional.
_reverse_bonuses = {}
for (src, tgt), bonus in CROSS_CATEGORY_BONUS.items():
    _reverse_bonuses[(tgt, src)] = bonus * 0.8  # slightly lower for reverse direction
CROSS_CATEGORY_BONUS.update(_reverse_bonuses)


if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]


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
    except (UnicodeDecodeError, OSError):
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

    # 5. Cross-category bonus: reward meaningful cross-domain connections.
    # Same-category gets a mild bonus but cross-category bridges are prioritized
    # because they build the "latticework" — they're what make the agent network
    # genuinely interconnected rather than 65 independent silos.
    if source["category"] != target["category"]:
        cross_bonus = CROSS_CATEGORY_BONUS.get(
            (source["category"], target["category"]), 0.0
        )
        if cross_bonus:
            score += cross_bonus
            evidence.append(f"cross-category: {source['category']}↔{target['category']}")
    else:
        # Same-category: mild bonus only, to avoid reinforcing silo walls
        score += 0.03

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


def find_cycles(all_agents, max_report=10):
    """Detect cycles in the depends_on graph using DFS.

    Returns (cycle_count, largest_cycle, example_cycles, largest_component_size).
    """
    # Build graph from agent frontmatter (not from terms index)
    graph = {aid: set() for aid in all_agents}
    for _cat, _rel, filepath in discover_agents():
        content = filepath.read_text(encoding="utf-8")
        fm = get_frontmatter_text(content)
        deps = get_list_field("depends_on", fm)
        for dep in deps:
            if dep in graph:
                graph[filepath.stem].add(dep)

    cycles: list[list[str]] = []
    # Color-based iterative DFS: WHITE=0 (unvisited), GRAY=1 (in stack), BLACK=2 (done)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = dict.fromkeys(graph, WHITE)
    path: list[str] = []
    # Stack entries: (node, iterator_over_neighbors_or_None)
    # - On first visit: push (node, iter(neighbors)), set GRAY, append to path
    # - After iterating neighbors: pop path, set BLACK
    stack: list[tuple[str, object]] = []

    for start_node in sorted(graph):
        if color[start_node] != WHITE:
            continue
        stack.append((start_node, None))
        while stack:
            node, neighbor_iter = stack.pop()
            if neighbor_iter is None:
                # First time seeing this node — initialise traversal
                if color[node] == BLACK:
                    continue
                color[node] = GRAY
                path.append(node)
                neighbors = iter(graph.get(node, set()))
                stack.append((node, neighbors))
            else:
                # Resume after processing children — try next neighbor
                try:
                    neighbor = next(neighbor_iter)
                except StopIteration:
                    # All neighbors processed — finish node
                    path.pop()
                    color[node] = BLACK
                    continue
                # Push back current node to resume after this neighbor
                stack.append((node, neighbor_iter))
                if color[neighbor] == WHITE:
                    stack.append((neighbor, None))
                elif color[neighbor] == GRAY:
                    # Cycle found: neighbor is on the current path
                    cycle_start = path.index(neighbor)
                    cycles.append(list(path[cycle_start:]))

    undirected = {aid: set(graph[aid]) for aid in graph}
    for aid in graph:
        for dep in graph[aid]:
            undirected.setdefault(dep, set()).add(aid)

    seen_comp = set()
    max_comp = 0

    def bfs_component(start):
        q = [start]
        comp = {start}
        seen_comp.add(start)
        while q:
            n = q.pop()
            for nb in undirected.get(n, set()):
                if nb not in seen_comp:
                    seen_comp.add(nb)
                    comp.add(nb)
                    q.append(nb)
        return len(comp)

    for node in undirected:
        if node not in seen_comp:
            size = bfs_component(node)
            if size > max_comp:
                max_comp = size

    cycles.sort(key=len, reverse=True)
    return len(cycles), cycles[0] if cycles else [], cycles[:max_report], max_comp


def print_cycle_report(all_agents):
    """Print a cycle detection report."""
    cycle_count, largest, examples, max_comp = find_cycles(all_agents)
    print(f"\n{BOLD}Dependency Cycle Detection{RESET}")
    print(f"  Total agents:         {len(all_agents)}")
    print(f"  Cycle count:          {RED}{cycle_count}{RESET}")
    print(f"  Largest cycle length: {len(largest)}")
    print(f"  Largest component:    {max_comp} agents")
    if cycle_count > 0:
        print(f"\n  {BOLD}Largest cycle:{RESET}")
        chain = " -> ".join(largest[:12])
        print(f"  {chain}")
        if len(largest) > 12:
            print(f"  ... ({len(largest) - 12} more)")
        print(f"\n  {BOLD}Sample cycles:{RESET}")
        for _, cycle in enumerate(examples[:5]):
            agents_in = len(cycle)
            cats = {aid.split("-")[0] for aid in cycle}
            chain = " -> ".join(cycle[:5])
            print(f"  [{agents_in} agents, {len(cats)} categories] {chain}...")
    if cycle_count > 100:
        print(f"\n  {RED}High cycle count - consider breaking weak dependency links{RESET}")


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
    pct = agents_with_deps / total * 100 if total else 0
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


def compute_cross_stats(all_agents):
    """Compute cross-category dependency coverage per category.

    Returns dict: category → {total, with_deps, with_cross, cross_deps, ...}
    """
    agent_deps = {}
    for _cat, _rel, filepath in discover_agents():
        content = filepath.read_text(encoding="utf-8")
        fm = get_frontmatter_text(content)
        deps = get_list_field("depends_on", fm)
        agent_deps[filepath.stem] = {
            "category": filepath.parent.name,
            "deps": deps,
        }

    cats = defaultdict(lambda: {
        "total": 0, "with_deps": 0, "with_cross": 0, "cross_deps": 0,
        "siloed": [], "cross_agents": [],
    })

    for aid, info in agent_deps.items():
        cat = info["category"]
        cats[cat]["total"] += 1
        if info["deps"]:
            cats[cat]["with_deps"] += 1
            has_cross = False
            for dep_id in info["deps"]:
                if dep_id in all_agents:
                    if all_agents[dep_id]["category"] != cat:
                        cats[cat]["cross_deps"] += 1
                        has_cross = True
            if has_cross:
                cats[cat]["with_cross"] += 1
                cats[cat]["cross_agents"].append(aid)
            else:
                cats[cat]["siloed"].append(aid)
        else:
            cats[cat]["siloed"].append(aid)

    return dict(cats)


def print_cross_stats(stats):
    """Print cross-category dependency coverage report."""
    total_agents = sum(s["total"] for s in stats.values())
    total_with_cross = sum(s["with_cross"] for s in stats.values())

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Cross-Category Dependency Coverage{RESET}")
    print(f"  {total_with_cross}/{total_agents} agents ({total_with_cross / max(1, total_agents) * 100:.1f}%) have cross-category deps")
    print(f"{BOLD}{'='*60}{RESET}\n")

    ranked = sorted(stats.items(), key=lambda x: (
        x[1]["with_cross"] / max(1, x[1]["total"]), -x[1]["total"]
    ))

    print(f"{BOLD}Categories by Cross-Category Coverage:{RESET}")
    print(f"  {'Category':<28} {'Total':>5} {'Cross':>5} {'Coverage':>8}  Status")
    print(f"  {'-'*28} {'-'*5} {'-'*5} {'-'*8}  {'-'*12}")
    for cat, s in ranked:
        pct = s["with_cross"] / max(1, s["total"]) * 100
        if pct == 0:
            color, status = RED, "SILO"
        elif pct < 5:
            color, status = YELLOW, "NEAR-SILO"
        elif pct < 15:
            color, status = RESET, "emerging"
        else:
            color, status = GREEN, "connected"
        print(f"  {cat:<28} {s['total']:>5} {s['with_cross']:>5} {color}{pct:>7.1f}%{RESET}  {status}")

    siloed = [(cat, s) for cat, s in ranked if s["with_cross"] == 0 and s["total"] >= 3]
    if siloed:
        print(f"\n{BOLD}{RED}Completely Siloed (0% cross-category):{RESET}")
        for cat, s in siloed:
            print(f"  {RED}{cat}{RESET}: {s['total']} agents, zero cross-category deps")


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
    parser.add_argument("--cross-stats", action="store_true",
                        help="Cross-category dependency coverage per category")
    parser.add_argument("--agent", "-a",
                        help="Filter to specific agent")
    parser.add_argument("--category", "-c",
                        help="Filter to specific category")
    parser.add_argument("--min-confidence", type=float, default=0.5,
                        help="Minimum confidence for suggestions (default: 0.5)")
    parser.add_argument("--apply", action="store_true",
                        help="Write suggested cross-category deps to agent files")
    parser.add_argument("--cycles", action="store_true",
                        help="Detect dependency cycles in the graph")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable JSON output")
    args = parser.parse_args()

    # Build index (shared across all modes)
    all_agents = build_agent_index(category_filter=args.category)

    # Default to --report if no action specified
    if not any([args.suggest, args.validate, args.orphans, args.cross_stats, args.apply, args.cycles]):
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

    # --cycles mode
    if args.cycles:
        print_cycle_report(all_agents)
        return

    # --cross-stats mode
    if args.cross_stats:
        stats = compute_cross_stats(all_agents)
        if args.json:
            json.dump(stats, sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
        else:
            print_cross_stats(stats)
        return

    # --apply mode: write suggested cross-category deps to agent files
    if args.apply:
        term_index = build_term_index(all_agents)
        suggestions = suggest_dependencies(all_agents, term_index,
                                           min_confidence=args.min_confidence)
        applied = 0
        for _cat, _rel, filepath in discover_agents(category_filter=args.category):
            agent_id = filepath.stem
            if agent_id not in suggestions:
                continue
            deps = suggestions[agent_id]
            # Only apply cross-category deps with confidence >= min_confidence
            cross_deps = [(tid, c) for tid, c, _ in deps
                          if tid in all_agents
                          and all_agents[tid]["category"] != all_agents[agent_id]["category"]
                          and c >= args.min_confidence]
            if not cross_deps:
                continue

            content = filepath.read_text(encoding="utf-8")
            fm = get_frontmatter_text(content)
            existing = set(get_list_field("depends_on", fm))
            new_deps = [tid for tid, _ in cross_deps if tid not in existing]
            if not new_deps:
                continue

            # Take up to 3 highest-confidence new cross-category deps
            new_deps = new_deps[:3]
            all_updated = sorted(existing | set(new_deps))

            # Rebuild depends_on block at YAML root level
            dep_lines = ["depends_on:"]
            for dep in all_updated:
                dep_lines.append(f"  - {dep}")

            # Replace or insert depends_on in frontmatter
            fm_lines = fm.split("\n")
            new_fm_lines = []
            in_deps = False
            deps_written = False
            for line in fm_lines:
                stripped = line.strip()
                if stripped.startswith("depends_on:"):
                    in_deps = True
                    if not deps_written:
                        new_fm_lines.extend(dep_lines)
                        deps_written = True
                    continue
                if in_deps and re.match(r"^\s+- ", line):
                    continue
                if in_deps and not re.match(r"^\s+- ", line):
                    in_deps = False
                new_fm_lines.append(line)

            if not deps_written:
                # Insert before closing --- of frontmatter
                new_fm_lines.extend(dep_lines)

            new_fm = "\n".join(new_fm_lines)
            body = get_body(content)
            new_content = f"---\n{new_fm}\n---{body}"
            tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
            tmp_path.write_text(new_content, encoding="utf-8", newline="\n")
            tmp_path.replace(filepath)
            applied += 1
            print(f"  {GREEN}+{len(new_deps)}{RESET} cross-category deps added to {agent_id} "
                  f"({', '.join(new_deps[:2])}{'...' if len(new_deps) > 2 else ''})")

        print(f"\n  Applied cross-category deps to {applied} agents")
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
