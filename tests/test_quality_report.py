"""Tests for scripts/quality-report.py — quality dashboard and fix estimation."""

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

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
print_dashboard = mod.print_dashboard
print_json_report = mod.print_json_report
main = mod.main


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

    def test_with_security_flags_shows_warning(self, capsys):
        """Line 272: agent with security_flags > 0 shows security warning."""
        agent = _make_agent(security_flags=2)
        print_agent_detail(agent)
        captured = capsys.readouterr()
        assert "security flag" in captured.out

    def test_no_security_flags_shows_clean(self, capsys):
        agent = _make_agent(security_flags=0)
        print_agent_detail(agent)
        captured = capsys.readouterr()
        assert "No security flags" in captured.out

    def test_with_days_since_modified(self, capsys):
        """Lines 278-281: agent with days_since_modified shows freshness."""
        agent = _make_agent()
        agent["days_since_modified"] = 30
        agent["last_modified"] = "2026-06-10"
        print_agent_detail(agent)
        captured = capsys.readouterr()
        assert "Last Modified" in captured.out
        assert "2026-06-10" in captured.out
        assert "30 days ago" in captured.out

    def test_with_days_since_modified_over_365(self, capsys):
        """Lines 278-281: stale agent over 365 days shows >1 year."""
        agent = _make_agent()
        agent["days_since_modified"] = 400
        agent["last_modified"] = "2025-06-01"
        print_agent_detail(agent)
        captured = capsys.readouterr()
        assert "400 days ago (>1 year)" in captured.out


