"""Tests for scripts/agent-lifecycle.py — lifecycle state machine."""

import importlib.util
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
