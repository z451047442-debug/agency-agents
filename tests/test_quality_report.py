"""Tests for scripts/quality-report.py — quality dashboard and fix estimation."""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "quality_report", str(SCRIPTS_DIR / "quality-report.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

_estimate_fix_effort = mod._estimate_fix_effort
build_report = mod.build_report
print_agent_detail = mod.print_agent_detail


def _make_agent(scores=None, broken_links=0, lint_errors=0,
                lint_warnings=0, security_flags=0, word_count=200,
                sections_found=4, file_size_kb=3.0, issues=None,
                agent_id="test-agent", category="testing", grade="B", total=5):
    return {
        "id": agent_id,
        "category": category,
        "grade": grade,
        "total": total,
        "word_count": word_count,
        "sections_found": sections_found,
        "file_size_kb": file_size_kb,
        "scores": scores or {"content_depth": 3, "structure": 3, "frontmatter": 2, "file_health": 2},
        "broken_links": broken_links,
        "lint_errors": lint_errors,
        "lint_warnings": lint_warnings,
        "security_flags": security_flags,
        "issues": issues or [],
        "path": f"{category}/{agent_id}.md",
    }


class TestEstimateFixEffort:
    def test_all_good_returns_done(self):
        report = {
            "scores": {"content_depth": 3, "structure": 3, "frontmatter": 2, "file_health": 2},
            "broken_links": 0,
            "lint_errors": 0,
            "lint_warnings": 0,
            "security_flags": 0,
        }
        level, fixes = _estimate_fix_effort(report)
        assert level == "done"
        assert fixes == []

    def test_low_frontmatter_is_easy(self):
        report = {
            "scores": {"frontmatter": 0, "content_depth": 3, "structure": 3, "file_health": 2},
            "broken_links": 0, "lint_errors": 0, "lint_warnings": 0, "security_flags": 0,
        }
        level, fixes = _estimate_fix_effort(report)
        assert level == "easy"

    def test_low_structure_is_moderate(self):
        report = {
            "scores": {"frontmatter": 2, "content_depth": 3, "structure": 1, "file_health": 2},
            "broken_links": 0, "lint_errors": 0, "lint_warnings": 0, "security_flags": 0,
        }
        level, fixes = _estimate_fix_effort(report)
        assert level == "moderate"

    def test_low_content_depth_is_hard(self):
        report = {
            "scores": {"frontmatter": 2, "structure": 3, "content_depth": 1, "file_health": 2},
            "broken_links": 0, "lint_errors": 0, "lint_warnings": 0, "security_flags": 0,
        }
        level, fixes = _estimate_fix_effort(report)
        assert level == "hard"

    def test_lint_errors_is_hard(self):
        report = {
            "scores": {"frontmatter": 2, "structure": 3, "content_depth": 3, "file_health": 2},
            "broken_links": 0, "lint_errors": 5, "lint_warnings": 0, "security_flags": 0,
        }
        level, fixes = _estimate_fix_effort(report)
        assert level == "hard"

    def test_broken_links_is_easy(self):
        report = {
            "scores": {"frontmatter": 2, "structure": 3, "content_depth": 3, "file_health": 2},
            "broken_links": 3, "lint_errors": 0, "lint_warnings": 0, "security_flags": 0,
        }
        level, fixes = _estimate_fix_effort(report)
        assert level == "easy"

    def test_security_flags_is_moderate(self):
        report = {
            "scores": {"frontmatter": 2, "structure": 3, "content_depth": 3, "file_health": 2},
            "broken_links": 0, "lint_errors": 0, "lint_warnings": 0, "security_flags": 1,
        }
        level, fixes = _estimate_fix_effort(report)
        assert level == "moderate"

    def test_hard_takes_priority(self):
        report = {
            "scores": {"frontmatter": 0, "structure": 1, "content_depth": 1, "file_health": 1},
            "broken_links": 5, "lint_errors": 3, "lint_warnings": 5, "security_flags": 2,
        }
        level, fixes = _estimate_fix_effort(report)
        assert level == "hard"

    def test_fixes_are_tuples(self):
        report = {
            "scores": {"frontmatter": 0, "structure": 0, "content_depth": 0, "file_health": 0},
            "broken_links": 0, "lint_errors": 0, "lint_warnings": 0, "security_flags": 0,
        }
        level, fixes = _estimate_fix_effort(report)
        for f in fixes:
            assert isinstance(f, tuple)
            assert len(f) == 2
            assert f[0] in ("easy", "moderate", "hard")


class TestBuildReport:
    def test_builds_for_all_agents(self):
        agents = build_report()
        assert isinstance(agents, dict)
        assert len(agents) > 0

    def test_each_agent_has_required_keys(self):
        agents = build_report()
        for agent_id, a in list(agents.items())[:5]:
            assert "id" in a
            assert "category" in a
            assert "grade" in a
            assert "scores" in a

    def test_category_filter(self):
        agents = build_report(category_filter="engineering")
        for agent_id, a in agents.items():
            assert a["category"] == "engineering"

    def test_agent_filter(self):
        agents = build_report(agent_filter="engineering-frontend-developer")
        assert len(agents) == 1
        agent_id = list(agents.keys())[0]
        assert agent_id == "engineering-frontend-developer"


class TestEstimateFixEffortExtra:
    """Additional edge cases for _estimate_fix_effort."""

    def test_low_file_health_is_moderate(self):
        report = _make_agent(
            scores={"frontmatter": 2, "structure": 3, "content_depth": 3, "file_health": 1})
        level, fixes = _estimate_fix_effort(report)
        assert level == "moderate"
        assert any("file size" in f[1].lower() for f in fixes)

    def test_many_lint_warnings_is_moderate(self):
        report = _make_agent(lint_warnings=5)
        level, fixes = _estimate_fix_effort(report)
        assert level == "moderate"
        assert any("warning" in f[1].lower() for f in fixes)

    def test_few_lint_warnings_not_moderate(self):
        report = _make_agent(lint_warnings=2)
        level, fixes = _estimate_fix_effort(report)
        # 2 warnings alone shouldn't trigger moderate (frontmatter/structure are fine)
        assert level == "done"

    def test_fix_items_include_specific_counts(self):
        report = _make_agent(security_flags=3, broken_links=2, lint_errors=4)
        level, fixes = _estimate_fix_effort(report)
        assert any("3" in f[1] and "security" in f[1].lower() for f in fixes)
        assert any("2" in f[1] and "broken" in f[1].lower() for f in fixes)
        assert any("4" in f[1] and "error" in f[1].lower() for f in fixes)


class TestPrintAgentDetail:
    def test_prints_agent_header(self, capsys):
        agent = _make_agent(agent_id="testing-tester")
        print_agent_detail(agent)
        captured = capsys.readouterr()
        assert "testing-tester" in captured.out

    def test_prints_category_and_grade(self, capsys):
        agent = _make_agent(category="engineering", grade="A", total=9)
        print_agent_detail(agent)
        captured = capsys.readouterr()
        assert "engineering" in captured.out
        assert "A" in captured.out
        assert "9/10" in captured.out

    def test_clean_agent_shows_no_lint_issues(self, capsys):
        agent = _make_agent()
        print_agent_detail(agent)
        captured = capsys.readouterr()
        assert "Clean" in captured.out

    def test_agent_with_errors_shows_them(self, capsys):
        agent = _make_agent(lint_errors=3, lint_warnings=1,
                           scores={"content_depth": 1, "structure": 2,
                                   "frontmatter": 1, "file_health": 2})
        print_agent_detail(agent)
        captured = capsys.readouterr()
        assert "3 error" in captured.out
        assert "1 warning" in captured.out

    def test_agent_with_issues_shows_them(self, capsys):
        agent = _make_agent(issues=["Missing Identity section", "Short content"])
        print_agent_detail(agent)
        captured = capsys.readouterr()
        assert "Missing Identity section" in captured.out
        assert "Issues" in captured.out

    def test_done_agent_no_fix_section(self, capsys):
        agent = _make_agent(grade="A", total=9)
        print_agent_detail(agent)
        captured = capsys.readouterr()
        assert "Recommended Fixes" not in captured.out