class TestPrintDashboard:
    """Tests for print_dashboard() covering lines 131-220."""

    def _make_args(self, category=None, fixable=False):
        """Create a mock args object."""
        class Args:
            pass
        args = Args()
        args.category = category
        args.fixable = fixable
        return args

    def _make_agent(self, agent_id="test", category="testing", grade="A", total=9,
                    word_count=500, broken_links=0, lint_errors=0, lint_warnings=0,
                    security_flags=0, issues=None, scores=None,
                    days_since_modified=None, last_modified=None):
        """Helper matching the structure from build_report."""
        return {
            "id": agent_id,
            "category": category,
            "grade": grade,
            "total": total,
            "word_count": word_count,
            "broken_links": broken_links,
            "lint_errors": lint_errors,
            "lint_warnings": lint_warnings,
            "security_flags": security_flags,
            "issues": issues or [],
            "scores": scores or {"content_depth": 3, "structure": 3,
                                 "frontmatter": 2, "file_health": 2},
            "sections_found": 5,
            "file_size_kb": 3.0,
            "days_since_modified": days_since_modified,
            "last_modified": last_modified,
            "path": f"{category}/{agent_id}.md",
        }

    def test_empty_agents(self, capsys):
        """Line 132-133: empty agents dict prints message and returns."""
        print_dashboard({}, self._make_args())
        captured = capsys.readouterr()
        assert "No agents found" in captured.out

    def test_dashboard_header(self, capsys):
        """Lines 149-155: dashboard shows header with generated date and count."""
        agents = {"a": self._make_agent("a", "testing")}
        print_dashboard(agents, self._make_args())
        captured = capsys.readouterr()
        assert "Unified Quality Dashboard" in captured.out

    def test_dashboard_with_category(self, capsys):
        """Line 153-154: dashboard shows category filter."""
        agents = {"a": self._make_agent("a", "engineering")}
        print_dashboard(agents, self._make_args(category="engineering"))
        captured = capsys.readouterr()
        assert "Category: engineering" in captured.out

    def test_overall_health_pass(self, capsys):
        """Line 159-160: quality gate PASS when A/B >= 60%."""
        agents = {
            "a1": self._make_agent("a1", "t", "A", 9),
            "a2": self._make_agent("a2", "t", "B", 6),
            "a3": self._make_agent("a3", "t", "C", 4),
        }
        print_dashboard(agents, self._make_args())
        captured = capsys.readouterr()
        assert "PASS" in captured.out

    def test_overall_health_fail(self, capsys):
        """Lines 159-160: quality gate FAIL when A/B < 60%."""
        agents = {
            "a1": self._make_agent("a1", "t", "C", 4),
            "a2": self._make_agent("a2", "t", "D", 2),
            "a3": self._make_agent("a3", "t", "D", 1),
        }
        print_dashboard(agents, self._make_args())
        captured = capsys.readouterr()
        assert "FAIL" in captured.out

    def test_grade_distribution(self, capsys):
        """Lines 161-165: grade distribution shown with counts."""
        agents = {
            "a1": self._make_agent("a1", "t", "A", 9),
            "a2": self._make_agent("a2", "t", "B", 7),
            "a3": self._make_agent("a3", "t", "C", 4),
            "a4": self._make_agent("a4", "t", "D", 1),
        }
        print_dashboard(agents, self._make_args())
        captured = capsys.readouterr()
        assert "Grade Distribution" in captured.out

    def test_improvement_landscape(self, capsys):
        """Lines 168-172: improvement landscape shows effort groups."""
        agents = {
            "a1": self._make_agent("a1", "t", "A", 10),
            "a2": self._make_agent("a2", "t", "B", 6, broken_links=5),
            "a3": self._make_agent("a3", "t", "C", 4, lint_warnings=5),
            "a4": self._make_agent("a4", "t", "D", 1, lint_errors=5),
        }
        print_dashboard(agents, self._make_args())
        captured = capsys.readouterr()
        assert "Improvement Landscape" in captured.out

    def test_category_health(self, capsys):
        """Lines 175-188: category health section with sorted categories."""
        agents = {
            "a1": self._make_agent("a1", "engineering", "A", 9),
            "a2": self._make_agent("a2", "design", "B", 7),
        }
        print_dashboard(agents, self._make_args())
        captured = capsys.readouterr()
        assert "Category Health" in captured.out

    def test_category_health_with_d_agents(self, capsys):
        """Lines 175-188: category health with D-grade agents."""
        agents = {
            "a1": self._make_agent("a1", "testing", "D", 1),
            "a2": self._make_agent("a2", "testing", "C", 3),
            "a3": self._make_agent("a3", "testing", "B", 6),
        }
        print_dashboard(agents, self._make_args())
        captured = capsys.readouterr()
        assert "Category Health" in captured.out

    def test_fixable_section(self, capsys):
        """Lines 191-206: --fixable shows top improvement opportunities."""
        agents = {
            "a1": self._make_agent("a1", "t", "B", 6, broken_links=3),
            "a2": self._make_agent("a2", "t", "C", 4, lint_warnings=5),
        }
        print_dashboard(agents, self._make_args(fixable=True))
        captured = capsys.readouterr()
        assert "Top Improvement Opportunities" in captured.out

    def test_fixable_skips_done_agents(self, capsys):
        """Line 201-202: done-grade agents skipped in fixable list."""
        agents = {
            "a1": self._make_agent("a1", "t", "A", 10),
        }
        print_dashboard(agents, self._make_args(fixable=True))
        captured = capsys.readouterr()
        assert "Top Improvement Opportunities" in captured.out
        # a1 is done, should not appear as a fix item
        # The fixable section header prints, but no agent entries follow

    def test_security_flagged_agents(self, capsys):
        """Lines 208-213: security-flagged agents get their own section."""
        agents = {
            "a1": self._make_agent("a1", "t", "A", 9, security_flags=3),
        }
        print_dashboard(agents, self._make_args())
        captured = capsys.readouterr()
        assert "Security-Flagged Agents" in captured.out

    def test_no_security_flagged_agents(self, capsys):
        """Line 210: no sec_flagged agents => section skipped."""
        agents = {
            "a1": self._make_agent("a1", "t", "A", 9, security_flags=0),
        }
        print_dashboard(agents, self._make_args())
        captured = capsys.readouterr()
        assert "Security-Flagged Agents" not in captured.out

    def test_needs_attention_perimeter(self, capsys):
        """Lines 216-222: needs attention section with short/stale/broken counts."""
        agents = {
            "a1": self._make_agent("a1", "t", "A", 9, word_count=50),
            "a2": self._make_agent("a2", "t", "B", 7, days_since_modified=400),
            "a3": self._make_agent("a3", "t", "C", 4, broken_links=2),
        }
        print_dashboard(agents, self._make_args())
        captured = capsys.readouterr()
        assert "Needs Attention" in captured.out

    def test_category_with_many_issues(self, capsys):
        """Line 187: issues > count triggers flag display."""
        agents = {
            "a1": self._make_agent("a1", "testing", "C", 3,
                                   issues=["issue1", "issue2"]),
            "a2": self._make_agent("a2", "testing", "C", 3,
                                   issues=["issue3", "issue4"]),
        }
        print_dashboard(agents, self._make_args())
        captured = capsys.readouterr()
        # 4 issues > 2 agents => flag shown
        assert "issues" in captured.out.lower()


class TestPrintJsonReport:
    """Tests for print_json_report() covering lines 286-310."""

    def _make_agent(self, agent_id="test", category="testing", grade="A", total=9,
                    word_count=500, lint_errors=0, lint_warnings=0,
                    security_flags=0, issues=None, scores=None):
        return {
            "id": agent_id,
            "category": category,
            "grade": grade,
            "total": total,
            "word_count": word_count,
            "lint_errors": lint_errors,
            "lint_warnings": lint_warnings,
            "security_flags": security_flags,
            "issues": issues or [],
            "scores": scores or {"content_depth": 3, "structure": 3,
                                 "frontmatter": 2, "file_health": 2},
            "path": f"{category}/{agent_id}.md",
        }

    def test_outputs_valid_json(self, capsys):
        """Line 309: valid JSON output with all fields."""
        agents = {"test": self._make_agent()}
        print_json_report(agents)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["total_agents"] == 1
        assert len(data["agents"]) == 1
        a = data["agents"][0]
        assert a["id"] == "test"
        assert a["grade"] == "A"
        assert "fix_effort" in a
        assert "fixes" in a

    def test_outputs_multiple_agents(self, capsys):
        agents = {
            "a1": self._make_agent("a1", "t1", "A", 9),
            "a2": self._make_agent("a2", "t2", "B", 6, lint_errors=2),
        }
        print_json_report(agents)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["total_agents"] == 2
        assert len(data["agents"]) == 2

    def test_includes_generated_date(self, capsys):
        agents = {"test": self._make_agent()}
        print_json_report(agents)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "generated" in data


