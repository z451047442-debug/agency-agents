# Agency Hardening & Quality Enhancement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebalance NEXUS Hardening agents, fix quality issues in 104 flagged agents, build 2 new NEXUS tools, and add 4 metadata fields.

**Architecture:** Execute 4 tracks in priority order (P1→P4). Each track produces independently testable deliverables. P1 reclassifies existing agents + creates missing role agents. P2 auto-fixes deps + expands thin agents. P3 builds 2 new scripts using existing `_shared` modules. P4 extends schema/linter/search with new fields.

**Tech Stack:** Python 3.12, pytest, YAML frontmatter in markdown files

## Global Constraints

- All new scripts must follow existing patterns: use `_shared` modules, `argparse`, `Path`
- Schema field additions must be optional (not `required`) to avoid breaking existing agents
- All agent file modifications must use `atomic_write` from `_shared`
- Run `python -m pytest tests/ --cov=scripts` after each track completes
- Run `python scripts/lint-agents.py --all` after any agent file modifications
- Commit after each completed task, not in bulk

---

## Track P1: NEXUS Hardening Rebalance

### Task 1: Bulk suggest + review hardening candidates

**Files:**
- Modify: `scripts/suggest-nexus-roles.py` (add `--json` output mode)
- Test: `tests/test_suggest_nexus_roles.py`

**Interfaces:**
- Consumes: `_shared.discovery.discover_agents`, existing `analyze_agent`
- Produces: `suggest_nexus_roles.main()` with `--phase phase-4-hardening --json` flag

- [ ] **Step 1: Add `--phase` and `--json` flags to suggest-nexus-roles.py**

```python
# In main(), add new arguments:
parser.add_argument("--phase", "-p",
                    help="Filter suggestions to a specific NEXUS phase (e.g., phase-4-hardening)")
parser.add_argument("--json", action="store_true",
                    help="Output as JSON for machine consumption")
```

- [ ] **Step 2: Implement `--phase` filtering logic**

```python
# After analyze_agent() returns matches, filter by phase:
if args.phase:
    matches = [(pid, label, count) for pid, label, count in matches
               if pid == args.phase]
```

- [ ] **Step 3: Implement `--json` output**

```python
# In main(), after the analysis loop, add JSON output branch:
if args.json:
    output = []
    for result in results:  # collected during loop
        output.append({
            "agent_id": result["agent_id"],
            "category": result["category"],
            "path": result["path"],
            "matches": [{"phase": pid, "label": label, "keywords": count}
                        for pid, label, count in result["matches"]],
        })
    json.dump(output, sys.stdout, indent=2)
    return
```

- [ ] **Step 4: Update tests**

```python
# tests/test_suggest_nexus_roles.py — add TestPhaseFilter class

class TestPhaseFilter:
    def test_filters_to_single_phase(self, tmp_path, monkeypatch, capsys):
        f = tmp_path / "agent.md"
        f.write_text(
            "---\nname: Dev\n---\nI do testing and qa with code review and deployment.",
            encoding="utf-8",
        )
        with patch.object(sys, "argv",
                          ["suggest-nexus-roles.py", "--file", str(f),
                           "--phase", "phase-4-hardening"]):
            mod.main()
        out = capsys.readouterr().out
        assert "phase-4-hardening" in out
        assert "phase-5-launch" not in out  # deployment keyword shouldn't show
```

- [ ] **Step 5: Run tests, verify pass**

Run: `python -m pytest tests/test_suggest_nexus_roles.py -v`
Expected: all tests PASS

- [ ] **Step 6: Run full scan for hardening candidates**

Run: `python scripts/suggest-nexus-roles.py --phase phase-4-hardening --json --min-confidence 2`
Expected: JSON output listing agents whose body matches hardening keywords

- [ ] **Step 7: Commit**

```bash
git add scripts/suggest-nexus-roles.py tests/test_suggest_nexus_roles.py
git commit -m "feat: add --phase and --json flags to suggest-nexus-roles.py"
```

---

### Task 2: Batch-add hardening roles from suggestions

**Files:**
- Create: `scripts/batch-add-hardening-v2.py`
- Test: `tests/test_batch_add_hardening_v2.py`

