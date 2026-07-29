#!/usr/bin/env python3
"""Batch add phase-4-hardening to nexus_roles for selected agents."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CANDIDATES = [
    # testing (15)
    "testing/testing-api-tester.md",
    "testing/testing-automation-architect.md",
    "testing/testing-director.md",
    "testing/testing-engineering-quality-assurance-automation.md",
    "testing/testing-engineering-reliability-testing.md",
    "testing/testing-engineering-sdet.md",
    "testing/testing-engineering-test-automation-framework.md",
    "testing/testing-localization.md",
    "testing/testing-multi-agent-coordinator.md",
    "testing/testing-performance-benchmarker.md",
    "testing/testing-playwright-expert.md",
    "testing/testing-security-penetration.md",
    "testing/testing-test-results-analyzer.md",
    "testing/testing-usability.md",
    "testing/testing-accessibility-auditor.md",
    # cybersecurity (5)
    "cybersecurity/cybersecurity-security-architect.md",
    "cybersecurity/cybersecurity-engineering-security-architect-cloud.md",
    "cybersecurity/cybersecurity-engineering-compliance-engineer.md",
    "cybersecurity/cybersecurity-engineering-privacy-engineer.md",
    "cybersecurity/cybersecurity-soc-analyst.md",
    # infrastructure (9)
    "infrastructure/infrastructure-datadog-expert.md",
    "infrastructure/infrastructure-engineering-incident-commander.md",
    "infrastructure/infrastructure-engineering-site-reliability-architect.md",
    "infrastructure/infrastructure-engineering-site-reliability-automation.md",
    "infrastructure/infrastructure-engineering-sre-manager.md",
    "infrastructure/infrastructure-backup-admin.md",
    "infrastructure/infrastructure-monitoring-admin.md",
    "infrastructure/infrastructure-engineering-observability-engineer.md",
    "infrastructure/infrastructure-storage-backup.md",
]


def add_hardening_role(filepath):
    """Add phase-4-hardening to nexus_roles in YAML frontmatter."""
    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines(True)

    # Find frontmatter boundaries
    fm_start = fm_end = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "---":
            if fm_start is None:
                fm_start = i
            elif fm_end is None:
                fm_end = i
                break

    if fm_start is None or fm_end is None:
        return False, "no frontmatter"

    # Already present?
    fm_text = "".join(lines[fm_start : fm_end + 1])
    if "phase-4-hardening" in fm_text:
        return False, "already present"

    # Find nexus_roles line
    for i in range(fm_start + 1, fm_end):
        stripped = lines[i].strip()
        if stripped.startswith("nexus_roles:"):
            indent = len(lines[i]) - len(lines[i].lstrip())
            if stripped == "nexus_roles: []":
                lines[i] = f"{' ' * indent}nexus_roles:\n"
                lines.insert(i + 1, f"{' ' * (indent + 2)}- phase-4-hardening\n")
            else:
                lines[i] = lines[i].rstrip("\n") + "\n"
                # Find where to insert: after last list item
                j = i + 1
                while j < fm_end:
                    sj = lines[j].strip()
                    if sj.startswith("- ") or sj == "" or sj.startswith("#"):
                        j += 1
                    else:
                        break
                lines.insert(j, f"{' ' * (indent + 2)}- phase-4-hardening\n")
            filepath.write_text("".join(lines), encoding="utf-8")
            return True, "added"

    # No nexus_roles field — add before closing ---
    insert_at = fm_end
    for i in range(fm_end - 1, fm_start, -1):
        if lines[i].strip() and not lines[i].strip().startswith("#"):
            # Get indent from previous field
            prev_indent = len(lines[i]) - len(lines[i].lstrip())
            indent = " " * prev_indent
            lines.insert(i + 1, f"{indent}nexus_roles:\n")
            lines.insert(i + 2, f"{indent}  - phase-4-hardening\n")
            filepath.write_text("".join(lines), encoding="utf-8")
            return True, "added (new field)"

    return False, "could not insert"


def main():
    added = 0
    skipped = 0
    for rel_path in CANDIDATES:
        filepath = ROOT / rel_path
        ok, msg = add_hardening_role(filepath)
        status = "+" if ok else "~"
        print(f"  [{status}] {rel_path:<70} {msg}")
        if ok:
            added += 1
        else:
            skipped += 1

    print(f"\n{added} added, {skipped} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