class TestMain:
    """Tests for main() covering lines 314-344."""

    def test_main_default_dashboard(self, monkeypatch, capsys):
        """Line 344: default mode calls print_dashboard."""
        dashboard_called = []
        monkeypatch.setattr(mod, "build_report",
                           lambda **kw: {"test": "agent"})
        monkeypatch.setattr(mod, "print_dashboard",
                           lambda agents, args: dashboard_called.append(True))
        monkeypatch.setattr(sys, "argv", ["quality-report.py"])
        mod.main()
        assert len(dashboard_called) == 1

    def test_main_json_mode(self, monkeypatch, capsys):
        """Lines 334-335: --json flag calls print_json_report."""
        json_called = []
        monkeypatch.setattr(mod, "build_report",
                           lambda **kw: {"test": "agent"})
        monkeypatch.setattr(mod, "print_json_report",
                           lambda agents: json_called.append(True))
        monkeypatch.setattr(sys, "argv", ["quality-report.py", "--json"])
        mod.main()
        assert len(json_called) == 1

    def test_main_agent_found(self, monkeypatch, capsys):
        """Lines 336-339: --agent flag found => print_agent_detail."""
        detail_called = []
        monkeypatch.setattr(mod, "build_report",
                           lambda **kw: {"target": {"id": "target"}})
        monkeypatch.setattr(mod, "print_agent_detail",
                           lambda agent: detail_called.append(agent))
        monkeypatch.setattr(sys, "argv", ["quality-report.py", "--agent", "target"])
        mod.main()
        assert len(detail_called) == 1
        assert detail_called[0]["id"] == "target"

    def test_main_agent_not_found(self, monkeypatch, capsys):
        """Lines 340-342: --agent not found => stderr + exit 1."""
        monkeypatch.setattr(mod, "build_report",
                           lambda **kw: {})
        monkeypatch.setattr(sys, "argv", ["quality-report.py", "--agent", "nonexistent"])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 1

    def test_main_passes_category_filter(self, monkeypatch):
        """--category filter is forwarded to build_report."""
        build_calls = []

        def _track(**kw):
            build_calls.append(kw)
            return {}

        monkeypatch.setattr(mod, "build_report", _track)
        monkeypatch.setattr(mod, "print_dashboard", lambda agents, args: None)
        monkeypatch.setattr(sys, "argv",
                           ["quality-report.py", "--category", "engineering"])
        mod.main()
        assert build_calls[0].get("category_filter") == "engineering"

    def test_main_no_freshness_flag(self, monkeypatch):
        """--no-freshness sets check_freshness=False."""
        build_calls = []

        def _track(**kw):
            build_calls.append(kw)
            return {}

        monkeypatch.setattr(mod, "build_report", _track)
        monkeypatch.setattr(mod, "print_dashboard", lambda agents, args: None)
        monkeypatch.setattr(sys, "argv",
                           ["quality-report.py", "--no-freshness"])
        mod.main()
        assert build_calls[0].get("check_freshness") is False

    def test_main_with_fixable_flag(self, monkeypatch):
        """--fixable flag is parsed and print_dashboard receives it."""
        dashboard_calls = []

        def _dash(agents, args):
            dashboard_calls.append(args)

        monkeypatch.setattr(mod, "build_report",
                           lambda **kw: {"test": "agent"})
        monkeypatch.setattr(mod, "print_dashboard", _dash)
        monkeypatch.setattr(sys, "argv", ["quality-report.py", "--fixable"])
        mod.main()
        assert dashboard_calls[0].fixable is True

    def test_lines_30_32_encoding_reconfigure(self, monkeypatch):
        """Lines 30, 32: stdout/stderr reconfigure when encoding is not utf-8."""
        import importlib
        old_stdout_enc = sys.stdout.encoding
        old_stderr_enc = sys.stderr.encoding

        class FakeStream(io.StringIO):
            encoding = "ascii"
            def reconfigure(self, **kw):
                self._reconfigured = True

        fake_out = FakeStream()
        fake_err = FakeStream()
        monkeypatch.setattr(sys, "stdout", fake_out)
        monkeypatch.setattr(sys, "stderr", fake_err)

        # Re-import the module to trigger the reconfigure logic
        spec2 = importlib.util.spec_from_file_location(
            "quality_report_enc", str(SCRIPTS_DIR / "quality-report.py")
        )
        mod2 = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(mod2)

        assert getattr(fake_out, "_reconfigured", False) is True
        assert getattr(fake_err, "_reconfigured", False) is True