**Interfaces:**
- Consumes: `_shared.discovery.discover_agents`, `_shared.frontmatter.*`, `_shared.atomic_write`, `suggest_nexus_roles.analyze_agent`
- Produces: CLI script with `--dry-run`, `--category`, `--min-confidence` flags

- [ ] **Step 1: Write the test**

```python
# tests/test_batch_add_hardening_v2.py
import pytest
from pathlib import Path
from unittest.mock import patch
import importlib.util, sys

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
spec = importlib.util.spec_from_file_location(
    "batch_add_hardening_v2", str(SCRIPTS_DIR / "batch-add-hardening-v2.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestBatchAddHardeningV2:
    def test_repo_root(self):
        assert mod.ROOT.is_dir()

    def test_needs_hardening_true(self):
        body = "## Testing\nI specialize in testing, qa, code review, security audit, and vulnerability assessment."
        assert mod.needs_hardening(body) is True

    def test_needs_hardening_false(self):
        body = "## Discovery\nI do market research and user interviews."
        assert mod.needs_hardening(body) is False

    def test_add_hardening_role_inserts_after_date_added(self, tmp_path):
        f = tmp_path / "agent.md"
        f.write_text(
            "---\nname: Tester\ndate_added: '2026-07-01'\n---\nBody",
            encoding="utf-8",
        )
        mod.add_hardening_role(f)
        content = f.read_text(encoding="utf-8")
        assert "phase-4-hardening" in content

    def test_add_hardening_role_idempotent(self, tmp_path):
        f = tmp_path / "agent.md"
        f.write_text(
            "---\nname: Tester\ndate_added: '2026-07-01'\nnexus_roles:\n  - phase-4-hardening\n---\nBody",
            encoding="utf-8",
        )
        mod.add_hardening_role(f)
        content = f.read_text(encoding="utf-8")
        assert content.count("phase-4-hardening") == 1

    def test_dry_run_no_write(self, tmp_path, monkeypatch):
        d = tmp_path / "testing"
        d.mkdir()
        f = d / "testing-sdet.md"
        f.write_text(
            "---\nname: SDET\ndate_added: '2026-07-01'\n---\nI do testing and qa.",
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "ROOT", tmp_path)
        import io
        with patch.object(sys, "argv",
                          ["batch-add-hardening-v2.py", "--dry-run", "--min-confidence", "1"]):
            with patch.object(sys, "stdout", io.StringIO()) as mock_stdout:
                try:
                    mod.main()
                except SystemExit:
                    pass
        content_after = f.read_text(encoding="utf-8")
        assert "phase-4-hardening" not in content_after  # dry-run shouldn't modify
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_batch_add_hardening_v2.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write the script**

```python
#!/usr/bin/env python3
"""Batch add phase-4-hardening to nexus_roles for agents with hardening keywords (v2).

Uses suggest-nexus-roles keyword analysis to find candidates automatically,
rather than a hardcoded candidate list.

Usage:
    python scripts/batch-add-hardening-v2.py --dry-run           # preview only
    python scripts/batch-add-hardening-v2.py                     # apply
    python scripts/batch-add-hardening-v2.py --category testing  # single category
    python scripts/batch-add-hardening-v2.py --min-confidence 3  # stricter matching
"""

import argparse
import re
import sys
from pathlib import Path

from _shared import GREEN, RED, RESET, YELLOW, atomic_write
from _shared.discovery import EXCLUDE_DIRS, discover_agents

ROOT = Path(__file__).resolve().parent.parent

HARDENING_KEYWORDS = [
    "testing", "qa", "security review", "performance", "optimization",
    "hardening", "code review", "linting", "audit", "quality",
    "vulnerability", "validation", "verification", "benchmark", "refactor",
]


def needs_hardening(body: str, min_confidence: int = 2) -> bool:
    body_lower = body.lower()
    count = 0
    for kw in HARDENING_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", body_lower):
            count += 1
        if count >= min_confidence:
            return True
    return False


