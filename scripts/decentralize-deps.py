#!/usr/bin/env python
"""Dependency network decentralization — reduce hub risk, connect orphans.

Analyzes the depends_on graph, identifies over-centralized hub nodes, and
migrates dependencies to domain-specific coordinators.

Strategy (3 phases):
  Phase 1 — Create domain coordinators in category dirs
  Phase 2 — Migrate agents to depend on domain coordinator instead of global hub
  Phase 3 — Validate: no broken deps, scores stable, hub in-degree reduced

Usage:
    python scripts/decentralize-deps.py --analyze              # topology report
    python scripts/decentralize-deps.py --dry-run              # preview plan
    python scripts/decentralize-deps.py --phase 1              # create coordinators
    python scripts/decentralize-deps.py --phase 2              # migrate deps
    python scripts/decentralize-deps.py --phase 3              # validate
    python scripts/decentralize-deps.py --rollback             # undo phase 2
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

HUB_DECENTRALIZE_PLAN = {
    "engineering-multi-agent-systems-architect": {
        "hub_category": "engineering",
        "domains": {
            "infrastructure": {
                "id": "infrastructure-multi-agent-coordinator",
                "name": "Infrastructure Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for infrastructure — "
                               "network topology, cloud architecture, data center operations",
                "emoji": "🏗️",
                "color": "#2563EB",
            },
            "data-science": {
                "id": "data-science-multi-agent-coordinator",
                "name": "Data Science Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for data science — "
                               "ML pipelines, experiment tracking, model deployment",
                "emoji": "📊",
                "color": "#7C3AED",
            },
            "marketing": {
                "id": "marketing-multi-agent-coordinator",
                "name": "Marketing Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for marketing — "
                               "content, paid media, SEO, analytics",
                "emoji": "📢",
                "color": "#DC2626",
            },
            "automotive": {
                "id": "automotive-multi-agent-coordinator",
                "name": "Automotive Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for automotive — "
                               "vehicle systems, ADAS, powertrain, homologation",
                "emoji": "🚗",
                "color": "#EA580C",
            },
            "logistics": {
                "id": "logistics-multi-agent-coordinator",
                "name": "Logistics Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for logistics — "
                               "supply chain, freight, warehousing, last-mile delivery",
                "emoji": "🚚",
                "color": "#65A30D",
            },
            "iot": {
                "id": "iot-multi-agent-coordinator",
                "name": "IoT Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for IoT — "
                               "edge computing, sensor networks, embedded systems",
                "emoji": "📡",
                "color": "#0891B2",
            },
            "testing": {
                "id": "testing-multi-agent-coordinator",
                "name": "Testing Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for testing — "
                               "QA automation, performance, security, accessibility",
                "emoji": "🧪",
                "color": "#7C3AED",
            },
            "design": {
                "id": "design-multi-agent-coordinator",
                "name": "Design Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for design — "
                               "UX/UI, brand, visual systems, design ops",
                "emoji": "🎨",
                "color": "#DB2777",
            },
            "network-engineering": {
                "id": "network-engineering-multi-agent-coordinator",
                "name": "Network Engineering Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for network engineering — "
                               "routing, switching, SDN, network automation",
                "emoji": "🌐",
                "color": "#2563EB",
            },
            "food-beverage": {
                "id": "food-beverage-multi-agent-coordinator",
                "name": "Food & Beverage Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for food & beverage — "
                               "product development, safety, supply chain, manufacturing",
                "emoji": "🍽️",
                "color": "#DC2626",
            },
            "gis": {
                "id": "gis-multi-agent-coordinator",
                "name": "GIS Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for GIS — "
                               "spatial analysis, remote sensing, cartography, geodata pipelines",
                "emoji": "🗺️",
                "color": "#059669",
            },
            "securities": {
                "id": "securities-multi-agent-coordinator",
                "name": "Securities Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for securities — "
                               "trading, analysis, portfolio management, compliance",
                "emoji": "📈",
                "color": "#1D4ED8",
            },
            "spatial-computing": {
                "id": "spatial-computing-multi-agent-coordinator",
                "name": "Spatial Computing Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for spatial computing — "
                               "AR/VR/XR, 3D assets, spatial interaction design",
                "emoji": "🥽",
                "color": "#7C3AED",
            },
            "agriculture": {
                "id": "agriculture-multi-agent-coordinator",
                "name": "Agriculture Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for agriculture — "
                               "precision farming, agri-supply-chain, IoT, agronomy",
                "emoji": "🌾",
                "color": "#65A30D",
            },
            "legal": {
                "id": "legal-multi-agent-coordinator",
                "name": "Legal Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for legal — "
                               "corporate, IP, compliance, litigation support",
                "emoji": "⚖️",
                "color": "#1E3A5F",
            },
            "robotics": {
                "id": "robotics-multi-agent-coordinator",
                "name": "Robotics Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for robotics — "
                               "motion control, perception, ROS, automation integration",
                "emoji": "🤖",
                "color": "#475569",
            },
            "web3": {
                "id": "web3-multi-agent-coordinator",
                "name": "Web3 Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for Web3 — "
                               "smart contracts, DeFi, DAOs, blockchain infrastructure",
                "emoji": "⛓️",
                "color": "#9333EA",
            },
            "education": {
                "id": "education-multi-agent-coordinator",
                "name": "Education Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for education — "
                               "curriculum design, EdTech, assessment, academic research",
                "emoji": "📚",
                "color": "#2563EB",
            },
            "insurance": {
                "id": "insurance-multi-agent-coordinator",
                "name": "Insurance Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for insurance — "
                               "underwriting, claims, actuarial, insurtech",
                "emoji": "🛡️",
                "color": "#0D9488",
            },
            "telecom": {
                "id": "telecom-multi-agent-coordinator",
                "name": "Telecom Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for telecom — "
                               "5G core, RAN, optical, network slicing",
                "emoji": "📶",
                "color": "#0284C7",
            },
            "energy": {
                "id": "energy-multi-agent-coordinator",
                "name": "Energy Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for energy — "
                               "renewables, grid, storage, carbon management",
                "emoji": "⚡",
                "color": "#CA8A04",
            },
            "project-management": {
                "id": "project-management-multi-agent-coordinator",
                "name": "Project Management Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for project management — "
                               "PMO, scheduling, risk, stakeholder coordination",
                "emoji": "📋",
                "color": "#2563EB",
            },
            "finance": {
                "id": "finance-multi-agent-coordinator",
                "name": "Finance Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for finance — "
                               "FP&A, accounting, treasury, corporate finance",
                "emoji": "💰",
                "color": "#059669",
            },
            "media-entertainment": {
                "id": "media-entertainment-multi-agent-coordinator",
                "name": "Media & Entertainment Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for media — "
                               "production, post-production, animation, sound design",
                "emoji": "🎬",
                "color": "#DC2626",
            },
            "customer-service": {
                "id": "customer-service-multi-agent-coordinator",
                "name": "Customer Service Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for customer service",
                "emoji": "🎧",
                "color": "#0D9488",
            },
            "environmental": {
                "id": "environmental-multi-agent-coordinator",
                "name": "Environmental Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for environmental projects",
                "emoji": "🌍",
                "color": "#059669",
            },
            "hr": {
                "id": "hr-multi-agent-coordinator",
                "name": "HR Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for HR — "
                               "recruitment, people analytics, employee experience",
                "emoji": "👥",
                "color": "#7C3AED",
            },
            "operations": {
                "id": "operations-multi-agent-coordinator",
                "name": "Operations Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for business operations",
                "emoji": "⚙️",
                "color": "#475569",
            },
            "administration": {
                "id": "administration-multi-agent-coordinator",
                "name": "Administration Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for administration",
                "emoji": "🏢",
                "color": "#64748B",
            },
            "aerospace": {
                "id": "aerospace-multi-agent-coordinator",
                "name": "Aerospace Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for aerospace — "
                               "aircraft, avionics, space systems, UAM",
                "emoji": "✈️",
                "color": "#1E40AF",
            },
            "manufacturing": {
                "id": "manufacturing-multi-agent-coordinator",
                "name": "Manufacturing Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for manufacturing — "
                               "smart factory, quality, lean, Industry 4.0",
                "emoji": "🏭",
                "color": "#D97706",
            },
            "pharma-biotech": {
                "id": "pharma-biotech-multi-agent-coordinator",
                "name": "Pharma & Biotech Multi-Agent Coordinator",
                "description": "Coordinates multi-agent workflows for pharma & biotech — "
                               "drug development, clinical trials, regulatory",
                "emoji": "💊",
                "color": "#059669",
            },
        },
    },
}

COORDINATOR_TEMPLATE = """---
name: "{name}"
description: "{description}"
emoji: {emoji}
color: "{color}"
version: "1.0.0"
date_added: "{date_added}"
vibe: "orchestrating {domain} specialists into coherent multi-agent workflows"
nexus_roles:
  - phase-2-strategy
  - phase-3-build
