#!/usr/bin/env python
"""Agent effectiveness A/B testing framework.

Addresses the core criticism from the 5-expert audit: "工程纪律A，科学思维F —
1,085 tests pass but none test whether agents actually improve LLM output quality."

Usage:
    python scripts/ab-test.py --init                    # create test suite scaffold
    python scripts/ab-test.py --list                    # list defined test cases
    python scripts/ab-test.py --run engineering-frontend-developer  # run A/B eval
    python scripts/ab-test.py --report                  # summary report
    python scripts/ab-test.py --report --json           # machine-readable results

Test structure:
    Each test case defines a domain task prompt and evaluation criteria.
    The framework provides an interactive evaluation template — a human evaluator
    (or automated LLM judge) compares the agent-guided response against criteria.
    This keeps the framework provider-agnostic and cost-free.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc

REPO = Path(__file__).resolve().parent.parent
TEST_DIR = REPO / "tests" / "ab-cases"
RESULTS_DIR = REPO / "tests" / "ab-results"

DEFAULT_TEST_CASES = {
    "tc-001-frontend-perf": {
        "title": "Frontend Performance Audit",
        "domain": "engineering",
        "agent": "engineering-frontend-developer",
        "prompt": "A React e-commerce product listing page takes 8 seconds to load on mobile. "
                 "The page renders 2,000 product cards with images. Audit the performance "
                 "issues and provide a concrete optimization plan with specific techniques.",
        "eval_criteria": {
            "named_techniques": {"min": 3, "description": "Named optimization techniques (virtualization, code splitting, etc.)"},
            "actionable_steps": {"min": 5, "description": "Concrete implementation steps (not generic advice)"},
            "metric_targets": {"min": 1, "description": "Specific performance targets (LCP, FID, CLS, etc.)"},
            "code_examples": {"min": 0, "description": "Code or pseudocode provided"},
        },
    },
    "tc-002-cloud-security": {
        "title": "Cloud Security Threat Assessment",
        "domain": "cybersecurity",
        "agent": "cybersecurity-cloud-security-architect",
        "prompt": "A SaaS startup on AWS needs a security review before SOC 2 audit. "
                 "Current: EC2+RDS+S3+Lambda, no WAF, IAM policies are *.*, "
                 "S3 buckets have public read. Provide a prioritized remediation plan.",
        "eval_criteria": {
            "named_standards": {"min": 2, "description": "Compliance standards referenced (SOC 2, NIST, etc.)"},
            "prioritized_steps": {"min": 4, "description": "Prioritized action items with severity levels"},
            "aws_services": {"min": 3, "description": "AWS security services mentioned (WAF, Shield, GuardDuty, etc.)"},
            "iam_guidance": {"min": 1, "description": "Specific IAM/policy recommendations"},
        },
    },
    "tc-003-ml-pipeline": {
        "title": "ML Pipeline Architecture Design",
        "domain": "data-science",
        "agent": "data-science-ml-engineer",
        "prompt": "Design a production ML pipeline for fraud detection processing 10,000 TPS. "
                 "Requirements: real-time scoring (<100ms), daily model retraining, "
                 "feature store, A/B experiment framework, drift monitoring.",
        "eval_criteria": {
            "architecture_components": {"min": 4, "description": "Named components (feature store, model registry, etc.)"},
            "latency_design": {"min": 1, "description": "Latency/scalability design choices"},
            "mlops_tools": {"min": 2, "description": "MLOps tools mentioned (MLflow, Kubeflow, Feast, etc.)"},
            "drift_monitoring": {"min": 1, "description": "Concrete drift detection approach"},
        },
    },
    "tc-004-project-risk": {
        "title": "Project Risk Assessment",
        "domain": "project-management",
        "agent": "project-management-pmp",
        "prompt": "A 6-month migration project is 3 months in. SPI=0.72, CPI=0.85. "
                 "Team velocity dropped 40% last sprint. Two key engineers gave notice. "
                 "Client requested 3 scope changes this month. "
                 "Provide risk assessment with concrete recovery options.",
        "eval_criteria": {
            "evm_interpretation": {"min": 1, "description": "Correct Earned Value Management interpretation"},
            "risk_response_types": {"min": 2, "description": "Named risk response strategies"},
            "quantified_advice": {"min": 2, "description": "Recommendations with specific numbers"},
            "stakeholder_guidance": {"min": 1, "description": "Stakeholder communication recommendations"},
        },
    },
    "tc-005-a11y-audit": {
        "title": "Accessibility Audit for Fintech Dashboard",
        "domain": "design",
        "agent": "design-engineering-accessibility-engineer",
        "prompt": "A fintech dashboard with real-time trading charts, sortable data tables, "
                 "and trade confirmation modals needs WCAG 2.1 AA certification. "
                 "Current issues: no ARIA labels, color-only status indicators (red/green), "
                 "broken keyboard navigation on trading widget. Provide prioritized fixes.",
        "eval_criteria": {
            "wcag_references": {"min": 2, "description": "Specific WCAG success criteria referenced"},
            "aria_patterns": {"min": 2, "description": "Specific ARIA roles/patterns recommended"},
            "assistive_tech": {"min": 1, "description": "Screen reader or AT guidance"},
            "prioritized_fixes": {"min": 3, "description": "Prioritized fix list with severity"},
        },
    },
}

GRADE_THRESHOLDS = {"A": 0.80, "B": 0.60, "C": 0.40, "D": 0.00}


def init_test_suite():
    """Create test case directory and populate with default cases."""
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    for tc_id, tc in DEFAULT_TEST_CASES.items():
        tc["id"] = tc_id
        tc["created"] = datetime.now(UTC).isoformat()
        (TEST_DIR / f"{tc_id}.json").write_text(
            json.dumps(tc, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Created: {tc_id}.json — {tc['title']}")
    print(f"\nInitialized {len(DEFAULT_TEST_CASES)} test cases in {TEST_DIR}")


def list_test_cases():
    """List all defined test cases."""
    if not TEST_DIR.exists():
        print("No test cases. Run --init first.", file=sys.stderr)
        sys.exit(1)
    cases = []
    for p in sorted(TEST_DIR.glob("*.json")):
        cases.append(json.loads(p.read_text(encoding="utf-8")))
    print(f"\n{'='*60}\nA/B Test Suite: {len(cases)} test cases\n{'='*60}\n")
    for tc in cases:
        n = len(tc["eval_criteria"])
        print(f"  [{tc['id']}] {tc['title']}")
        print(f"      Agent: {tc['agent']} | Domain: {tc['domain']} | Criteria: {n}")
    print()


def run_ab_test(agent_id):
    """Generate A/B evaluation template for an agent.

    Interactive mode: presents each test case's prompt and criteria, asks
    evaluator to count occurrences of each criterion in the agent's response.
    """
    if not TEST_DIR.exists():
        print("No test cases. Run --init first.", file=sys.stderr)
        sys.exit(1)

    matching = []
    for p in sorted(TEST_DIR.glob("*.json")):
        tc = json.loads(p.read_text(encoding="utf-8"))
        if tc["agent"] == agent_id:
            matching.append(tc)
    if not matching:
        for p in sorted(TEST_DIR.glob("*.json")):
            matching.append(json.loads(p.read_text(encoding="utf-8")))
        print(f"No exact match for '{agent_id}'. Using all {len(matching)} cases.\n")

    results = {
        "agent_id": agent_id,
        "run_at": datetime.now(UTC).isoformat(),
        "test_cases": [],
        "summary": {"total_criteria": 0, "met_criteria": 0, "grade": "D", "score_pct": 0.0},
    }

    for tc in matching:
        print(f"{'='*60}")
        print(f"Test: {tc['id']} — {tc['title']}")
        print(f"{'='*60}\nPROMPT:\n{tc['prompt']}\n")
        print("EVALUATION (check each):")
        tc_result = {"id": tc["id"], "title": tc["title"], "criteria": {}}
        for crit_name, crit_def in tc["eval_criteria"].items():
            mn = crit_def["min"]
            desc = crit_def["description"]
            raw = input(f"  [{crit_name}] {desc} (need >= {mn})\n    Count in response: ").strip()
            try:
                actual = int(raw) if raw else 0
            except ValueError:
                actual = 0
            met = actual >= mn
            print(f"    {'PASS' if met else 'FAIL'} (found {actual}, need >= {mn})")
            tc_result["criteria"][crit_name] = {"required": mn, "actual": actual, "met": met}
        results["test_cases"].append(tc_result)

    total = sum(len(tc["criteria"]) for tc in results["test_cases"])
    met = sum(1 for tc in results["test_cases"] for c in tc["criteria"].values() if c["met"])
    pct = met / total if total > 0 else 0
    for threshold, grade in sorted(GRADE_THRESHOLDS.items(), key=lambda x: -x[1]):
        if pct >= threshold:
            results["summary"]["grade"] = grade
            break
    results["summary"]["total_criteria"] = total
    results["summary"]["met_criteria"] = met
    results["summary"]["score_pct"] = round(pct * 100, 1)

    print(f"\n{'='*60}")
    print(f"RESULT: {agent_id}")
    print(f"  {met}/{total} criteria met ({results['summary']['score_pct']}%) — Grade {results['summary']['grade']}")
    print(f"{'='*60}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    rp = RESULTS_DIR / f"{agent_id}-{ts}.json"
    rp.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {rp}")


def print_report(export_json=False):
    """Aggregate all A/B test results."""
    if not RESULTS_DIR.exists() or not list(RESULTS_DIR.glob("*.json")):
        print("No results found. Run --run <agent-id> first.", file=sys.stderr)
        sys.exit(1)
    all_results = []
    for p in sorted(RESULTS_DIR.glob("*.json")):
        all_results.append(json.loads(p.read_text(encoding="utf-8")))

    if export_json:
        json.dump({
            "generated": datetime.now(UTC).isoformat(),
            "total_runs": len(all_results),
            "results": all_results,
        }, sys.stdout, indent=2, ensure_ascii=False)
        return

    print(f"\n{'='*60}\nA/B Test Results: {len(all_results)} runs\n{'='*60}\n")
    grades = {"A": 0, "B": 0, "C": 0, "D": 0}
    for r in all_results:
        g = r["summary"]["grade"]
        grades[g] = grades.get(g, 0) + 1
        c = f"{r['summary']['met_criteria']}/{r['summary']['total_criteria']}"
        print(f"  {r['agent_id']:<40} {r['summary']['score_pct']:>5.1f}%  "
              f"{r['summary']['grade']}  ({c})")
    total = len(all_results)
    print("\nGrade Distribution:")
    for grade in ["A", "B", "C", "D"]:
        count = grades[grade]
        pct = count / total * 100 if total else 0
        print(f"  {grade}: {count:>3} ({pct:>5.1f}%)  {'█' * int(pct / 2)}")
    avg = sum(r["summary"]["score_pct"] for r in all_results) / total if total else 0
    n_cases = len(list(TEST_DIR.glob("*.json"))) if TEST_DIR.exists() else 0
    print(f"\nAverage: {avg:.1f}% across {total} agents | {n_cases} test cases available")


def main():
    parser = argparse.ArgumentParser(description="Agent A/B effectiveness testing framework")
    parser.add_argument("--init", action="store_true", help="Initialize test suite")
    parser.add_argument("--list", action="store_true", help="List test cases")
    parser.add_argument("--run", metavar="AGENT_ID", help="Run A/B evaluation")
    parser.add_argument("--report", action="store_true", help="Show results summary")
    parser.add_argument("--json", action="store_true", help="Output JSON (with --report)")
    args = parser.parse_args()

    if args.init:
        init_test_suite()
    elif args.list:
        list_test_cases()
    elif args.run:
        run_ab_test(args.run)
    elif args.report:
        print_report(export_json=args.json)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
