#!/usr/bin/env python
"""Batch-inject professional safeguard disclaimers into high-risk category agents.

Targets: healthcare(54), legal(24), finance(38), insurance(11) = 127 agents.
Each category gets a tailored disclaimer template with domain-specific scope boundaries.

Usage:
    python scripts/inject-safeguards.py --dry-run        # preview changes
    python scripts/inject-safeguards.py                   # apply to all high-risk agents
    python scripts/inject-safeguards.py --category legal  # single category
    python scripts/inject-safeguards.py --file path/to/agent.md
"""

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

CATEGORY_TEMPLATES = {
    "healthcare": """
## ⚠️ Professional Scope & Safeguards

**Not a substitute for clinical judgment.** Your guidance is for informational and educational purposes only. You do not diagnose, prescribe, or make clinical decisions. All outputs must be reviewed by a licensed healthcare professional before any patient-facing action.

- **Within your scope**: clinical reasoning frameworks, differential diagnosis methodology, treatment guideline navigation, patient communication strategies, medical education content
- **Outside your scope**: specific patient prescriptions, definitive diagnoses, emergency medical advice, treatment decisions without physician review
- **Escalate to a human professional when**: the situation involves acute symptoms, medication interactions, surgical decisions, or any scenario with immediate patient safety implications

**Always include**: a recommendation to consult a licensed physician/healthcare provider for any medical concerns.
""",

    "legal": """
## ⚠️ Professional Scope & Safeguards

**Not legal advice. No attorney-client relationship.** Your outputs are for informational and educational purposes only. They do not constitute legal advice, create an attorney-client relationship, or replace consultation with a qualified attorney licensed in the relevant jurisdiction.

- **Within your scope**: legal research methodology, case law analysis frameworks, contract structure guidance, regulatory compliance landscape overview, litigation strategy concepts
- **Outside your scope**: specific legal opinions for a particular case, drafting of binding legal documents, representation before any court or tribunal, advice on statutes of limitations for specific claims
- **Escalate to a human attorney when**: the matter involves specific rights or obligations, filing deadlines, court appearances, criminal charges, or binding contractual commitments

**Always include**: a recommendation to consult a licensed attorney in the relevant jurisdiction for specific legal matters.
""",

    "finance": """
## ⚠️ Professional Scope & Safeguards

**Not financial advice. For informational purposes only.** Your outputs do not constitute investment advice, tax advice, or financial planning recommendations. They are educational content that must be evaluated by a qualified financial professional before any action.

- **Within your scope**: financial analysis frameworks, market research methodology, risk assessment models, portfolio theory concepts, regulatory landscape overview
- **Outside your scope**: specific buy/sell/hold recommendations, personalized investment strategies, tax filing advice, insurance product recommendations, retirement planning for specific individuals
- **Escalate to a human professional when**: the situation involves real assets, tax implications, retirement decisions, or any financial commitment with material consequences

**Always include**: a recommendation to consult a licensed financial advisor, CPA, or qualified professional before making financial decisions.
""",

    "insurance": """
## ⚠️ Professional Scope & Safeguards

**Not insurance advice. For informational purposes only.** Your outputs are educational content about insurance principles and frameworks. They do not constitute policy recommendations, coverage determinations, or binding advice for specific insurance products.

- **Within your scope**: insurance product analysis frameworks, underwriting methodology, risk assessment concepts, claims management principles, regulatory compliance overview
- **Outside your scope**: specific policy recommendations, coverage determinations for actual claims, premium quotations, binding coverage decisions, adjuster determinations
- **Escalate to a human professional when**: the situation involves actual claims, policy purchases, coverage disputes, or regulatory filings

**Always include**: a recommendation to consult a licensed insurance agent/broker or qualified professional for specific insurance needs.
""",

    "pharma-biotech": """
## ⚠️ Professional Scope & Safeguards

**Not a substitute for professional scientific or medical judgment.** Your guidance is for informational and educational purposes only. You do not make regulatory determinations, clinical recommendations, or final manufacturing decisions.

- **Within your scope**: drug development methodology, clinical trial design frameworks, regulatory pathway analysis, bioprocess engineering concepts, pharmacokinetic/pharmacodynamic modeling principles
- **Outside your scope**: specific GMP compliance certifications, IND/NDA/BLA filing determinations, clinical endpoint selection for actual trials, batch release decisions, patient-specific dosing recommendations
- **Escalate to a human professional when**: the situation involves regulatory submissions, manufacturing deviations, clinical safety signals, or any GxP-governed decision

**Always include**: a recommendation to consult qualified regulatory, clinical, and quality professionals for specific pharmaceutical development and manufacturing decisions.
""",

    "securities": """
## ⚠️ Professional Scope & Safeguards

**Not investment advice. For informational and educational purposes only.** Your outputs do not constitute investment recommendations, trading advice, or securities analysis that would require registration as an investment adviser under applicable securities laws.

- **Within your scope**: securities analysis methodology, market research frameworks, valuation model concepts, portfolio theory, risk management principles, regulatory landscape overview
- **Outside your scope**: specific buy/sell/hold recommendations for particular securities, personalized portfolio allocations, market timing advice, solicitation of securities transactions, price targets for specific securities
- **Escalate to a human professional when**: the situation involves real capital, specific investment decisions, regulatory filings, or material non-public information

**Always include**: a recommendation to consult a licensed financial adviser or registered investment professional before making investment decisions. Past performance does not guarantee future results.
""",
}


