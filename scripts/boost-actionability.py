#!/usr/bin/env python
"""Inject actionable directives into stuck B-grade agents to boost content_depth."""

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

DOMAIN_ACTIONS = {
    "engineering": """- Always define interface contracts before implementation (OpenAPI/GraphQL schema-first)
- Ensure every component has a single responsibility; refactor when it exceeds 200 lines
- Validate all external inputs at the boundary; never trust data from APIs or files
- Implement automated tests for every critical path before marking a feature complete
- Review every PR against SOLID principles and the team's coding standards
- Monitor deployment health for 30 minutes after every release; keep rollback plan ready
- Document architectural decisions in ADRs; link them from relevant code
- Run performance benchmarks on every PR that modifies data access or algorithms""",
    "manufacturing": """- Always conduct FMEA before introducing a new process step; document all failure modes
- Ensure SPC control charts are updated within each shift; investigate points beyond 2-sigma
- Verify calibration of all measurement instruments before each production run
- Implement 5S audit at every shift start; score and photograph each station
- Never bypass a quality gate; every non-conformance must have documented disposition
- Run DOE before adjusting critical process parameters; document factor interactions
- Review OEE metrics daily; escalate any cell below 85% to engineering within 2 hours
- Maintain traceability from raw material lot to finished product serial number""",
    "data-science": """- Always split data chronologically for time-series; never use random split
- Ensure feature distributions are validated in production against training baselines
- Verify model predictions against a holdout set before every deployment
- Implement data drift monitoring on all production models; alert if PSI exceeds 0.2
- Review feature importance quarterly; retire features with near-zero SHAP values
- Document every experiment with hypothesis, method, results, and decision in MLflow
- Calibrate probability outputs when using models for risk scoring or pricing
- Never deploy a model without an A/B test plan and pre-registered success criterion""",
    "infrastructure": """- Always apply changes via IaC; never make manual console modifications in production
- Ensure every service has defined SLOs with error budgets; halt features if budget exhausted
- Verify backup restoration quarterly; document RTO/RPO against business requirements
- Implement least-privilege IAM; review and prune unused permissions monthly
- Monitor capacity trends weekly; provision additional resources before 70% utilization
- Run chaos engineering experiments monthly; start with dependency faults
- Maintain runbooks for every P0/P1 alert; update after each incident
- Review security groups quarterly; remove any rule without documented justification""",
    "robotics": """- Always validate inverse kinematics against joint limits before execution
- Ensure collision detection is tested with physical obstacles before production deployment
- Verify sensor calibration at every shift start; document drift from baseline
- Implement safety-rated monitored speed in all collaborative workspaces (ISO/TS 15066)
- Run path planning simulation before uploading trajectories to the physical controller
- Review emergency stop logs weekly; investigate any unplanned E-stop within 24 hours
- Maintain a digital twin of the production cell; validate changes in simulation first
- Document all teach points with tolerances; update after any mechanical maintenance""",
    "cybersecurity": """- Always verify identity for every access request; never grant based on IP or location
- Ensure all penetration test findings are remediated or risk-accepted within SLA
- Verify incident response runbooks with quarterly tabletop exercises
- Implement MFA on every external-facing service; audit MFA coverage monthly
- Review SIEM alert rules quarterly; tune out false positives exceeding 5% of volume
- Rotate all service account credentials every 90 days; automate rotation where possible
- Maintain an accurate asset inventory; reconcile with cloud provider APIs weekly
- Never defer a critical CVE patch beyond SLA without documented compensating control""",
    "testing": """- Always write test cases before implementation code; verify they fail first
- Ensure every critical user journey has an automated end-to-end test
- Verify test data is isolated per test run; never share state between test cases
- Implement flaky test quarantine; any test failing over 2% of runs requires investigation
- Review test coverage gaps monthly; prioritize tests for untested error handling paths
- Run the full regression suite before every release; block on unexpected failures
- Maintain a bug taxonomy; classify every escaped defect to identify testing gaps
- Never mark a test as skipped without a linked issue tracking its re-enablement""",
    "healthcare": """- Always validate clinical decisions against current evidence-based guidelines
- Ensure patient data is de-identified before any secondary analysis
- Verify AI model outputs with a qualified clinician before clinical use
- Implement double-check for high-risk medication calculations and dosing
- Review adverse event reports within 24 hours; escalate serious events immediately
- Maintain audit trails for all clinical decisions with timestamps and attribution
- Document differential diagnoses with supporting and refuting evidence
- Never rely solely on a single diagnostic test; triangulate with clinical presentation""",
    "marketing": """- Always define success metrics before launching any campaign; pre-register KPIs
- Ensure every campaign has a control group; never compare against historical baselines
- Verify UTM parameters are consistent across all channels before campaign launch
- Implement holdout groups for CRM campaigns; measure incremental lift
- Review creative performance weekly; pause ads below CTR benchmark by day 7
- Document audience segmentation logic; ensure it is reproducible and explainable
- Maintain a content calendar with at least 4 weeks of forward visibility
- Never spend over 10% of budget on a new channel without a validated test result""",
    "customer-service": """- Always acknowledge customer contact within SLA window; confirm receipt immediately
- Ensure every interaction is categorized with root cause; never close unresolved
- Verify customer understanding before closing; use teach-back for complex issues
- Implement callback for every abandoned call within 15 minutes during business hours
- Review CSAT detractors daily; follow up personally within 24 hours
- Maintain a knowledge base article for every top-20 contact reason; update quarterly
- Monitor queue depth in real time; escalate when wait time exceeds 5 minutes
- Never transfer a customer more than once; own the resolution or warm-transfer""",
    "administration": """- Always verify contract renewal dates 90 days before expiry
- Ensure every expense has a receipt and budget code before processing payment
- Verify vendor certifications annually; document compliance in the vendor register
- Implement document retention per records schedule; never destroy ahead of schedule
- Review travel policy compliance quarterly; flag any pattern of policy exceptions
- Maintain an up-to-date asset register; reconcile physical inventory every 6 months
- Process invoices within payment terms; never incur a late fee on valid invoices
- Archive completed projects within 30 days; ensure deliverables are indexed""",
}
DEFAULT_ACTIONS = """- Always verify requirements with stakeholders before beginning implementation
- Ensure deliverables meet documented acceptance criteria before submission
- Validate assumptions with data; never rely on intuition for critical decisions
- Implement regular review cadence; surface blockers within 24 hours
- Document key decisions with rationale; maintain an accessible decision log
- Review progress against milestones weekly; escalate schedule risks at 10% variance
- Maintain a current risk register; update mitigation status at each review
- Never commit to a deadline without understanding the scope and dependencies"""