def add_hardening_role(filepath: Path):
    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines(True)

    # Find frontmatter boundaries
    fm_start = None
    fm_end = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if fm_start is None:
                fm_start = i
            elif fm_end is None:
                fm_end = i
                break

    if fm_start is None or fm_end is None:
        return False

    # Check if already has phase-4-hardening
    fm_text = "".join(lines[fm_start + 1:fm_end])
    if "phase-4-hardening" in fm_text:
        return False  # already present, idempotent

    # Find insertion point: after nexus_roles list start, or after date_added
    inserted = False
    new_lines = []
    in_nexus_roles = False

    for i, line in enumerate(lines[:fm_end]):
        new_lines.append(line)
        if not inserted:
            if re.match(r"^nexus_roles:", line):
                in_nexus_roles = True
            elif in_nexus_roles and re.match(r"^\s+- ", line):
                pass  # keep scanning nexus_roles items
            elif in_nexus_roles and not re.match(r"^\s+- ", line):
                # End of nexus_roles block — insert before this line
                new_lines.insert(-1, "  - phase-4-hardening\n")
                inserted = True
                in_nexus_roles = False
            elif re.match(r"^date_added:", line) and not in_nexus_roles:
                # No nexus_roles yet — insert it after date_added
                new_lines.append("nexus_roles:\n")
                new_lines.append("  - phase-4-hardening\n")
                inserted = True

    if not inserted:
        # Append to end of frontmatter
        new_lines.insert(-1, "nexus_roles:\n")
        new_lines.insert(-1, "  - phase-4-hardening\n")

    new_lines.extend(lines[fm_end:])
    new_content = "".join(new_lines)
    atomic_write(filepath, new_content)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Batch add phase-4-hardening to agents matching hardening keywords"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    parser.add_argument("--category", "-c", help="Only process one category")
    parser.add_argument("--min-confidence", type=int, default=2,
                        help="Minimum keyword matches (default: 2)")
    args = parser.parse_args()

    candidates = []
    for _cat, _rel, filepath in discover_agents(category_filter=args.category):
        if filepath.name.startswith("."):
            continue
        try:
            body = filepath.read_text(encoding="utf-8")
        except OSError:
            continue
        parts = body.split("---", 2)
        body_text = parts[2] if len(parts) >= 3 else body
        if needs_hardening(body_text, args.min_confidence):
            candidates.append(filepath)

    print(f"Found {len(candidates)} candidates for hardening role")

    if args.dry_run:
        print(f"{YELLOW}DRY RUN — no changes written{RESET}")
        for f in candidates:
            print(f"  {f.relative_to(ROOT)}")
        return

    added = 0
    skipped = 0
    for f in candidates:
        if add_hardening_role(f):
            print(f"  {GREEN}+ hardening{RESET} {f.relative_to(ROOT)}")
            added += 1
        else:
            skipped += 1

    print(f"\nAdded: {added} | Already had: {skipped}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify pass**

Run: `python -m pytest tests/test_batch_add_hardening_v2.py -v`
Expected: all tests PASS

- [ ] **Step 5: Dry-run preview**

Run: `python scripts/batch-add-hardening-v2.py --dry-run --min-confidence 2`
Expected: List of candidate agents, count estimate

- [ ] **Step 6: Apply**

Run: `python scripts/batch-add-hardening-v2.py --min-confidence 2`
Expected: hardening agent count increases (verify with `python scripts/nexus-orchestrator.py --stats`)

- [ ] **Step 7: Validate**

Run: `python scripts/lint-agents.py --all --no-freshness`
Expected: no new errors

- [ ] **Step 8: Commit**

```bash
git add scripts/batch-add-hardening-v2.py tests/test_batch_add_hardening_v2.py
git commit -m "feat: batch-add-hardening-v2 with keyword-based auto-detection"
```

---

### Task 3: Gap analysis against 8 playbook roles

**Files:**
- Modify: `scripts/nexus-coverage.py` (new script — P3 Task 6, but gap analysis logic needed first)
- This is a research task — run queries, produce report, no code changes to agents

**Interfaces:**
- Consumes: existing agent files with `nexus_roles`, `docs/playbooks/phase-4-hardening.md`
- Produces: gap report (terminal output)

- [ ] **Step 1: Search existing agents for each of the 8 playbook roles**

```bash
# Evidence Collector
python scripts/search-agents.sh "evidence collector" "screenshot" "visual evidence"
# API Tester
python scripts/search-agents.sh "api tester" "api testing" "API regression"
# Performance Benchmarker
python scripts/search-agents.sh "performance benchmark" "load testing" "benchmarker"
# Legal Compliance Checker
python scripts/search-agents.sh "compliance checker" "legal compliance" "regulatory audit"
# Test Results Analyzer
python scripts/search-agents.sh "test results" "quality metrics" "test analyzer"
# Workflow Optimizer
python scripts/search-agents.sh "workflow optimizer" "process efficiency" "process improvement"
# Infrastructure Maintainer
python scripts/search-agents.sh "infrastructure maintainer" "production readiness" "infrastructure ops"
# Reality Checker
python scripts/search-agents.sh "reality checker" "final verdict" "integration testing"
```

- [ ] **Step 2: Compile gap report**

Document which roles have strong coverage (≥3 agents), which have weak (1-2), which are missing (0). Write findings to the plan as a comment.

- [ ] **Step 3: Identify which roles need new agents**

From gap report, determine the list of roles that need new dedicated agents. Expected: Reality Checker is the most likely gap.

---

### Task 4: Create missing hardening role agents

**Files:**
- Create: `_solution/_solution-reality-checker.md` (and 1-4 more based on gap analysis in Task 3)

**Interfaces:**
- Follows agent file anatomy from CLAUDE.md

- [ ] **Step 1: Create `_solution/_solution-reality-checker.md`**

Write the agent file following the standard anatomy:
- Required frontmatter: name, description, emoji, color
- Standard frontmatter: version, date_added, nexus_roles (phase-4-hardening)
- Body sections: Identity, Mission, Rules, Deliverables, Workflow
- Description references Reality Checker as "the final gate for NEXUS Phase 4"

- [ ] **Step 2: Create other missing role agents** (based on Task 3 gap report)

- [ ] **Step 3: Lint new agents**

Run: `python scripts/lint-agents.py _solution/_solution-reality-checker.md`
Expected: PASS

- [ ] **Step 4: Regenerate index**

Run: `python scripts/generate-index.py`
Expected: AGENTS.json updated

- [ ] **Step 5: Verify hardening count**

Run: `python scripts/nexus-orchestrator.py --stats`
Expected: hardening ≥ 180

- [ ] **Step 6: Commit**

---

## Track P2: Quality Governance

### Task 5: Auto-fix cross-category depends_on for flagged agents

**Files:**
- Modify: `scripts/analyze-deps.py` (extend `--apply` to target "no cross-category" subset)

**Interfaces:**
- Consumes: existing `--apply` logic, `agent-lifecycle.py --auto-flag` output
- Produces: `--apply --no-cross-category-only` mode

- [ ] **Step 1: Add `--no-cross-category-only` flag**

```python
# In analyze-deps.py main():
parser.add_argument("--no-cross-category-only", action="store_true",
                    help="Only apply deps to agents with no cross-category depends_on")
```

- [ ] **Step 2: Implement filtering logic in `--apply` branch**

```python
# In the --apply branch, add filtering before applying:
if args.no_cross_category_only:
    agents_to_fix = set()
    for agent_id, data in all_agents.items():
        deps = data.get("depends_on", [])
        has_cross = any(
            all_agents[d]["category"] != data["category"]
            for d in deps if d in all_agents
        )
        if not has_cross:
            agents_to_fix.add(agent_id)
    # Only apply to agents in agents_to_fix
```

- [ ] **Step 3: Dry-run to preview**

Run: `python scripts/analyze-deps.py --apply --no-cross-category-only --min-confidence 0.5 --dry-run`
Expected: List of agents that would receive cross-category deps

- [ ] **Step 4: Apply**

Run: `python scripts/analyze-deps.py --apply --no-cross-category-only --min-confidence 0.5`
Expected: cross-category deps added to ~51 agents

- [ ] **Step 5: Validate**

Run: `python scripts/analyze-deps.py --validate`
Expected: 0 broken references

Run: `python scripts/agent-lifecycle.py --auto-flag | grep "no cross-category"`
Expected: count reduced to 0

- [ ] **Step 6: Run full tests**

Run: `python -m pytest tests/ -v`
Expected: all PASS

- [ ] **Step 7: Commit**

---

### Task 6: Content expansion for thin agents

**Files:**
- Create: `scripts/expand-thin-agents.py`
- Test: `tests/test_expand_thin_agents.py`

**Interfaces:**
- Consumes: `_shared.frontmatter.*`, `_shared.discovery.discover_agents`, `_shared.atomic_write`
- Produces: CLI script with `--dry-run`, `--agent`, `--category`, `--all` flags

- [ ] **Step 1: Write the test**

```python
# tests/test_expand_thin_agents.py

class TestExpandThinAgents:
    def test_count_substantive_sections(self):
        """Verify section counting with synthetic agent content."""
        from scripts._shared.validators import count_substantive_sections
        body = """## Identity\nI am a tester.\n\n## Mission\nI test things.\n\n## Rules\nBe thorough."""
        assert count_substantive_sections(body) == 3

    def test_identify_missing_sections(self, tmp_path):
        from scripts._shared.validators import CORE_SECTIONS
        agent_file = tmp_path / "agent.md"
        agent_file.write_text(
            "---\nname: Test\n---\n## Identity\nI am a tester.\n\n## Rules\nBe thorough.",
            encoding="utf-8",
        )
        missing = mod.identify_missing_sections(agent_file)
        assert "Mission" in " ".join(str(m) for m in missing)

    def test_generate_section_template(self):
        agent = {"name": "Test Agent", "category": "testing", "body": "I test things."}
        template = mod.generate_section_template(agent, "Mission")
        assert "Mission" in template
        assert len(template) > 50

    def test_dry_run_no_write(self, tmp_path, monkeypatch):
        d = tmp_path / "testing"
        d.mkdir()
        f = d / "testing-example.md"
        f.write_text(
            "---\nname: Example\ndate_added: '2026-07-01'\n---\n## Identity\nI am an example.\n\n## Rules\nBe helpful.",
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "ROOT", tmp_path)
        # ... run with --dry-run, verify file unchanged
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_expand_thin_agents.py -v`
Expected: FAIL

- [ ] **Step 3: Write the script**

```python
#!/usr/bin/env python3
"""Expand thin agents (1-3 substantive sections) by generating missing sections.

Usage:
    python scripts/expand-thin-agents.py --dry-run              # preview
    python scripts/expand-thin-agents.py --agent <id>           # single agent
    python scripts/expand-thin-agents.py --category testing     # one category
    python scripts/expand-thin-agents.py --all                  # all thin agents
"""

import argparse
import sys
from pathlib import Path

from _shared import GREEN, RED, RESET, YELLOW, atomic_write
from _shared.discovery import discover_agents
from _shared.frontmatter import get_body
from _shared.validators import CORE_SECTIONS, count_substantive_sections

ROOT = Path(__file__).resolve().parent.parent

SECTION_TEMPLATES = {
    "Mission": """## 🎯 Your Core Mission

As a {name}, your mission is to {mission_hint}. You deliver value through:

- **[Core competency 1]**: [What this means in practice]
- **[Core competency 2]**: [How you apply this skill]  
- **[Core competency 3]**: [The outcome you drive]

Your work directly impacts [stakeholder/outcome].""",

    "Deliverables": """## 📦 Your Deliverables

For every engagement, you produce:

1. **[Deliverable Name]**: [Format + brief description]
2. **[Deliverable Name]**: [Format + brief description]
3. **[Deliverable Name]**: [Format + brief description]

Each deliverable follows your category's quality standards.""",

    "Workflow": """## 🔄 Your Workflow

Your standard process:

1. **Understand**: Review context and requirements
2. **Analyze**: Apply your domain expertise
3. **Produce**: Create deliverables to specification
4. **Validate**: Self-review against quality criteria
5. **Iterate**: Incorporate feedback and refine""",
}


def identify_missing_sections(filepath: Path) -> list[str]:
    body = get_body(filepath.read_text(encoding="utf-8"))
    existing = set()
    for section_name, patterns in CORE_SECTIONS.items():
        for pattern in patterns if isinstance(patterns, list) else [patterns]:
            if pattern.lower() in body.lower():
                existing.add(section_name)
                break
    return [s for s in SECTION_TEMPLATES if s not in existing]


def generate_section_template(agent_info: dict, section_name: str) -> str:
    template = SECTION_TEMPLATES.get(section_name, "")
    return template.format(
        name=agent_info.get("name", "expert"),
        mission_hint=agent_info.get("description", "delivering expert results"),
    )


def main():
    parser = argparse.ArgumentParser(description="Expand thin agents with missing sections")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--agent", "-a")
    parser.add_argument("--category", "-c")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if not any([args.agent, args.category, args.all]):
        print("Specify --agent, --category, or --all")
        sys.exit(1)

    # Discover agents to process
    # ... implementation

    # For each thin agent, identify missing sections, generate and insert
    # ... implementation


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Expand agent.py to be usable as a library**

Modify `_shared/__init__.py` to export `atomic_write` (already done). Ensure `expand-agent.py` core logic is importable.

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_expand_thin_agents.py -v`
Expected: PASS

- [ ] **Step 6: Dry-run + apply to thin agents**

Run: `python scripts/expand-thin-agents.py --all --dry-run`
Expected: List of agents and which sections would be added

Run: `python scripts/expand-thin-agents.py --all`
Expected: sections added to thin agents

- [ ] **Step 7: Validate**

Run: `python scripts/lint-agents.py --all --no-freshness`
Expected: no new errors
Run: `python scripts/agent-lifecycle.py --auto-flag | grep "only 1/7\|only 2/7\|only 3/7"`
Expected: count reduced

- [ ] **Step 8: Commit**

---

## Track P3: NEXUS Orchestration Tools

### Task 7: Build match-nexus-agents.py

**Files:**
- Create: `scripts/match-nexus-agents.py`
- Test: `tests/test_match_nexus_agents.py`

**Interfaces:**
- Consumes: `_shared.discovery.discover_agents`, `_shared.frontmatter.*`, `AGENTS.json` index
- Produces: `match_nexus_agents.main()` with `--project`, `--phase`, `--json` flags

- [ ] **Step 1: Write the test**

```python
# tests/test_match_nexus_agents.py

class TestMatchNexusAgents:
    def test_match_by_keywords(self):
        desc = "Build a secure web application with user authentication and API integration"
        matches = mod.match_agents(desc, all_agents={"test-agent": mock_agent()})
        assert len(matches) > 0

    def test_filter_by_phase(self):
        matches = mod.match_agents("build a website", phase="phase-3-build")
        for m in matches:
            assert "phase-3-build" in m.get("nexus_roles", [])

    def test_empty_description_returns_empty(self):
        assert mod.match_agents("") == []

    def test_json_output(self, capsys):
        # test --json flag produces valid JSON
        pass
```

- [ ] **Step 2: Write the script**

```python
#!/usr/bin/env python3
"""Match NEXUS agents to a project based on natural language description.

Usage:
    python scripts/match-nexus-agents.py --project "Build a mobile app with real-time chat"
    python scripts/match-nexus-agents.py --project "..." --phase phase-3-build
    python scripts/match-nexus-agents.py --project "..." --json
"""

# Core algorithm:
# 1. Tokenize project description into keywords
# 2. Score each agent by keyword match in body + description
# 3. Group top matches by NEXUS phase
# 4. Return roster
```

- [ ] **Step 3: Run tests, iterate until pass**

- [ ] **Step 4: Commit**

---

### Task 8: Build nexus-coverage.py

**Files:**
- Create: `scripts/nexus-coverage.py`
- Test: `tests/test_nexus_coverage.py`

**Interfaces:**
- Consumes: `_shared.discovery.discover_agents`, `_shared.frontmatter.get_list_field`
- Produces: `nexus_coverage.main()` with `--category`, `--gaps`, `--json` flags

- [ ] **Step 1: Write the test**

```python
# tests/test_nexus_coverage.py

class TestNexusCoverage:
    def test_phase_counts(self, tmp_path, monkeypatch):
        # Setup test agents with known nexus_roles
        d = tmp_path / "engineering"
        d.mkdir()
        (d / "agent1.md").write_text(
            "---\nname: A\nnexus_roles:\n  - phase-3-build\n  - phase-4-hardening\n---\nBody",
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "REPO", tmp_path)
        counts = mod.count_phase_coverage()
        assert counts["phase-3-build"] == 1
        assert counts["phase-4-hardening"] == 1

    def test_gap_detection(self, tmp_path, monkeypatch):
        # Setup agents missing a phase entirely
        d = tmp_path / "engineering"
        d.mkdir()
        (d / "agent1.md").write_text(
            "---\nname: A\nnexus_roles:\n  - phase-3-build\n---\nBody",
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "REPO", tmp_path)
        gaps = mod.find_gaps()
        assert "phase-0-discovery" in gaps  # no agent covers this

    def test_category_breakdown(self, tmp_path, monkeypatch):
        pass
```

- [ ] **Step 2: Write the script**

```python
#!/usr/bin/env python3
"""Visualize NEXUS phase coverage across all agents.

Usage:
    python scripts/nexus-coverage.py                  # full heatmap
    python scripts/nexus-coverage.py --category testing # single category
    python scripts/nexus-coverage.py --gaps            # show uncovered roles only
    python scripts/nexus-coverage.py --json            # machine-readable output
"""

# Output: per-phase bar chart showing agent count, category diversity score, role coverage %
```

- [ ] **Step 3: Run tests, iterate until pass**

- [ ] **Step 4: Verify with real data**

Run: `python scripts/nexus-coverage.py`
Run: `python scripts/nexus-coverage.py --gaps`
Expected: meaningful output showing coverage gaps

- [ ] **Step 5: Commit**

---

## Track P4: New Metadata Fields

### Task 9: Update frontmatter schema

**Files:**
- Modify: `schemas/agent-frontmatter.schema.json`

**Interfaces:**
- Consumes: existing schema
- Produces: updated schema with 4 new optional properties

- [ ] **Step 1: Add 4 new fields to schema properties**

```json
"tags": {
  "type": "array",
  "description": "Free-form tags for improved searchability.",
  "items": {"type": "string", "minLength": 1, "maxLength": 64},
  "uniqueItems": true
},
"keywords": {
  "type": "array",
  "description": "Structured search keywords used for ranking in search-agents.py.",
  "items": {"type": "string", "minLength": 2, "maxLength": 80},
  "uniqueItems": true
},
"complexity": {
  "type": "string",
  "enum": ["low", "medium", "high"],
  "description": "NEXUS scheduling weight — routes complex tasks to premium models."
},
"estimated_duration": {
  "type": "string",
  "maxLength": 32,
  "description": "Expected task duration hint (e.g., '2-4h', '1-2d')."
}
```

- [ ] **Step 2: Verify schema validity**

Run: `python -c "import json; json.load(open('schemas/agent-frontmatter.schema.json')); print('Valid JSON')"`
Expected: Valid JSON

- [ ] **Step 3: Commit**

---

### Task 10: Update linter to recognize new fields

**Files:**
- Modify: `scripts/lint-agents.py`
- Test: `tests/test_lint_agents.py`

**Interfaces:**
- Consumes: existing linter rules
- Produces: linter recognizes new fields (no errors for valid values)

- [ ] **Step 1: Find the `additionalProperties: false` check in lint-agents.py and update**

Read `scripts/lint-agents.py` to find where schema validation happens. The schema's `additionalProperties: false` means new fields won't cause errors. Only need to add optional validation warnings for invalid values.

```python
# Add to lint-agents.py — validate new field values if present
KNOWN_TAGS = set()  # populated from existing agents over time
KNOWN_KEYWORDS = set()

def validate_complexity(value: str) -> list[str]:
    if value not in ("low", "medium", "high"):
        return [f"complexity must be low/medium/high, got '{value}'"]
    return []
```

- [ ] **Step 2: Add test for new field validation**

```python
# tests/test_lint_agents.py

def test_tags_field_accepted(self, tmp_path):
    f = tmp_path / "agent.md"
    f.write_text(
        "---\nname: Test\ndescription: A test agent\nemoji: 🎯\ncolor: blue\n"
        "tags:\n  - cloud\n  - security\n---\n## Identity\nI am a test.\n\n"
        "## Mission\nI test things.\n\n## Rules\nBe thorough.\n",
        encoding="utf-8",
    )
    # Should pass lint without errors

def test_invalid_complexity_warns(self, tmp_path):
    pass
```

- [ ] **Step 3: Run linter tests**

Run: `python -m pytest tests/test_lint_agents.py -v`
Expected: all PASS

- [ ] **Step 4: Commit**

---

### Task 11: Update search to weight new fields

**Files:**
- Modify: `scripts/search-agents.py`
- Test: `tests/test_search_agents.py`

**Interfaces:**
- Consumes: existing search logic
- Produces: search ranks higher for `tags` and `keywords` matches

- [ ] **Step 1: Add tag/keyword scoring to search ranking**

```python
# In search-agents.py scoring logic:
TAG_MATCH_BONUS = 2.0    # exact tag match
KEYWORD_MATCH_BONUS = 1.5  # partial keyword match

def score_agent(query_terms, agent_data):
    base_score = existing_scoring(query_terms, agent_data)
    # Add tag bonus
    for tag in agent_data.get("tags", []):
        if any(term.lower() in tag.lower() for term in query_terms):
            base_score += TAG_MATCH_BONUS
    # Add keyword bonus
    for kw in agent_data.get("keywords", []):
        if any(term.lower() in kw.lower() for term in query_terms):
            base_score += KEYWORD_MATCH_BONUS
    return base_score
```

- [ ] **Step 2: Add test**

```python
# tests/test_search_agents.py

def test_tag_boost(self):
    results = search("kubernetes", agents_with_tags=[...])
    # agent with tag "kubernetes" should rank above agent without
```

- [ ] **Step 3: Run search tests**

Run: `python -m pytest tests/test_search_agents.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

---

### Task 12: Batch-populate new fields

**Files:**
- Create: `scripts/batch-add-metadata.py`

**Interfaces:**
- Consumes: `_shared.*`, `suggest-nexus-roles.analyze_agent`
- Produces: `--dry-run`, `--field tags|keywords|complexity|duration`, `--category`

- [ ] **Step 1: Write the script**

Auto-populate:
- `tags`: extract from agent body keywords (category name, key concepts)
- `keywords`: extract from description + section headers
- `complexity`: infer from category (director/chief → high, coordinator → medium, else low)
- `estimated_duration`: infer from complexity (high → "4-8h", medium → "2-4h", low → "1-2h")

- [ ] **Step 2: Dry-run + apply**

Run: `python scripts/batch-add-metadata.py --dry-run --field tags`
Expected: preview of tags for each agent

Run: `python scripts/batch-add-metadata.py --field tags`
Expected: tags added to agents

- [ ] **Step 3: Validate**

Run: `python scripts/lint-agents.py --all --no-freshness`
Expected: no new errors

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest tests/ --cov=scripts`
Expected: all PASS

- [ ] **Step 5: Final commit**

---

## Success Verification

After all tracks complete, run these checks:

- [ ] `python scripts/nexus-orchestrator.py --stats` — hardening ≥ 180
- [ ] `python scripts/agent-lifecycle.py --auto-flag | grep "no cross-category"` — count = 0
- [ ] `python scripts/agent-lifecycle.py --auto-flag | grep "only 1/7\|only 2/7\|only 3/7"` — count < 10
- [ ] `python scripts/nexus-coverage.py --gaps` — no critical gaps remaining
- [ ] `python scripts/match-nexus-agents.py --project "build a secure web app"` — returns valid roster
- [ ] `python scripts/lint-agents.py --all --no-freshness` — no new errors
- [ ] `python scripts/analyze-deps.py --validate` — 0 broken references
- [ ] `python -m pytest tests/ --cov=scripts` — all PASS, coverage maintained
