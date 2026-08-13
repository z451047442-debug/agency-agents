#!/usr/bin/env python3
"""Security audit for The Agency's own configuration and tooling.

Scans shell scripts, Python scripts, and configuration files for dangerous
patterns — command injection, hardcoded secrets, unsafe shell constructs.
Inspired by ECC's AgentShield security-scan pattern.

Usage:
    python scripts/audit-security.py                    # full audit
    python scripts/audit-security.py --json             # machine-readable output
    python scripts/audit-security.py --check            # CI mode: exit 1 on findings
"""

import argparse
import json
import re
import sys
from pathlib import Path

from _shared import BOLD, GREEN, RED, REPO, RESET, YELLOW

# ── Shell script patterns ──────────────────────────────────────────────────

SHELL_PATTERNS = {
    "pipe_curl_bash": (
        r"curl\s+.+\s*\|\s*(?:ba)?sh",
        "CRITICAL",
        "curl pipe bash — remote code execution risk; verify the URL is trusted",
    ),
    "unquoted_variable_in_eval": (
        r"eval\s+.*\$",
        "HIGH",
        "eval with unquoted variable — command injection risk",
    ),
    "rm_rf_unsafe": (
        r"rm\s+-rf\s+\$?(?:/\w*|\*)",
        "MEDIUM",
        "rm -rf with dynamic path — verify the variable is sanitized",
    ),
    "sudo_in_script": (
        r"\bsudo\b",
        "LOW",
        "sudo in script — elevated privileges; ensure the script is not run unattended",
    ),
}

# ── Python script patterns ─────────────────────────────────────────────────

PYTHON_PATTERNS = {
    "os_system_input": (
        r"os\.system\(.*\{.*\}",
        "CRITICAL",
        "os.system with format string — command injection risk; use subprocess.run",
    ),
    "hardcoded_secret": (
        r"(?:password|secret|token|api_key|apikey)\s*[:=]\s*[\"'][^\"']{8,}[\"']",
        "HIGH",
        "hardcoded credential — use environment variables",
    ),
    "pickle_loads": (
        r"pickle\.loads?\(",
        "HIGH",
        "pickle deserialization — arbitrary code execution risk; use json instead",
    ),
    "yaml_load_unsafe": (
        r"yaml\.load\(",
        "MEDIUM",
        "yaml.load without SafeLoader — use yaml.safe_load instead",
    ),
    "shell_true": (
        r"subprocess\.\w+\(.*shell\s*=\s*True",
        "MEDIUM",
        "subprocess with shell=True — prefer shell=False with list args",
    ),
}

# ── Config file patterns ───────────────────────────────────────────────────

CONFIG_PATTERNS = {
    "github_token": (
        r"gh[pst]_[a-zA-Z0-9]{36,}",
        "CRITICAL",
        "GitHub token in config — revoke immediately and use environment variable",
    ),
    "aws_key": (
        r"AKIA[0-9A-Z]{16}",
        "CRITICAL",
        "AWS access key in config — revoke and use IAM roles or env vars",
    ),
}


def scan_file(filepath: Path, patterns: dict) -> list[dict]:
    """Scan a file for security patterns. Returns list of findings."""
    findings: list[dict] = []
    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return findings

    rel = str(filepath.relative_to(REPO)).replace("\\", "/")
    for name, (pattern, severity, desc) in patterns.items():
        for m in re.finditer(pattern, content, re.MULTILINE):
            ln = content[:m.start()].count("\n") + 1
            snippet = content[max(0, m.start() - 10):m.end() + 10].replace("\n", " ").strip()
            findings.append({
                "file": rel, "line": ln, "severity": severity,
                "rule": name, "desc": desc, "match": snippet,
            })
    return findings


def audit_all() -> list[dict]:
    """Run all security audits and return combined findings."""
    findings = []
    for sh in REPO.glob("scripts/**/*.sh"):
        findings.extend(scan_file(sh, SHELL_PATTERNS))
    for py in REPO.glob("scripts/**/*.py"):
        if "__pycache__" in str(py):
            continue
        findings.extend(scan_file(py, PYTHON_PATTERNS))
    # Recursively scan config files (root-only globs missed .github/, scripts/,
    # etc.). Skip VCS/env/derived directories.
    config_suffixes = {".json", ".yaml", ".yml", ".toml"}
    skip_roots = {".git", "env", "integrations", "__pycache__"}
    for f in REPO.rglob("*"):
        if not f.is_file():
            continue
        try:
            rel = f.relative_to(REPO)
        except ValueError:
            continue
        if rel.parts and rel.parts[0] in skip_roots:
            continue
        if (f.suffix in config_suffixes
                or f.name.startswith(".env")
                or f.name == "CLAUDE.md"):
            findings.extend(scan_file(f, CONFIG_PATTERNS))
    return findings


def print_report(findings: list[dict]) -> int:
    """Print human-readable report. Returns count of CRITICAL + HIGH findings."""
    if not findings:
        print(f"{GREEN}No security issues found.{RESET}")
        return 0

    by_sev: dict[str, list[dict]] = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
    for f in findings:
        by_sev[f["severity"]].append(f)

    for sev, color in [("CRITICAL", RED), ("HIGH", YELLOW), ("MEDIUM", ""), ("LOW", "")]:
        items = by_sev[sev]
        if not items:
            continue
        print(f"\n{BOLD}{color}{sev} ({len(items)} findings){RESET}")
        for f in items:
            print(f"  {color}{f['file']}:{f['line']}{RESET} [{f['rule']}]")
            print(f"    {f['desc']}")

    critical_high = len(by_sev["CRITICAL"]) + len(by_sev["HIGH"])
    print(f"\n{BOLD}Summary: {len(findings)} findings "
          f"({len(by_sev['LOW'])} low, {len(by_sev['MEDIUM'])} medium, "
          f"{len(by_sev['HIGH'])} high, {len(by_sev['CRITICAL'])} critical){RESET}")
    return critical_high


def main() -> None:
    parser = argparse.ArgumentParser(description="Security audit for Agency tooling")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    findings = audit_all()

    if args.json:
        json.dump({"findings": findings, "total": len(findings)},
                  sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return

    critical_high = print_report(findings)
    if args.check and critical_high > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