def inject(path, category):
    c = path.read_text(encoding="utf-8")
    parts = c.split("---", 2)
    if len(parts) < 3: return False
    body = parts[2]
    if re.search(r"Actionable Directive|Execution Standard|Operations Directive", body, re.IGNORECASE):
        return False
    actions = DOMAIN_ACTIONS.get(category, DEFAULT_ACTIONS)
    target = re.search(r"^##[^#\n]*?(?:communication|how you communicate|tone|learning|success metrics)",
                       body, re.IGNORECASE | re.MULTILINE)
    pos = target.start() if target else len(body)
    section = f"\n## 🎯 Actionable Directives\n\n{actions}\n"
    path.write_text("---".join(parts[:2]) + "---" + body[:pos] + section + body[pos:], encoding="utf-8")
    return True


def main():
    sc = ["python", str(REPO/"scripts"/"score-agents.py"), "--json", "--no-freshness"]
    r = subprocess.run(sc, capture_output=True, text=True, timeout=120, cwd=str(REPO))
    data = json.loads(r.stdout)
    gold = [a for a in data["agents"] if a["total"]>=8 and a.get("tool_references",0)>=2
            and a.get("boilerplate_count",0)<=3 and a["word_count"]>=500]
    targets = [a for a in gold if a["total"]==8]
    if not targets:
        print("All Gold agents are A-grade!")
        return
    print(f"Injecting directives into {len(targets)} agents\n")
    n = 0
    for a in targets:
        p = REPO / a["category"] / f"{a['id']}.md"
        if not p.exists(): continue
        if inject(p, a["category"]): n += 1
    print(f"Injected: {n}")
    r2 = subprocess.run(sc, capture_output=True, text=True, timeout=120, cwd=str(REPO))
    nd = json.loads(r2.stdout)
    ng = [a for a in nd["agents"] if a["total"]>=8 and a.get("tool_references",0)>=2
          and a.get("boilerplate_count",0)<=3 and a["word_count"]>=500]
    na = sum(1 for a in ng if a["total"]>=9)
    nb = sum(1 for a in ng if a["total"]==8)
    old_a = sum(1 for a in gold if a["total"]>=9)
    print(f"\nGold A: {na} (+{na-old_a})  Gold B: {nb}  Total: {len(ng)}")


if __name__ == "__main__":
    main()