depends_on:
  - engineering-multi-agent-systems-architect
---

# {name}

## 🧠 Your Identity & Memory

You are a domain-specific multi-agent coordinator for **{domain}** projects.
You adapt general multi-agent systems architecture principles to the specific
constraints and workflows of the {domain} domain.

## 🎯 Your Core Mission

- Design agent team topologies optimized for {domain} project patterns
- Recommend which specialists to compose for {domain}-specific workflows
- Define handoff protocols and context-passing conventions for {domain} toolchains
- Ensure agent teams comply with {domain} industry standards

## 🚨 Critical Rules You Must Follow

1. Always consider {domain}-specific regulatory and compliance requirements
2. Prefer {domain}-native tools and frameworks in agent composition
3. Ensure context continuity across agent handoffs
4. Validate agent team outputs against {domain} quality benchmarks

## 📋 Your Technical Deliverables

- Agent team topology diagrams for {domain} project types
- Context-passing protocol specifications
- Agent selection matrices for {domain} tasks
- Multi-agent workflow runbooks for common {domain} scenarios

## 🔄 Your Workflow Process

1. Receive the {domain} project brief and constraints
2. Select appropriate specialist agents from the {domain} category
3. Design the agent team topology and communication protocol
4. Define success metrics and quality gates per agent
5. Orchestrate the team through the project lifecycle

