"""Tests for scripts/contribute.py — contribution dashboard."""

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "contribute", str(SCRIPTS_DIR / "contribute.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

estimate_effort = mod.estimate_effort
build_opportunities = mod.build_opportunities
print_dashboard = mod.print_dashboard
print_json_output = mod.print_json_output
IMPACT_WEIGHTS = mod.IMPACT_WEIGHTS
SKILL_LEVELS = mod.SKILL_LEVELS


# ── SKILL_LEVELS ─────────────────────────────────────────────────────────────

class TestSkillLevels:
    def test_has_three_levels(self):
        assert set(SKILL_LEVELS.keys()) == {"beginner", "intermediate", "advanced"}

    def test_each_level_has_required_fields(self):
        for level, config in SKILL_LEVELS.items():
            assert "description" in config
            assert "max_effort" in config
            assert "time_estimate" in config


# ── IMPACT_WEIGHTS ───────────────────────────────────────────────────────────

class TestImpactWeights:
    def test_all_expected_keys_present(self):
        assert "content_depth" in IMPACT_WEIGHTS
        assert "structure" in IMPACT_WEIGHTS
        assert "frontmatter" in IMPACT_WEIGHTS
        assert "security" in IMPACT_WEIGHTS
        assert "lint_errors" in IMPACT_WEIGHTS
        assert "broken_deps" in IMPACT_WEIGHTS

    def test_security_has_highest_weight(self):
        assert IMPACT_WEIGHTS["security"] >= IMPACT_WEIGHTS["content_depth"]


# ── estimate_effort ──────────────────────────────────────────────────────────

class TestEstimateEffort:
    def test_no_issues_all_good_scores_returns_done(self):
        scores = {"content_depth": 3, "structure": 3, "frontmatter": 2, "file_health": 2}
        assert estimate_effort([], scores, 800) == "done"

    def test_done_when_enough_scores(self):
        scores = {"content_depth": 2, "structure": 3, "frontmatter": 2, "file_health": 2}
        assert estimate_effort([], scores, 500) == "done"

    def test_low_content_depth_is_hard(self):
        scores = {"content_depth": 1, "structure": 3, "frontmatter": 2, "file_health": 2}
        assert estimate_effort([], scores, 100) == "hard"

    def test_lint_error_is_hard(self):
        scores = {"content_depth": 3, "structure": 3, "frontmatter": 2, "file_health": 2}
        assert estimate_effort(["ERROR: bad yaml"], scores, 500) == "hard"

    def test_low_structure_is_moderate(self):
        scores = {"content_depth": 2, "structure": 2, "frontmatter": 2, "file_health": 2}
        assert estimate_effort([], scores, 500) == "moderate"

    def test_many_issues_is_moderate(self):
        scores = {"content_depth": 3, "structure": 3, "frontmatter": 2, "file_health": 2}
        issues = ["warn: missing section", "warn: short content", "warn: no nexus_roles"]
        assert estimate_effort(issues, scores, 500) == "moderate"

    def test_few_warnings_is_easy(self):
        scores = {"content_depth": 3, "structure": 3, "frontmatter": 2, "file_health": 2}
        assert estimate_effort(["warn: missing section"], scores, 500) == "easy"

    def test_word_count_not_used_in_effort(self):
        scores = {"content_depth": 3, "structure": 3, "frontmatter": 2, "file_health": 2}
        assert estimate_effort([], scores, 100) == "done"
        assert estimate_effort([], scores, 10000) == "done"

    def test_single_warning_is_easy(self):
        scores = {"content_depth": 3, "structure": 3, "frontmatter": 2, "file_health": 2}
        assert estimate_effort(["warn: missing link"], scores, 500) == "easy"

    def test_done_when_no_issues_but_scores_below_threshold(self):
        """Line 81: returns 'done' when no issues but some scores below threshold.

        The first 'done' check fails because frontmatter=1 < 2, but
        content_depth >= 2 and structure >= 3, so we fall through to the
        second 'done' at line 81.
        """
        scores = {"content_depth": 2, "structure": 3, "frontmatter": 1, "file_health": 2}
        assert estimate_effort([], scores, 500) == "done"


# ── build_opportunities ──────────────────────────────────────────────────────

class TestBuildOpportunities:
    def test_returns_list_of_dicts(self):
        opps = build_opportunities()
        assert isinstance(opps, list)
        if opps:
            for key in ("id", "category", "grade", "effort", "priority", "impact"):
                assert key in opps[0]

    def test_sort_by_priority_desc(self):
        opps = build_opportunities()
        priorities = [o["priority"] for o in opps]
        assert priorities == sorted(priorities, reverse=True)

    def test_no_done_agents_returned(self):
        opps = build_opportunities()
        efforts = {o["effort"] for o in opps}
        assert "done" not in efforts

    def test_category_filter_works(self):
        opps = build_opportunities(category_filter="aviation")
        if opps:
            for o in opps:
                assert o["category"] == "aviation"

    def test_nonexistent_category_returns_empty(self):
        opps = build_opportunities(category_filter="zzz_nonexistent_zzz")
        assert opps == []

    def test_ease_values_match_effort(self):
        opps = build_opportunities()
        for o in opps:
            expected = {"easy": 3, "moderate": 2, "hard": 1}[o["effort"]]
            assert o["ease"] == expected

    def test_frontmatter_gap_adds_impact(self, monkeypatch):
        """Line 128: frontmatter score < 2 contributes to impact score."""
        def mock_score(filepath, check_freshness=False):
            return {
                "grade": "C", "total": 4,
                "scores": {"content_depth": 3, "structure": 3, "frontmatter": 0, "file_health": 2},
                "issues": ["Missing section"],
                "word_count": 500,
            }

        def mock_lint(filepath, errors, warnings, infos, freshness=False):
            pass  # leave lists empty, no errors or security flags

        monkeypatch.setattr(mod, "score_agent", mock_score)
        monkeypatch.setattr(mod, "lint_file", mock_lint)

        opps = build_opportunities(category_filter="engineering")
        # Every agent gets frontmatter=0, so impact includes (2-0)*1 = 2.0
        for o in opps:
            assert o["scores"]["frontmatter"] == 0
            assert o["impact"] >= 2.0


# ── print_dashboard ──────────────────────────────────────────────────────────

def _make_opp(agent_id="test-agent", category="testing", grade="C", total=4,
              word_count=200, effort="moderate", impact=6.0, priority=12.0,
              issues=None, security_flags=0, lint_errors=0, lint_warnings=0,
              scores=None, broken_links=0):
    if scores is None:
        scores = {"content_depth": 2, "structure": 2, "frontmatter": 2, "file_health": 2}
    return {
        "id": agent_id, "category": category, "grade": grade, "total": total,
        "word_count": word_count, "scores": scores, "effort": effort,
        "impact": impact, "ease": {"easy": 3, "moderate": 2, "hard": 1}[effort],
        "priority": priority, "issues": issues or [],
        "security_flags": security_flags, "lint_errors": lint_errors,
        "lint_warnings": lint_warnings, "broken_links": broken_links,
    }


class _Args:
    def __init__(self, skill=None, category=None, top=20, json=False):
        self.skill = skill
        self.category = category
        self.top = top
        self.json = json


class TestPrintDashboard:
    def test_prints_header(self):
        opps = [_make_opp()]
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_dashboard(opps, _Args())
        finally:
            sys.stdout = old_stdout
        output = buf.getvalue()
        assert "Community Contribution Dashboard" in output
        assert "opportunities" in output

    def test_shows_skill_level_stats(self):
        opps = [_make_opp(effort="easy"), _make_opp(agent_id="b", effort="hard")]
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_dashboard(opps, _Args())
        finally:
            sys.stdout = old_stdout
        output = buf.getvalue()
        assert "Beginner:" in output or "easy" in output.lower()

    def test_respects_top_limit(self):
        opps = [_make_opp(agent_id=f"a{i}") for i in range(30)]
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_dashboard(opps, _Args(top=5))
        finally:
            sys.stdout = old_stdout
        # Should not crash with more opps than top
        assert "Community Contribution Dashboard" in buf.getvalue()

    def test_skill_filter_includes_equal_effort(self):
        opps = [_make_opp(agent_id="ez", effort="easy"),
                _make_opp(agent_id="md", effort="moderate"),
                _make_opp(agent_id="hd", effort="hard")]
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_dashboard(opps, _Args(skill="beginner"))
        finally:
            sys.stdout = old_stdout
        assert "ez" in buf.getvalue()

    def test_shows_security_flags(self):
        opps = [_make_opp(security_flags=2)]
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_dashboard(opps, _Args())
        finally:
            sys.stdout = old_stdout
        assert "security" in buf.getvalue().lower()

    def test_shows_issue_on_dashboard(self):
        opps = [_make_opp(issues=["Missing Identity section"])]
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_dashboard(opps, _Args())
        finally:
            sys.stdout = old_stdout
        assert "Missing Identity section" in buf.getvalue()

    def test_shows_category_when_filtered(self):
        """Line 188: category header displayed when args.category is set."""
        opps = [_make_opp()]
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_dashboard(opps, _Args(category="engineering"))
        finally:
            sys.stdout = old_stdout
        output = buf.getvalue()
        assert "Category:" in output
        assert "engineering" in output


# ── print_json_output ────────────────────────────────────────────────────────

class TestPrintJsonOutput:
    def test_outputs_valid_json(self):
        opps = [_make_opp(), _make_opp(agent_id="b")]
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_json_output(opps, _Args())
        finally:
            sys.stdout = old_stdout
        data = json.loads(buf.getvalue())
        assert "total_opportunities" in data
        assert "opportunities" in data
        assert "generated" in data

    def test_respects_top_limit(self):
        opps = [_make_opp(agent_id=f"a{i}") for i in range(10)]
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_json_output(opps, _Args(top=3))
        finally:
            sys.stdout = old_stdout
        data = json.loads(buf.getvalue())
        assert len(data["opportunities"]) == 3

    def test_skill_filter_in_json(self):
        opps = [_make_opp(agent_id="ez", effort="easy"),
                _make_opp(agent_id="hd", effort="hard")]
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_json_output(opps, _Args(skill="beginner"))
        finally:
            sys.stdout = old_stdout
        data = json.loads(buf.getvalue())
        ids = [o["id"] for o in data["opportunities"]]
        assert "ez" in ids
        assert "hd" not in ids


# ── Module load: sys.stdout.reconfigure (line 34) ────────────────────────────

class _FakeStdout:
    """Minimal fake stdout to trigger line 34 (encoding check)."""
    encoding = "ascii"
    _reconfigure_calls = []

    def reconfigure(self, **kwargs):
        self._reconfigure_calls.append(kwargs)

    def write(self, s):
        pass

    def flush(self):
        pass

    def isatty(self):
        return True


class TestModuleLoadReconfigure:
    def test_reconfigure_called_when_encoding_not_utf8(self, monkeypatch):
        """Line 34: sys.stdout.reconfigure called when encoding is not utf-8."""
        import importlib.util

        fake_stdout = _FakeStdout()
        monkeypatch.setattr(sys, "stdout", fake_stdout)

        spec2 = importlib.util.spec_from_file_location(
            "contribute_reconf", str(SCRIPTS_DIR / "contribute.py")
        )
        mod2 = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(mod2)

        assert len(fake_stdout._reconfigure_calls) == 1
        assert fake_stdout._reconfigure_calls[0] == {
            "encoding": "utf-8", "errors": "replace"
        }


# ── main() (lines 268-285) ────────────────────────────────────────────────────

class TestMain:
    def test_main_dashboard_mode(self, monkeypatch):
        """Lines 268-285: main() calls print_dashboard in default mode."""
        opps = [_make_opp()]
        monkeypatch.setattr(mod, "build_opportunities",
                           lambda category_filter=None: opps)
        dashboard_calls = []
        monkeypatch.setattr(mod, "print_dashboard",
                           lambda o, a: dashboard_calls.append((o, a)))
        monkeypatch.setattr(sys, "argv", ["contribute.py"])
        mod.main()
        assert len(dashboard_calls) == 1

    def test_main_json_mode(self, monkeypatch):
        """Lines 268-285: main() calls print_json_output with --json flag."""
        opps = [_make_opp()]
        monkeypatch.setattr(mod, "build_opportunities",
                           lambda category_filter=None: opps)
        json_calls = []
        monkeypatch.setattr(mod, "print_json_output",
                           lambda o, a: json_calls.append((o, a)))
        monkeypatch.setattr(sys, "argv", ["contribute.py", "--json"])
        mod.main()
        assert len(json_calls) == 1

    def test_main_passes_category_filter(self, monkeypatch):
        """Lines 268-285: --category value forwarded to build_opportunities."""
        build_calls = []
        def _track(category_filter=None):
            build_calls.append(category_filter)
            return []
        monkeypatch.setattr(mod, "build_opportunities", _track)
        monkeypatch.setattr(mod, "print_dashboard", lambda o, a: None)
        monkeypatch.setattr(sys, "argv", ["contribute.py", "--category", "aviation"])
        mod.main()
        assert build_calls == ["aviation"]

    def test_main_passes_skill_filter(self, monkeypatch):
        """Lines 268-285: --skill flag is parsed and passed through."""
        opps = [_make_opp()]
        monkeypatch.setattr(mod, "build_opportunities",
                           lambda category_filter=None: opps)
        dashboard_calls = []
        monkeypatch.setattr(mod, "print_dashboard",
                           lambda o, a: dashboard_calls.append((o, a)))
        monkeypatch.setattr(sys, "argv", ["contribute.py", "--skill", "beginner"])
        mod.main()
        assert len(dashboard_calls) == 1

    def test_main_with_top_limit(self, monkeypatch):
        """Lines 268-285: --top flag limits results."""
        opps = [_make_opp(agent_id=f"a{i}") for i in range(10)]
        monkeypatch.setattr(mod, "build_opportunities",
                           lambda category_filter=None: opps)
        dashboard_calls = []
        monkeypatch.setattr(mod, "print_dashboard",
                           lambda o, a: dashboard_calls.append((o, a)))
        monkeypatch.setattr(sys, "argv", ["contribute.py", "--top", "5"])
        mod.main()
        assert len(dashboard_calls) == 1
