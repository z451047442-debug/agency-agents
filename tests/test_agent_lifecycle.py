"""Tests for scripts/agent-lifecycle.py — lifecycle state machine."""

import argparse
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "agent_lifecycle", str(SCRIPTS_DIR / "agent-lifecycle.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

get_current_lifecycle = mod.get_current_lifecycle
set_lifecycle = mod.set_lifecycle
VALID_TRANSITIONS = mod.VALID_TRANSITIONS


def make_agent(path, lifecycle=None):
    """Create a temporary agent .md file with optional lifecycle field."""
    lc_line = f"lifecycle: {lifecycle}\n" if lifecycle else ""
    content = f"""---
name: "Test Agent"
description: "Test agent for lifecycle tests"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
{lc_line}---
## Identity
You are a test agent.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class TestGetCurrentLifecycle:
    def test_reads_published(self, tmp_path):
        f = make_agent(tmp_path / "test" / "test-agent.md", "published")
        assert get_current_lifecycle(f) == "published"

    def test_reads_draft(self, tmp_path):
        f = make_agent(tmp_path / "test" / "test-agent.md", "draft")
        assert get_current_lifecycle(f) == "draft"

    def test_reads_review(self, tmp_path):
        f = make_agent(tmp_path / "test" / "test-agent.md", "review")
        assert get_current_lifecycle(f) == "review"

    def test_reads_deprecated(self, tmp_path):
        f = make_agent(tmp_path / "test" / "test-agent.md", "deprecated")
        assert get_current_lifecycle(f) == "deprecated"

    def test_defaults_to_published(self, tmp_path):
        f = make_agent(tmp_path / "test" / "test-agent.md")
        assert get_current_lifecycle(f) == "published"

    def test_nonexistent_file_returns_unknown(self, tmp_path):
        f = tmp_path / "test" / "nonexistent.md"
        assert get_current_lifecycle(f) == "unknown"

    def test_invalid_value_defaults_to_published(self, tmp_path):
        path = tmp_path / "test" / "test-agent.md"
        path.parent.mkdir(parents=True)
        path.write_text("""---
name: "Test"
description: "Test"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
lifecycle: invalid_state
---
## Identity
Test.
""", encoding="utf-8")
        assert get_current_lifecycle(path) == "published"


class TestSetLifecycle:
    def test_draft_to_review(self, tmp_path):
        f = make_agent(tmp_path / "test" / "test-agent.md", "draft")
        ok, msg = set_lifecycle(f, "review")
        assert ok
        assert get_current_lifecycle(f) == "review"

    def test_review_to_published(self, tmp_path):
        f = make_agent(tmp_path / "test" / "test-agent.md", "review")
        ok, msg = set_lifecycle(f, "published")
        assert ok
        assert get_current_lifecycle(f) == "published"

    def test_published_to_deprecated(self, tmp_path):
        f = make_agent(tmp_path / "test" / "test-agent.md", "published")
        ok, msg = set_lifecycle(f, "deprecated")
        assert ok
        assert get_current_lifecycle(f) == "deprecated"

    def test_review_back_to_draft(self, tmp_path):
        f = make_agent(tmp_path / "test" / "test-agent.md", "review")
        ok, msg = set_lifecycle(f, "draft")
        assert ok
        assert get_current_lifecycle(f) == "draft"

    def test_deprecated_can_revive_to_published(self, tmp_path):
        f = make_agent(tmp_path / "test" / "test-agent.md", "deprecated")
        ok, msg = set_lifecycle(f, "published")
        assert ok
        assert get_current_lifecycle(f) == "published"

    def test_reject_draft_to_published(self, tmp_path):
        f = make_agent(tmp_path / "test" / "test-agent.md", "draft")
        ok, msg = set_lifecycle(f, "published")
        assert not ok
        assert "invalid transition" in msg.lower()

    def test_reject_review_to_deprecated(self, tmp_path):
        f = make_agent(tmp_path / "test" / "test-agent.md", "review")
        ok, msg = set_lifecycle(f, "deprecated")
        assert not ok
        assert "invalid transition" in msg.lower()

    def test_noop_when_already_in_state(self, tmp_path):
        f = make_agent(tmp_path / "test" / "test-agent.md", "published")
        ok, msg = set_lifecycle(f, "published")
        assert ok
        assert "already" in msg.lower()

    def test_adds_lifecycle_when_missing(self, tmp_path):
        f = make_agent(tmp_path / "test" / "test-agent.md")
        ok, msg = set_lifecycle(f, "draft")
        assert ok
        assert get_current_lifecycle(f) == "draft"


class TestTransitionTable:
    def test_all_states_have_transitions(self):
        for state in ("draft", "review", "published", "deprecated"):
            assert state in VALID_TRANSITIONS

    def test_draft_cannot_go_to_published(self):
        assert "published" not in VALID_TRANSITIONS["draft"]

    def test_published_cannot_go_to_review(self):
        assert "review" not in VALID_TRANSITIONS["published"]

    def test_deprecated_can_revive(self):
        assert "published" in VALID_TRANSITIONS["deprecated"]


class TestBuildLifecycleReport:
    def test_returns_correct_structure(self, tmp_path, monkeypatch):
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)
        make_agent(tmp_path / "engineering" / "eng-agent.md", "published")
        report = mod.build_lifecycle_report(check_freshness=False)
        assert "agents" in report
        assert "by_state" in report
        assert "by_category_state" in report

    def test_counts_published_agents(self, tmp_path, monkeypatch):
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)
        make_agent(tmp_path / "eng" / "a1.md", "published")
        make_agent(tmp_path / "eng" / "a2.md", "draft")
        report = mod.build_lifecycle_report(check_freshness=False)
        assert report["by_state"].get("published", 0) == 1
        assert report["by_state"].get("draft", 0) == 1

    def test_agents_without_lifecycle_default_published(self, tmp_path, monkeypatch):
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)
        make_agent(tmp_path / "eng" / "a1.md", None)
        report = mod.build_lifecycle_report(check_freshness=False)
        assert report["by_state"].get("published", 0) == 1

    def test_category_filter(self, tmp_path, monkeypatch):
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)
        make_agent(tmp_path / "eng" / "a1.md", "published")
        make_agent(tmp_path / "design" / "a2.md", "draft")
        report = mod.build_lifecycle_report(category_filter="eng", check_freshness=False)
        assert report["by_state"].get("published", 0) == 1
        assert report["by_state"].get("draft", 0) == 0

    def test_grouped_by_category_state(self, tmp_path, monkeypatch):
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)
        make_agent(tmp_path / "eng" / "a1.md", "published")
        report = mod.build_lifecycle_report(check_freshness=False)
        assert "eng" in report["by_category_state"]
        assert report["by_category_state"]["eng"]["published"] == 1


# ── discover_all_agents ──────────────────────────────────────────────────────

class TestDiscoverAllAgents:
    def test_yields_triplets(self):
        gen = mod.discover_all_agents(category_filter="aviation")
        items = list(gen)
        for item in items:
            assert len(item) == 3
            assert isinstance(item[0], Path)
            assert isinstance(item[1], str)
            assert isinstance(item[2], str)

    def test_respects_category_filter(self):
        items = list(mod.discover_all_agents(category_filter="aviation"))
        for _fp, _aid, cat in items:
            assert cat == "aviation"

    def test_empty_for_nonexistent_category(self):
        items = list(mod.discover_all_agents(category_filter="zzz_no_such_cat_zzz"))
        assert items == []


# ── print_json_report ────────────────────────────────────────────────────────

class TestPrintJsonReport:
    def test_outputs_valid_json(self):
        report = {
            "agents": {"published": []},
            "by_state": {"published": 10, "draft": 2, "review": 1, "deprecated": 0},
            "by_category_state": {},
        }
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            mod.print_json_report(report)
        finally:
            sys.stdout = old_stdout
        data = json.loads(buf.getvalue())
        assert "generated" in data
        assert "total_agents" in data
        assert data["total_agents"] == 13
        assert data["by_state"]["published"] == 10

    def test_empty_report(self):
        report = {"agents": {}, "by_state": {}, "by_category_state": {}}
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            mod.print_json_report(report)
        finally:
            sys.stdout = old_stdout
        data = json.loads(buf.getvalue())
        assert data["total_agents"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Additional tests for uncovered lines
# ═══════════════════════════════════════════════════════════════════════════════


# ── sys.stdout.reconfigure (line 53) ───────────────────────────────────────────

class TestStdoutReconfigure:
    """Cover the ``sys.stdout.reconfigure`` guard when encoding is not utf-8."""

    def test_reconfigure_when_encoding_not_utf8(self, monkeypatch):
        import io as _io_mod

        class FakeStdout:
            encoding = 'cp1252'
            reconfigure_calls = []

            def reconfigure(self, **kw):
                self.reconfigure_calls.append(kw)

            def write(self, s):
                pass

            def flush(self):
                pass

        fake_stdout = FakeStdout()
        monkeypatch.setattr(sys, 'stdout', fake_stdout)

        fresh_spec = importlib.util.spec_from_file_location(
            "agent_lifecycle_fresh", str(SCRIPTS_DIR / "agent-lifecycle.py")
        )
        fresh_mod = importlib.util.module_from_spec(fresh_spec)
        fresh_spec.loader.exec_module(fresh_mod)
        assert fake_stdout.reconfigure_calls


# ── set_lifecycle edge cases ───────────────────────────────────────────────────

class TestSetLifecycleEdgeCases:
    """Cover read/write exception handlers and frontmatter variants."""

    def test_read_error_nonexistent_file(self, tmp_path):
        """Cover lines 88-89 — read_text raises FileNotFoundError."""
        f = tmp_path / "nonexistent" / "agent.md"
        ok, msg = set_lifecycle(f, "review")
        assert not ok
        assert "No such file" in msg or "Error" in msg or msg

    def test_write_error_on_directory(self, tmp_path):
        """Cover lines 134-135 — write_text fails because path is a directory."""
        f = make_agent(tmp_path / "d" / "agent.md", "draft")
        f.unlink()
        f.mkdir()
        ok, msg = set_lifecycle(f, "review")
        assert not ok
        # The error message should be from the exception
        assert msg

    def test_write_text_failure(self, tmp_path, monkeypatch):
        """Cover lines 134-135 — write_text raises an exception."""
        f = make_agent(tmp_path / "test" / "agent.md", "draft")
        # Patch write_text to raise an error, simulating a write failure
        original_write = Path.write_text

        def _failing_write(self_path, *args, **kwargs):
            if self_path == f:
                raise PermissionError("Permission denied")
            return original_write(self_path, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", _failing_write)
        ok, msg = set_lifecycle(f, "review")
        assert not ok
        assert "Permission denied" in msg

    def test_insert_after_version_no_date_added(self, tmp_path):
        """Cover lines 118-121 — frontmatter has version but no date_added."""
        path = tmp_path / "cat" / "agent.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        content = """---
name: "Test Agent"
description: "Test agent for lifecycle"
color: blue
emoji: "X"
version: "1.0.0"
---
## Identity
You are a test agent.
"""
        path.write_text(content, encoding="utf-8")
        ok, msg = set_lifecycle(path, "review")
        assert ok
        assert get_current_lifecycle(path) == "review"

    def test_append_at_end_no_date_added_no_version(self, tmp_path):
        """Cover line 126 — frontmatter has neither date_added nor version."""
        path = tmp_path / "cat" / "agent.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        content = """---
name: "Test Agent"
description: "Test agent for lifecycle"
color: blue
emoji: "X"
---
## Identity
You are a test agent.
"""
        path.write_text(content, encoding="utf-8")
        ok, msg = set_lifecycle(path, "draft")
        assert ok
        assert get_current_lifecycle(path) == "draft"

    def test_update_existing_lifecycle_field(self, tmp_path):
        """Cover line 101 — lifecycle: appears at start of frontmatter."""
        path = tmp_path / "cat" / "agent.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        content = """---
lifecycle: draft
name: "Test Agent"
description: "Test"
color: blue
emoji: "X"
---
## Identity
Test.
"""
        path.write_text(content, encoding="utf-8")
        ok, msg = set_lifecycle(path, "review")
        assert ok
        assert get_current_lifecycle(path) == "review"


# ── build_lifecycle_report with freshness ──────────────────────────────────────

class TestBuildLifecycleReportFreshness:
    """Cover lines 155-157 — freshness check via git_last_modified."""

    def test_includes_days_stale(self, tmp_path, monkeypatch):
        from datetime import date
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        make_agent(tmp_path / "eng" / "eng-agent.md", "published")

        fake_date = date(2025, 1, 15)
        monkeypatch.setattr(mod, "git_last_modified", lambda fp: fake_date)

        report = mod.build_lifecycle_report(check_freshness=True)
        published = report["agents"].get("published", [])
        assert len(published) == 1
        assert published[0]["days_stale"] is not None
        assert published[0]["days_stale"] > 365

    def test_freshness_none_when_check_disabled(self, tmp_path, monkeypatch):
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)
        make_agent(tmp_path / "eng" / "eng-agent.md", "published")
        report = mod.build_lifecycle_report(check_freshness=False)
        published = report["agents"].get("published", [])
        assert published[0]["days_stale"] is None

    def test_git_last_modified_returns_none(self, tmp_path, monkeypatch):
        """Cover path where git_last_modified returns None/False."""
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)
        make_agent(tmp_path / "eng" / "eng-agent.md", "published")
        monkeypatch.setattr(mod, "git_last_modified", lambda fp: None)
        report = mod.build_lifecycle_report(check_freshness=True)
        published = report["agents"].get("published", [])
        assert published[0]["days_stale"] is None


# ── print_report ───────────────────────────────────────────────────────────────

class TestPrintReport:
    """Cover lines 179-245 — the lifecycle dashboard output."""

    @staticmethod
    def _make_report(agents, by_state, by_category_state=None):
        return {
            "agents": agents,
            "by_state": by_state,
            "by_category_state": by_category_state or {},
        }

    def test_basic_output(self):
        report = self._make_report(
            agents={"published": [], "draft": [], "review": [], "deprecated": []},
            by_state={"published": 50, "draft": 5, "review": 3, "deprecated": 2},
        )
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_report(report, argparse.Namespace(category=None))
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "Agent Lifecycle Dashboard" in out
        assert "Total: 60 agents" in out
        assert "Portfolio by State" in out
        assert "Health Indicators" in out

    def test_review_backlog_high(self):
        """>20% review triggers red warning."""
        report = self._make_report(
            agents={"published": [], "draft": [], "review": [], "deprecated": []},
            by_state={"published": 10, "draft": 2, "review": 10, "deprecated": 0},
        )
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_report(report, argparse.Namespace(category=None))
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "Review backlog" in out

    def test_review_queue_moderate(self):
        """5-20% review triggers yellow warning."""
        report = self._make_report(
            agents={"published": [], "draft": [], "review": [], "deprecated": []},
            by_state={"published": 80, "draft": 5, "review": 10, "deprecated": 0},
        )
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_report(report, argparse.Namespace(category=None))
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "Review queue" in out

    def test_review_healthy(self):
        """<5% review shows healthy message."""
        report = self._make_report(
            agents={"published": [], "draft": [], "review": [], "deprecated": []},
            by_state={"published": 95, "draft": 2, "review": 2, "deprecated": 1},
        )
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_report(report, argparse.Namespace(category=None))
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "Review queue healthy" in out

    def test_high_draft_ratio_warning(self):
        """>30% draft triggers yellow warning."""
        report = self._make_report(
            agents={"published": [], "draft": [], "review": [], "deprecated": []},
            by_state={"published": 10, "draft": 40, "review": 2, "deprecated": 0},
        )
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_report(report, argparse.Namespace(category=None))
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "High draft ratio" in out

    def test_high_deprecated_ratio_warning(self):
        """>10% deprecated triggers yellow warning."""
        report = self._make_report(
            agents={"published": [], "draft": [], "review": [], "deprecated": []},
            by_state={"published": 50, "draft": 5, "review": 3, "deprecated": 20},
        )
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_report(report, argparse.Namespace(category=None))
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "consider cleanup" in out

    def test_stale_agents_section(self):
        """Cover lines 215-224 — stale agents listing."""
        stale_entry = {
            "id": "stale-agent", "category": "eng",
            "state": "published", "path": "eng/stale-agent.md",
            "days_stale": 400,
        }
        report = self._make_report(
            agents={"published": [stale_entry], "draft": [], "review": [],
                    "deprecated": [{
                        "id": "old-dep", "category": "eng",
                        "state": "deprecated", "path": "eng/old-dep.md",
                        "days_stale": 500,
                    }]},
            by_state={"published": 1, "draft": 0, "review": 0, "deprecated": 1},
        )
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_report(report, argparse.Namespace(category=None))
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "Stale Agents" in out
        assert "stale-agent" in out
        assert "old-dep" in out
        assert "candidate for removal" in out

    def test_category_filter_shown(self):
        """When args.category is set, it appears in output."""
        report = self._make_report(
            agents={"published": [], "draft": [], "review": [], "deprecated": []},
            by_state={"published": 5, "draft": 0, "review": 0, "deprecated": 0},
        )
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_report(report, argparse.Namespace(category="engineering"))
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "Category: engineering" in out

    def test_category_breakdown(self):
        """Cover lines 228-238 — categories with most drafts/reviews."""
        report = self._make_report(
            agents={"published": [], "draft": [], "review": [], "deprecated": []},
            by_state={"published": 10, "draft": 2, "review": 1, "deprecated": 0},
            by_category_state={
                "engineering": {"published": 5, "draft": 2, "review": 1, "deprecated": 0},
                "design": {"published": 5, "draft": 0, "review": 0, "deprecated": 0},
            },
        )
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_report(report, argparse.Namespace(category=None))
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "Categories with Most Drafts/Reviews" in out
        assert "engineering" in out
        # design should not appear since it has 0 drafts + 0 reviews
        assert "design" not in out

    def test_agents_in_review(self):
        """Cover lines 241-245 — actionable review list (<=20 agents)."""
        review_agents = [
            {"id": f"rev-agent-{i}", "category": "eng", "state": "review",
             "path": f"eng/rev-agent-{i}.md", "days_stale": 10}
            for i in range(3)
        ]
        report = self._make_report(
            agents={"published": [], "draft": [], "review": review_agents, "deprecated": []},
            by_state={"published": 5, "draft": 0, "review": 3, "deprecated": 0},
        )
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_report(report, argparse.Namespace(category=None))
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "Agents Awaiting Review" in out
        assert "rev-agent-0" in out

    def test_too_many_review_agents_skipped(self):
        """When >20 agents are in review, the list is skipped."""
        review_agents = [
            {"id": f"rev-agent-{i}", "category": "eng", "state": "review",
             "path": f"eng/rev-agent-{i}.md", "days_stale": 10}
            for i in range(25)
        ]
        report = self._make_report(
            agents={"published": [], "draft": [], "review": review_agents, "deprecated": []},
            by_state={"published": 5, "draft": 0, "review": 25, "deprecated": 0},
        )
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_report(report, argparse.Namespace(category=None))
        finally:
            sys.stdout = old
        out = buf.getvalue()
        # "Agents Awaiting Review" should NOT appear when > 20
        assert "Agents Awaiting Review" not in out

    def test_stale_deprecated_candidate_for_removal(self):
        """Cover the deprecated stale agent path with removal candidate text."""
        dep_entry = {
            "id": "old-deprecated", "category": "infra",
            "state": "deprecated", "path": "infra/old-deprecated.md",
            "days_stale": 500,
        }
        report = self._make_report(
            agents={"published": [], "draft": [], "review": [],
                    "deprecated": [dep_entry]},
            by_state={"published": 0, "draft": 0, "review": 0, "deprecated": 1},
        )
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_report(report, argparse.Namespace(category=None))
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "candidate for removal" in out


# ── sync_lifecycle_fields ──────────────────────────────────────────────────────

class TestSyncLifecycleFields:
    """Cover lines 261-280 — sync lifecycle: published to agents missing it."""

    def test_dry_run(self, tmp_path, monkeypatch, capsys):
        """Cover dry_run=True path (lines 268-269, 277-278)."""
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        # Agent without lifecycle field
        path = tmp_path / "eng" / "eng-agent.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("""---
name: "Test"
description: "Test"
color: blue
emoji: "X"
---
## Identity
Test.
""", encoding="utf-8")

        mod.sync_lifecycle_fields(category_filter="eng", dry_run=True)
        captured = capsys.readouterr()
        assert "would add" in captured.out
        assert "DRY RUN" in captured.out

    def test_actual_sync(self, tmp_path, monkeypatch, capsys):
        """Cover dry_run=False path (lines 270-275, 280)."""
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        path = tmp_path / "eng" / "eng-agent.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("""---
name: "Test"
description: "Test"
color: blue
emoji: "X"
---
## Identity
Test.
""", encoding="utf-8")

        mod.sync_lifecycle_fields(category_filter="eng", dry_run=False)
        captured = capsys.readouterr()
        assert "Synced" in captured.out
        # Verify lifecycle was actually added
        assert get_current_lifecycle(path) == "published"

    def test_sync_error_handling(self, tmp_path, monkeypatch, capsys):
        """Cover the error path in sync (line 275)."""
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        # Create a valid agent file that will be discovered
        path = tmp_path / "eng" / "ephemeral.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("""---
name: "Test"
description: "Test"
color: blue
emoji: "X"
version: "1.0.0"
date_added: "2026-07-03"
---
## Identity
Test.
""", encoding="utf-8")

        # Monkeypatch set_lifecycle to always fail for any path
        original = mod.set_lifecycle
        monkeypatch.setattr(mod, "set_lifecycle", lambda fp, state, note="": (False, "simulated error"))
        mod.sync_lifecycle_fields(category_filter="eng", dry_run=False)
        captured = capsys.readouterr()
        # The error symbol ✗ should appear for the failure
        assert "simulated error" in captured.out or "ephemeral" in captured.out


# ── find_stale_agents ──────────────────────────────────────────────────────────

class TestFindStaleAgents:
    """Cover lines 285-296 — find stale agents function."""

    def test_finds_stale_agents(self, tmp_path, monkeypatch):
        import _shared.discovery
        from datetime import date
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        make_agent(tmp_path / "eng" / "eng-agent.md", "published")
        old_date = date(2024, 1, 1)
        monkeypatch.setattr(mod, "git_last_modified", lambda fp: old_date)

        stale = mod.find_stale_agents(months=12)
        assert len(stale) == 1
        assert stale[0][0] == "eng-agent"
        assert stale[0][1] == "eng"
        assert stale[0][2] == "published"

    def test_excludes_recent_agents(self, tmp_path, monkeypatch):
        import _shared.discovery
        from datetime import date, timedelta
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        make_agent(tmp_path / "eng" / "eng-agent.md", "published")
        recent = date.today() - timedelta(days=5)
        monkeypatch.setattr(mod, "git_last_modified", lambda fp: recent)

        stale = mod.find_stale_agents(months=12)
        assert len(stale) == 0

    def test_sorted_by_days_descending(self, tmp_path, monkeypatch):
        import _shared.discovery
        from datetime import date
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        make_agent(tmp_path / "eng" / "eng-a.md", "published")
        make_agent(tmp_path / "eng" / "eng-b.md", "draft")

        dates = [date(2023, 1, 1), date(2024, 6, 1)]
        calls = []

        def fake_git_last_modified(fp):
            calls.append(fp)
            idx = 0 if "eng-a" in str(fp) else 1
            return dates[idx]

        monkeypatch.setattr(mod, "git_last_modified", fake_git_last_modified)
        stale = mod.find_stale_agents(months=6)
        assert len(stale) >= 1
        if len(stale) >= 2:
            # Most stale first
            assert stale[0][4] >= stale[1][4]

    def test_uses_custom_months(self, tmp_path, monkeypatch):
        import _shared.discovery
        from datetime import date, timedelta
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        make_agent(tmp_path / "eng" / "eng-agent.md", "published")
        # 2 months ago — should be stale with --months 1
        two_months_ago = date.today() - timedelta(days=65)
        monkeypatch.setattr(mod, "git_last_modified", lambda fp: two_months_ago)

        stale = mod.find_stale_agents(months=1)
        assert len(stale) == 1


# ── main() entry point ─────────────────────────────────────────────────────────

class TestMain:
    """Cover lines 300-404 — the CLI entry point for all modes."""

    def _set_repo(self, monkeypatch, tmp_path):
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)

    # ── --status ───────────────────────────────────────────────────────────

    def test_status_agent_found(self, tmp_path, monkeypatch, capsys):
        self._set_repo(monkeypatch, tmp_path)
        make_agent(tmp_path / "eng" / "eng-foo.md", "published")
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--status', '--agent', 'eng-foo'])
        mod.main()
        captured = capsys.readouterr()
        assert "eng-foo" in captured.out
        assert "published" in captured.out

    def test_status_agent_not_found(self, tmp_path, monkeypatch, capsys):
        self._set_repo(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--status', '--agent', 'no-such-agent'])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_status_requires_agent(self, tmp_path, monkeypatch, capsys):
        self._set_repo(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--status'])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "requires --agent" in captured.err

    # ── --transition ───────────────────────────────────────────────────────

    def test_transition_single_agent_success(self, tmp_path, monkeypatch, capsys):
        self._set_repo(monkeypatch, tmp_path)
        make_agent(tmp_path / "eng" / "eng-bar.md", "draft")
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--transition', 'review',
                            '--agent', 'eng-bar'])
        mod.main()
        captured = capsys.readouterr()
        assert "eng-bar" in captured.out

    def test_transition_invalid_state(self, tmp_path, monkeypatch, capsys):
        self._set_repo(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--transition', 'bogus',
                            '--agent', 'eng-bar'])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid state" in captured.err

    def test_transition_agent_not_found(self, tmp_path, monkeypatch, capsys):
        self._set_repo(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--transition', 'review',
                            '--agent', 'nonexistent'])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_transition_batch_category(self, tmp_path, monkeypatch, capsys):
        self._set_repo(monkeypatch, tmp_path)
        make_agent(tmp_path / "eng" / "eng-a1.md", "draft")
        make_agent(tmp_path / "eng" / "eng-a2.md", "draft")
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--transition', 'review',
                            '--category', 'eng'])
        mod.main()
        captured = capsys.readouterr()
        assert "Transitioned" in captured.out
        assert "eng" in captured.out

    def test_transition_requires_agent_or_category(self, tmp_path, monkeypatch, capsys):
        self._set_repo(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--transition', 'review'])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "requires --agent or --category" in captured.err

    def test_transition_already_in_state(self, tmp_path, monkeypatch, capsys):
        self._set_repo(monkeypatch, tmp_path)
        make_agent(tmp_path / "eng" / "eng-same.md", "review")
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--transition', 'review',
                            '--agent', 'eng-same'])
        mod.main()
        captured = capsys.readouterr()
        assert "already" in captured.out.lower()

    def test_transition_invalid_from_current(self, tmp_path, monkeypatch, capsys):
        """Transition blocked by state machine (e.g., published -> review)."""
        self._set_repo(monkeypatch, tmp_path)
        make_agent(tmp_path / "eng" / "eng-blocked.md", "published")
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--transition', 'review',
                            '--agent', 'eng-blocked'])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "invalid transition" in captured.out.lower()

    def test_transition_batch_skips_same_state(self, tmp_path, monkeypatch, capsys):
        """Batch transition skips agents already in target state."""
        self._set_repo(monkeypatch, tmp_path)
        make_agent(tmp_path / "eng" / "eng-already.md", "review")
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--transition', 'review',
                            '--category', 'eng'])
        mod.main()
        captured = capsys.readouterr()
        assert "Transitioned 0 agents" in captured.out

    # ── --sync ─────────────────────────────────────────────────────────────

    def test_sync_mode(self, tmp_path, monkeypatch, capsys):
        self._set_repo(monkeypatch, tmp_path)
        # Agent without lifecycle field
        path = tmp_path / "eng" / "eng-no-lifecycle.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("""---
name: "Test"
description: "Test"
color: blue
emoji: "X"
---
## Identity
Test.
""", encoding="utf-8")
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--sync'])
        mod.main()
        captured = capsys.readouterr()
        assert "Synced" in captured.out

    def test_sync_dry_run(self, tmp_path, monkeypatch, capsys):
        self._set_repo(monkeypatch, tmp_path)
        path = tmp_path / "eng" / "eng-nolc.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("""---
name: "Test"
description: "Test"
color: blue
emoji: "X"
---
## Identity
Test.
""", encoding="utf-8")
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--sync', '--dry-run'])
        mod.main()
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    # ── --find-stale ───────────────────────────────────────────────────────

    def test_find_stale_mode(self, tmp_path, monkeypatch, capsys):
        import _shared.discovery
        from datetime import date
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        make_agent(tmp_path / "eng" / "eng-old.md", "published")
        monkeypatch.setattr(mod, "git_last_modified",
                           lambda fp: date(2023, 1, 1))

        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--find-stale', '--months', '6'])
        mod.main()
        captured = capsys.readouterr()
        assert "not modified in 6+ months" in captured.out
        assert "eng-old" in captured.out

    def test_find_stale_with_many_results(self, tmp_path, monkeypatch, capsys):
        """Test the '... and N more' truncation path (line 396)."""
        import _shared.discovery
        from datetime import date
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        # Create 55 stale agents (triggers >50 truncation)
        for i in range(55):
            make_agent(tmp_path / "eng" / f"eng-stale-{i:03d}.md", "published")
        monkeypatch.setattr(mod, "git_last_modified",
                           lambda fp: date(2022, 1, 1))

        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--find-stale', '--months', '1'])
        mod.main()
        captured = capsys.readouterr()
        assert "and 5 more" in captured.out

    # ── --report (default) ─────────────────────────────────────────────────

    def test_report_mode(self, tmp_path, monkeypatch, capsys):
        self._set_repo(monkeypatch, tmp_path)
        make_agent(tmp_path / "eng" / "eng-rpt.md", "published")
        monkeypatch.setattr(mod, "git_last_modified", lambda fp: None)
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--report'])
        mod.main()
        captured = capsys.readouterr()
        assert "Agent Lifecycle Dashboard" in captured.out

    def test_report_json_mode(self, tmp_path, monkeypatch, capsys):
        self._set_repo(monkeypatch, tmp_path)
        make_agent(tmp_path / "eng" / "eng-json.md", "published")
        monkeypatch.setattr(mod, "git_last_modified", lambda fp: None)
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--report', '--json'])
        mod.main()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "by_state" in data
        assert data["total_agents"] == 1

    def test_report_with_category_filter(self, tmp_path, monkeypatch, capsys):
        self._set_repo(monkeypatch, tmp_path)
        make_agent(tmp_path / "eng" / "eng-cat.md", "published")
        monkeypatch.setattr(mod, "git_last_modified", lambda fp: None)
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--report', '--category', 'eng'])
        mod.main()
        captured = capsys.readouterr()
        assert "Category: eng" in captured.out

    def test_report_with_stale_published(self, tmp_path, monkeypatch, capsys):
        """Cover stale published agents path in report (lines 215-222)."""
        import _shared.discovery
        from datetime import date
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        monkeypatch.setattr(mod, "REPO", tmp_path)
        make_agent(tmp_path / "eng" / "eng-stale-pub.md", "published")
        monkeypatch.setattr(mod, "git_last_modified",
                           lambda fp: date(2024, 1, 1))

        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--report'])
        mod.main()
        captured = capsys.readouterr()
        assert "Stale Agents" in captured.out

    def test_deprecated_transition_batch(self, tmp_path, monkeypatch, capsys):
        """Cover deprecating a batch of agents by category."""
        self._set_repo(monkeypatch, tmp_path)
        make_agent(tmp_path / "eng" / "eng-dep1.md", "published")
        make_agent(tmp_path / "eng" / "eng-dep2.md", "published")
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--transition', 'deprecated',
                            '--category', 'eng'])
        mod.main()
        captured = capsys.readouterr()
        assert "Transitioned 2 agents" in captured.out

    def test_transition_with_note(self, tmp_path, monkeypatch, capsys):
        """Cover --transition with --note (line 355)."""
        self._set_repo(monkeypatch, tmp_path)
        make_agent(tmp_path / "eng" / "eng-note.md", "draft")
        monkeypatch.setattr(sys, 'argv',
                           ['agent-lifecycle.py', '--transition', 'review',
                            '--agent', 'eng-note', '--note', 'Reviewed by SME'])
        mod.main()
        captured = capsys.readouterr()
        assert "eng-note" in captured.out