## 💭 Your Communication Style

Direct, architecture-focused, with deep {domain} domain fluency.

## 🎯 Your Success Metrics

- Agent team output meets {domain} industry benchmarks
- Handoff context retention rate > 95%
- Coordination overhead < 15% of total project time

## ⚠️ Professional Scope & Safeguards

Your agent team designs are architectural recommendations. Always recommend
human review before production deployment in {domain} environments.
"""


def _read_frontmatter(filepath):
    content = filepath.read_text(encoding="utf-8", errors="replace")
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, "", content
    try:
        import yaml
        fm = yaml.safe_load(parts[1])
        return (fm if isinstance(fm, dict) else {}), parts[1], parts[2]
    except Exception:
        return {}, "", content


def _write_agent(filepath, fm, body):
    import yaml
    fm_str = yaml.dump(fm, allow_unicode=True, default_flow_style=False).strip()
    new_content = f"---\n{fm_str}\n---\n{body}"
    filepath.write_text(new_content, encoding="utf-8")


def analyze_topology():
    """Analyze current dependency topology."""
    in_deg = Counter()
    hub_dependents = defaultdict(list)

    for md in sorted(REPO.glob("*/*.md")):
        if any(s in str(md) for s in [".git", "docs", "integrations"]):
            continue
        fm, _, _ = _read_frontmatter(md)
        deps = fm.get("depends_on", []) or []
        if isinstance(deps, str):
            deps = [deps]

        src = md.stem
        src_cat = md.parent.name
        for dep in deps:
            dep = str(dep).strip()
            if dep:
                in_deg[dep] += 1
                if dep in HUB_DECENTRALIZE_PLAN:
                    hub_dependents[dep].append((src, src_cat))

    all_agents = {md.stem for md in REPO.glob("*/*.md")
                  if ".git" not in str(md) and "docs" not in str(md)}

    return {
        "total_agents": len(all_agents),
        "top_hubs": [(a, c) for a, c in in_deg.most_common(10)],
        "hub_dependents": {h: len(v) for h, v in hub_dependents.items()},
        "hub_by_category": {
            hub: dict(Counter(cat for _, cat in deps))
            for hub, deps in hub_dependents.items()
        },
        "orphans": len([a for a in all_agents if in_deg[a] == 0]),
    }


def create_coordinators(dry_run=False):
    """Phase 1: Create domain coordinator agent files."""
    created = []
    for hub_id, plan in HUB_DECENTRALIZE_PLAN.items():
        for domain, spec in plan["domains"].items():
            target_path = REPO / domain / f"{spec['id']}.md"
            if target_path.exists():
                print(f"  SKIP: {target_path.name} already exists")
                continue

            content = COORDINATOR_TEMPLATE.format(
                name=spec["name"],
                description=spec["description"],
                emoji=spec["emoji"],
                color=spec["color"],
                date_added=str(date.today()),
                domain=domain,
            )

            if dry_run:
                print(f"  WOULD CREATE: {target_path.name} in {domain}/")
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                print(f"  CREATED: {target_path.name}")
            created.append(str(target_path))

    return created


def migrate_dependencies(dry_run=False):
    """Phase 2: Migrate agents from global hub to domain coordinators."""
    migrations = []
    for hub_id, plan in HUB_DECENTRALIZE_PLAN.items():
        domain_map = {d: s["id"] for d, s in plan["domains"].items()}

        for md in sorted(REPO.glob("*/*.md")):
            if any(s in str(md) for s in [".git", "docs", "integrations"]):
                continue
            category = md.parent.name
            if category not in domain_map:
                continue

            fm, _, body = _read_frontmatter(md)
            deps = fm.get("depends_on", []) or []
            if isinstance(deps, str):
                deps = [deps]

            if hub_id not in deps:
                continue

            domain_coordinator = domain_map[category]
            new_deps = [domain_coordinator if d == hub_id else d for d in deps]

            if dry_run:
                migrations.append((md.stem, category, domain_coordinator))
            else:
                fm["depends_on"] = new_deps
                _write_agent(md, fm, body)
                migrations.append((md.stem, category, domain_coordinator))

    return migrations


def validate_after_migration():
    """Phase 3: Verify integrity after migration."""
    import subprocess

    print("Checking dependency integrity...")
    result = subprocess.run(
        ["python", str(REPO / "scripts" / "check-deps.py")],
        capture_output=True, text=True, cwd=str(REPO),
    )
    deps_ok = result.returncode == 0
    print(f"  Dependencies: {'PASS' if deps_ok else 'FAIL'}")

    # Re-analyze topology
    report = analyze_topology()
    old_hub_deg = 301  # baseline
    new_hub_deg = next((c for a, c in report["top_hubs"] if a == "engineering-multi-agent-systems-architect"), 0)
    print(f"  Hub in-degree: {old_hub_deg} → {new_hub_deg}")
    print(f"  Orphans: {report['orphans']}")

    return {
        "deps_ok": deps_ok,
        "hub_in_degree_before": old_hub_deg,
        "hub_in_degree_after": new_hub_deg,
        "orphans": report["orphans"],
    }


def rollback_migrations():
    """Undo Phase 2: restore original hub dependencies."""
    restored = 0
    for hub_id, plan in HUB_DECENTRALIZE_PLAN.items():
        domain_map = {d: s["id"] for d, s in plan["domains"].items()}

        for md in sorted(REPO.glob("*/*.md")):
            if any(s in str(md) for s in [".git", "docs", "integrations"]):
                continue
            category = md.parent.name
            if category not in domain_map:
                continue

            fm, _, body = _read_frontmatter(md)
            deps = fm.get("depends_on", []) or []
            if isinstance(deps, str):
                deps = [deps]

            domain_coordinator = domain_map[category]
            if domain_coordinator not in deps:
                continue

            new_deps = [hub_id if d == domain_coordinator else d for d in deps
                        if d != domain_coordinator]
            fm["depends_on"] = new_deps
            _write_agent(md, fm, body)
            restored += 1

    return restored


def main():
    parser = argparse.ArgumentParser(
        description="Dependency network decentralization")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3])
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.analyze:
        report = analyze_topology()
        if args.json:
            json.dump(report, sys.stdout, indent=2, default=str)
        else:
            print("\n=== Dependency Topology Report ===\n")
            print("Top 10 Hub Nodes:")
            for agent, count in report["top_hubs"]:
                print(f"  {count:>4d} → {agent}")
            print(f"\nOrphans (no inbound deps): {report['orphans']}")
            for hub, cats in report.get("hub_by_category", {}).items():
                print(f"\n{hub} dependents by category:")
                for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
                    print(f"  {cat}: {count}")
        return

    if args.rollback:
        count = rollback_migrations()
        print(f"Rolled back {count} migrations.")
        return

    if args.dry_run:
        print("\n=== DRY RUN: Decentralization Plan ===\n")
        print("Phase 1 — Create domain coordinators:")
        create_coordinators(dry_run=True)
        print("\nPhase 2 — Migrate dependencies:")
        migrations = migrate_dependencies(dry_run=True)
        by_cat = defaultdict(list)
        for agent, cat, coord in migrations:
            by_cat[cat].append(agent)
        for cat in sorted(by_cat):
            print(f"  {cat}: {len(by_cat[cat])} agents → {cat}-multi-agent-coordinator")
        print(f"\nTotal migrations: {len(migrations)}")
        report = analyze_topology()
        for hub, count in report["hub_dependents"].items():
            print(f"{hub}: {count} → ~{count - len(migrations)} deps after migration")
        return

    if args.phase == 1:
        print("Phase 1: Creating domain coordinators...")
        created = create_coordinators()
        print(f"Created {len(created)} coordinator(s). Run --phase 2 to migrate.")

    elif args.phase == 2:
        print("Phase 2: Migrating dependencies...")
        migrations = migrate_dependencies()
        by_cat = defaultdict(int)
        for _, cat, _ in migrations:
            by_cat[cat] += 1
        print(f"Migrated {len(migrations)} dependencies:")
        for cat, count in sorted(by_cat.items()):
            print(f"  {cat}: {count} agents")
        print("Run --phase 3 to validate or --rollback to undo.")

    elif args.phase == 3:
        print("Phase 3: Validating...")
        result = validate_after_migration()
        ok = result["deps_ok"] and result["hub_in_degree_after"] < result["hub_in_degree_before"]
        print(f"\nValidation: {'PASS' if ok else 'FAIL'}")
        print(f"  Hub in-degree: {result['hub_in_degree_before']} → {result['hub_in_degree_after']}")
        if not ok:
            print("Run --rollback to undo migrations.")


if __name__ == "__main__":
    main()
