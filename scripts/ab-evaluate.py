#!/usr/bin/env python
"""Batch A/B evaluation: scans agent content for domain signal patterns.

Non-interactive counterpart to ab-test.py. Evaluates matching test cases
by scanning agent .md files for criterion-specific keyword patterns.

Usage:
    python scripts/ab-evaluate.py                    # evaluate all test cases
    python scripts/ab-evaluate.py --agent <id>       # evaluate specific agent
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone

UTC = timezone.utc
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TEST_DIR = REPO / "tests" / "ab-cases"
RESULTS_DIR = REPO / "tests" / "ab-results"

CRITERIA_PATTERNS = {
    "named_techniques": [
        r"virtualiz", r"code.split", r"lazy.load", r"tree.shak",
        r"bundle.optimiz", r"cache", r"CDN", r"compression", r"image.optim",
    ],
    "actionable_steps": [
        r"^\s*(?:[-*]|\d+[.)])\s+\w",
        r"Step\s+\d",
        r"(?:you must|you should|always|never|ensure|verify|validate)",
    ],
    "metric_targets": [
        r"LCP", r"FID", r"CLS", r"INP", r"FCP", r"TTI", r"TBT",
        r"Core.Web.Vital", r"Lighthouse", r"<\d+\.?\d*\s*s", r"<\d+\s*ms",
    ],
    "code_examples": [r"```", r"`[^`]+`"],
    "named_standards": [
        r"SOC.2", r"NIST", r"ISO.27001", r"PCI", r"GDPR",
        r"HIPAA", r"FedRAMP", r"CIS", r"CCPA",
    ],
    "prioritized_steps": [
        r"priorit", r"severity", r"critical", r"high.risk", r"P0", r"P1",
    ],
    "aws_services": [
        r"WAF", r"Shield", r"GuardDuty", r"Security.Hub", r"Inspector",
        r"AWS.Config", r"CloudTrail", r"IAM", r"KMS", r"Macie",
    ],
    "iam_guidance": [
        r"IAM", r"least.privilege", r"policy", r"role", r"permission",
    ],
    "architecture_components": [
        r"feature.store", r"model.registr", r"feature.engin",
        r"serving", r"training.pipeline", r"orchestrat",
    ],
    "latency_design": [
        r"<\d+.ms", r"latency", r"throughput", r"real.time",
        r"batch", r"streaming", r"cache", r"pre.comput",
    ],
    "mlops_tools": [
        r"MLflow", r"Kubeflow", r"Feast", r"Tecton", r"SageMaker",
        r"Vertex.AI", r"Seldon", r"BentoML", r"TFX", r"Ray",
    ],
    "drift_monitoring": [
        r"drift", r"data.drift", r"concept.drift", r"model.decay",
        r"monitor", r"Evidently", r"WhyLogs", r"Great.Expectations",
    ],
    "evm_interpretation": [
        r"SPI", r"CPI", r"EVM", r"Earned.Value", r"Schedule.Variance",
        r"Cost.Variance", r"TCPI", r"BAC", r"EAC",
    ],
    "risk_response_types": [
        r"mitigate", r"transfer", r"avoid", r"accept",
        r"escalat", r"contingen", r"fallback",
    ],
    "quantified_advice": [
        r"\d+%", r"\d+\s*(?:week|day|month|hour|sprint)s?",
        r"\$\d+", r"\d+\s*FTE",
    ],
    "stakeholder_guidance": [
        r"stakeholder", r"sponsor", r"communicat",
        r"executive", r"client", r"steering",
    ],
    "wcag_references": [
        r"WCAG", r"success.criteri", r"SC\s*\d",
        r"guideline\s*\d", r"level\s*A",
    ],
    "aria_patterns": [
        r"aria-", r'role="', r"aria\s", r"role\s",
    ],
    "assistive_tech": [
        r"screen.reader", r"VoiceOver", r"NVDA", r"JAWS",
        r"TalkBack", r"assistive.tech", r"accessibility.test",
    ],
    "prioritized_fixes": [
        r"priority", r"severity", r"critical", r"P0",
        r"P1", r"must.fix", r"should.fix", r"blocker",
    ],
}


def evaluate_agent(agent_id, tc):
    """Evaluate one agent against one test case by scanning content."""
    agent_path = REPO / tc["domain"] / f"{agent_id}.md"
    if not agent_path.exists():
        candidates = sorted((REPO / tc["domain"]).rglob(f"{agent_id}.md"))
        agent_path = candidates[0] if candidates else agent_path
    if not agent_path.exists():
        return None
    content = agent_path.read_text(encoding="utf-8")
    result = {"id": tc["id"], "title": tc["title"], "criteria": {}}
    for crit_name, crit_def in tc["eval_criteria"].items():
        mn = crit_def["min"]
        patterns = CRITERIA_PATTERNS.get(crit_name, [])
        count = 0
        for pat in patterns:
            try:
                count += len(re.findall(pat, content, re.IGNORECASE | re.MULTILINE))
            except re.error:
                continue
        met = count >= mn
        result["criteria"][crit_name] = {
            "required": mn, "actual": count, "met": met,
        }
    total = len(result["criteria"])
    met_count = sum(1 for c in result["criteria"].values() if c["met"])
    pct = met_count / total * 100 if total > 0 else 0
    grade = "A" if pct >= 80 else "B" if pct >= 60 else "C" if pct >= 40 else "D"
    return {
        "agent_id": agent_id,
        "run_at": datetime.now(UTC).isoformat(),
        "test_cases": [result],
        "summary": {
            "total_criteria": total, "met_criteria": met_count,
            "grade": grade, "score_pct": round(pct, 1),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Batch A/B evaluation for agents")
    parser.add_argument("--agent", help="Evaluate a specific agent only")
    args = parser.parse_args()
    if not TEST_DIR.exists():
        print("No test cases. Run: python scripts/ab-test.py --init", file=sys.stderr)
        sys.exit(1)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    test_cases = []
    for p in sorted(TEST_DIR.glob("*.json")):
        tc = json.loads(p.read_text(encoding="utf-8"))
        if args.agent and tc["agent"] != args.agent:
            continue
        test_cases.append(tc)
    if not test_cases:
        print(f"No test cases for agent '{args.agent}'", file=sys.stderr)
        sys.exit(1)
    all_results = []
    for tc in test_cases:
        agent_id = tc["agent"]
        print(f"\n{'='*55}")
        print(f"Evaluating: {agent_id} against {tc['id']}")
        print(f"{'='*55}")
        result = evaluate_agent(agent_id, tc)
        if result is None:
            print("  SKIP: agent file not found")
            continue
        s = result["summary"]
        print(f"  Result: {s['met_criteria']}/{s['total_criteria']} criteria "
              f"({s['score_pct']}%) — Grade {s['grade']}")
        for cn, cv in result["test_cases"][0]["criteria"].items():
            status = "PASS" if cv["met"] else "FAIL"
            print(f"    [{status}] {cn}: found={cv['actual']} need>={cv['required']}")
        all_results.append(result)
        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        rp = RESULTS_DIR / f"{agent_id}-{ts}.json"
        rp.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if all_results:
        print(f"\n{'='*55}")
        print(f"SUMMARY: {len(all_results)} agents evaluated")
        print(f"{'='*55}")
        grades = {"A": 0, "B": 0, "C": 0, "D": 0}
        for r in all_results:
            g = r["summary"]["grade"]
            grades[g] += 1
            print(f"  {r['agent_id']:<40} {r['summary']['score_pct']:>5.1f}%  {g}")
        avg = sum(r["summary"]["score_pct"] for r in all_results) / len(all_results)
        print(f"\n  Average: {avg:.1f}%")
        for g in ["A", "B", "C", "D"]:
            if grades[g]:
                print(f"  Grade {g}: {grades[g]} agents")


if __name__ == "__main__":
    main()