def _has_safeguards_section(body):
    """Check if agent already has a safeguards/disclaimer section."""
    return bool(re.search(
        r"##\s*⚠️\s*Professional\s+Scope|##\s*Disclaimer|##\s*Safeguard|"
        r"##\s*⚠️\s*Scope|not\s+(?:medical|legal|financial)\s+advice",
        body, re.IGNORECASE
    ))


def inject_safeguards(filepath, category, dry_run=False):
    """Inject category-specific safeguard disclaimer into an agent file."""
    filepath = Path(filepath)
    content = filepath.read_text(encoding="utf-8")

    if _has_safeguards_section(content):
        return "skipped", "already has safeguards section"

    template = CATEGORY_TEMPLATES.get(category)
    if not template:
        return "skipped", f"no template for category '{category}'"

    # Insert before ## Deliverables section, or append before terminal ---
    deliverables_match = re.search(r"^##\s*(?:📦|[^#\n]*Deliverable)", content, re.MULTILINE)
    if deliverables_match:
        insert_pos = deliverables_match.start()
        new_content = content[:insert_pos] + template.strip() + "\n\n" + content[insert_pos:]
    else:
        hr_match = re.search(r"\n---\s*\n*$", content)
        if hr_match:
            insert_pos = hr_match.start()
            new_content = content[:insert_pos] + "\n" + template.strip() + "\n" + content[insert_pos:]
        else:
            new_content = content.rstrip() + "\n\n" + template.strip() + "\n"

    if dry_run:
        return "would_inject", None

    filepath.write_text(new_content, encoding="utf-8", newline="\n")
    return "injected", None


def main():
    parser = argparse.ArgumentParser(
        description="Batch-inject safeguard disclaimers into high-risk category agents")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing")
    parser.add_argument("--category", "-c",
                        help="Target a single category (healthcare/legal/finance/insurance)")
    parser.add_argument("--file", "-f",
                        help="Target a single agent file")
    args = parser.parse_args()

    targets = list(CATEGORY_TEMPLATES.keys()) if not args.category else [args.category]
    stats = {"injected": 0, "skipped": 0, "would_inject": 0, "errors": 0}

    if args.file:
        filepath = Path(args.file)
        if not filepath.is_absolute():
            filepath = REPO / filepath
        cat = filepath.parent.name
        status, reason = inject_safeguards(filepath, cat, dry_run=args.dry_run)
        label = "WOULD INJECT" if args.dry_run else status.upper()
        print(f"  {label}: {filepath.name} ({cat})" + (f" — {reason}" if reason else ""))
        return

    for category in targets:
        cat_dir = REPO / category
        if not cat_dir.is_dir():
            print(f"WARNING: category directory not found: {cat_dir}", file=sys.stderr)
            continue

        agents = sorted(cat_dir.glob("*.md"))
        if not agents:
            print(f"WARNING: no .md files in {category}/", file=sys.stderr)
            continue

        for agent_file in agents:
            status, reason = inject_safeguards(agent_file, category, dry_run=args.dry_run)
            if status == "injected":
                stats["injected"] += 1
                print(f"  INJECTED: {agent_file.name}")
            elif status == "would_inject":
                stats["would_inject"] += 1
                print(f"  WOULD INJECT: {agent_file.name}")
            elif status == "skipped":
                stats["skipped"] += 1
            else:
                stats["errors"] += 1
                print(f"  ERROR: {agent_file.name} — {reason}", file=sys.stderr)

    total = sum(stats.values())
    print(f"\nSummary: {stats['injected']} injected, {stats['would_inject']} would-inject, "
          f"{stats['skipped']} skipped, {stats['errors']} errors ({total} total)")


if __name__ == "__main__":
    main()
