#!/usr/bin/env python3
"""Generate model routing configuration for oh-my-claudecode.

Maps agency agent quality scores to OMC's 3-tier model routing:
  A-grade (>=12.5) → opus   (complex, high-stakes tasks)
  B-grade (>=10.0) → sonnet (standard implementation)
  C/D-grade (<10.0) → haiku (simple or draft agents)

Usage:
    python scripts/generate-omc-model-routing.py                # full routing map
    python scripts/generate-omc-model-routing.py --summary      # tier distribution only
    python scripts/generate-omc-model-routing.py --category engineering
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from _shared import REPO, atomic_write

INDEX_PATH = REPO / "AGENTS.json"
SCORE_SCRIPT = REPO / "scripts" / "score-agents.py"
OUT_PATH = REPO / "integrations" / "oh-my-claudecode" / "model-routing.json"

TIER_CUTOFFS = {"opus": 12.5, "sonnet": 10.0, "haiku": 0.0}
TIER_DESC = {
    "opus": "Complex reasoning, architecture, high-stakes decisions",
    "sonnet": "Standard implementation, debugging, testing",
    "haiku": "Simple lookups, fast responses, draft agents",
}
RISK_TIER_WEIGHT = {"critical": 1.5, "high": 1.0, "general": 0.0}


def load_agents() -> list[dict[str, Any]]:
    with open(INDEX_PATH, encoding="utf-8") as f:
        return cast(list[dict[str, Any]], json.load(f)["agents"])


def compute_scores() -> tuple[dict[str, float], dict[str, str]]:
    import subprocess

    result = subprocess.run(
        [sys.executable, str(SCORE_SCRIPT), "--json"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    if result.returncode != 0:
        print(f"Scoring failed: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result.stdout)
    scores: dict[str, float] = {}
    risks: dict[str, str] = {}
    for entry in data.get("agents", []):
        aid = entry["id"]
        scores[aid] = entry.get("total", 0.0)
        risks[aid] = entry.get("risk_tier", "general")
    return scores, risks


def assign_tier(score: float, risk: str) -> str:
    adjusted = score + RISK_TIER_WEIGHT.get(risk, 0.0)
    if adjusted >= TIER_CUTOFFS["opus"] or score >= TIER_CUTOFFS["opus"]:
        return "opus"
    if adjusted >= TIER_CUTOFFS["sonnet"] or score >= TIER_CUTOFFS["sonnet"]:
        return "sonnet"
    return "haiku"


def generate_routing(scores: dict[str, float], risks: dict[str, str],
                     agents: list[dict]) -> dict:
    routing: dict[str, dict] = {}
    for a in agents:
        aid = a["id"]
        score = scores.get(aid, 0.0)
        risk = risks.get(aid, "general")
        tier = assign_tier(score, risk)
        routing[aid] = {
            "tier": tier,
            "score": round(score, 1),
            "risk": risk,
            "category": a["category"],
            "description": TIER_DESC[tier],
        }
    return routing


def show_summary(routing: dict) -> None:
    counts: dict[str, int] = {}
    for v in routing.values():
        counts[v["tier"]] = counts.get(v["tier"], 0) + 1

    total = len(routing)
    print(f"Model Routing Summary ({total} agents)")
    for tier in ("opus", "sonnet", "haiku"):
        c = counts.get(tier, 0)
        pct = c * 100 // total if total else 0
        bar = "█" * (c * 40 // total) if total else ""
        print(f"  {tier:<8} {c:>5} ({pct:>3}%) {bar}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate model routing for oh-my-claudecode")
    parser.add_argument("--summary", action="store_true", help="Show distribution only")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--output", type=Path, default=OUT_PATH,
                        help=f"Output path (default: {OUT_PATH})")
    args = parser.parse_args()

    agents = load_agents()
    if args.category:
        agents = [a for a in agents if a["category"] == args.category]

    print(f"Scoring {len(agents)} agents...")
    scores, risks = compute_scores()
    routing = generate_routing(scores, risks, agents)

    show_summary(routing)

    if not args.summary:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(args.output,
                     json.dumps(routing, ensure_ascii=False, indent=2))
        print(f"\nRouting written to: {args.output}")


if __name__ == "__main__":
    main()
