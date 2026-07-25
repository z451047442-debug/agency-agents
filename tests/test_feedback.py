"""Tests for scripts/feedback.py — the missing test coverage."""

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def clean_feedback_env(monkeypatch, tmp_path):
    """Redirect feedback storage to a temp file, then import a fresh module."""
    fb_file = tmp_path / ".feedback.jsonl"
    # Force a fresh import by using a unique module name each time
    import uuid
    mod_name = f"feedback_{uuid.uuid4().hex[:8]}"
    spec = importlib.util.spec_from_file_location(
        mod_name, str(SCRIPTS_DIR / "feedback.py")
    )
    feedback_mod = importlib.util.module_from_spec(spec)
    # Override FEEDBACK_FILE before executing the module code
    feedback_mod.FEEDBACK_FILE = fb_file
    # Monkeypatch the file exists check so the module's _ensure_file works
    monkeypatch.setattr(feedback_mod, "FEEDBACK_FILE", fb_file)
    spec.loader.exec_module(feedback_mod)
    # Ensure FEEDBACK_FILE is set after module init
    feedback_mod.FEEDBACK_FILE = fb_file
    return feedback_mod, fb_file


class TestAddFeedback:
    def test_add_with_rating(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        entry = fb.add_feedback("test-agent", rating=4)
        assert entry["rating"] == 4
        assert entry["agent"] == "test-agent"
        assert "timestamp" in entry
        entries = fb._read_all()
        assert len(entries) == 1

    def test_add_with_comment(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        entry = fb.add_feedback("test-agent", comment="Great agent")
        assert entry["comment"] == "Great agent"
        assert "rating" not in entry

    def test_add_with_issue(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        entry = fb.add_feedback("test-agent", issue="Outdated docs")
        assert entry["issue"] == "Outdated docs"

    def test_rating_clamped(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        assert fb.add_feedback("a", rating=0)["rating"] == 1
        assert fb.add_feedback("a", rating=6)["rating"] == 5

    def test_comment_truncated(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        long_comment = "x" * 600
        entry = fb.add_feedback("a", comment=long_comment)
        assert len(entry["comment"]) == 500


class TestReadAll:
    def test_empty_file(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        assert fb._read_all() == []

    def test_non_empty(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        fb.add_feedback("a", rating=5)
        fb.add_feedback("b", rating=3)
        assert len(fb._read_all()) == 2

    def test_skips_corrupted_lines(self, clean_feedback_env):
        fb, fb_file = clean_feedback_env
        fb.add_feedback("a", rating=5)
        with open(fb_file, "a", encoding="utf-8") as f:
            f.write("{invalid json}\n")
        fb.add_feedback("b", rating=3)
        assert len(fb._read_all()) == 2


class TestExportFeedback:
    def test_export_json(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        fb.add_feedback("a", rating=4, comment="good")
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            fb.export_feedback()
        output = json.loads(buf.getvalue())
        assert output["count"] == 1
        assert output["feedback"][0]["rating"] == 4


class TestPurgeFeedback:
    def test_purge_removes_file(self, clean_feedback_env):
        fb, fb_file = clean_feedback_env
        fb.add_feedback("a", rating=3)
        assert fb_file.exists()
        fb.purge_feedback()
        assert not fb_file.exists()

    def test_purge_no_file(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        fb.purge_feedback()  # should not raise


class TestShowReport:
    def test_empty_report(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            fb.show_report()
        assert "No feedback recorded yet" in buf.getvalue()

    def test_report_with_entries(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        fb.add_feedback("agent-x", rating=5, comment="Excellent")
        fb.add_feedback("agent-x", rating=3)
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            fb.show_report()
        output = buf.getvalue()
        assert "agent-x" in output
        assert "Excellent" in output


class TestShowStats:
    def test_empty_stats(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            fb.show_stats()
        assert "No local feedback data" in buf.getvalue()

    def test_stats_with_ratings(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        fb.add_feedback("top-agent", rating=5)
        fb.add_feedback("top-agent", rating=4)
        fb.add_feedback("low-agent", rating=1)
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            fb.show_stats()
        output = buf.getvalue()
        assert "Feedback entries: 3" in output
        assert "Unique agents: 2" in output


class TestSubmitFeedback:
    def test_submit_empty(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            fb.submit_feedback()
        assert "No feedback to submit" in buf.getvalue()

    def test_submit_markdown_format(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        fb.add_feedback("agent-z", rating=2, issue="broken link on line 5")
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            fb.submit_feedback()
        output = buf.getvalue()
        assert "## User Feedback Report" in output
        assert "agent-z" in output
        assert "broken link on line 5" in output


class TestMainCLI:
    def test_no_args_shows_help(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf), \
             mock.patch.object(sys, "argv", ["feedback.py"]):
            try:
                fb.main()
            except SystemExit:
                pass
        output = buf.getvalue()
        assert "Agent feedback collection" in output

    def test_rate_missing_agent(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        buf = io.StringIO()
        with mock.patch.object(sys, "stderr", buf):
            try:
                # Simulate --rate 5 without --agent
                fb.main._parse_args_test = True
            except SystemExit:
                pass
        # Verify the module's main() guards against missing agent
        with mock.patch.object(sys, "argv", ["feedback.py", "--rate", "5"]):
            with pytest.raises(SystemExit) as exc:
                fb.main()
            assert exc.value.code == 1

    def test_rate_with_agent(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        with mock.patch.object(sys, "argv", ["feedback.py", "--agent", "test-x", "--rate", "4"]):
            try:
                fb.main()
            except SystemExit:
                pass
        entries = fb._read_all()
        assert len(entries) == 1
        assert entries[0]["rating"] == 4
        assert entries[0]["agent"] == "test-x"

    def test_used_mode(self, clean_feedback_env, tmp_path):
        fb, _ = clean_feedback_env
        usage_file = tmp_path / ".usage.jsonl"
        fb.USAGE_FILE = usage_file
        with mock.patch.object(sys, "argv", ["feedback.py", "--used", "agent-used"]):
            try:
                fb.main()
            except SystemExit:
                pass
        assert usage_file.exists()
        entries = fb._read_usage()
        assert "agent-used" in entries

    def test_used_multiple_times(self, clean_feedback_env, tmp_path):
        fb, _ = clean_feedback_env
        usage_file = tmp_path / ".usage.jsonl"
        fb.USAGE_FILE = usage_file
        fb.record_usage("agent-repeat")
        fb.record_usage("agent-repeat")
        fb.record_usage("agent-repeat")
        entries = fb._read_usage()
        assert entries["agent-repeat"] == 3

    def test_prompt_mode(self, clean_feedback_env, tmp_path):
        fb, _ = clean_feedback_env
        usage_file = tmp_path / ".usage.jsonl"
        fb.USAGE_FILE = usage_file
        fb.record_usage("unrated-agent")
        fb.record_usage("unrated-agent")
        fb.record_usage("unrated-agent")
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf), \
             mock.patch.object(sys, "argv", ["feedback.py", "--prompt"]):
            try:
                fb.main()
            except SystemExit:
                pass
        output = buf.getvalue()
        assert "unrated-agent" in output

    def test_prompt_all_rated(self, clean_feedback_env, tmp_path):
        fb, _ = clean_feedback_env
        usage_file = tmp_path / ".usage.jsonl"
        fb.USAGE_FILE = usage_file
        fb.record_usage("rated-agent")
        fb.record_usage("rated-agent")
        fb.record_usage("rated-agent")
        fb.add_feedback("rated-agent", rating=4)
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf), \
             mock.patch.object(sys, "argv", ["feedback.py", "--prompt"]):
            try:
                fb.main()
            except SystemExit:
                pass
        output = buf.getvalue()
        assert "All frequently used agents have been rated" in output

    def test_read_usage_empty(self, clean_feedback_env, tmp_path):
        fb, _ = clean_feedback_env
        usage_file = tmp_path / ".nonexistent.jsonl"
        fb.USAGE_FILE = usage_file
        result = fb._read_usage()
        assert result == {}

    def test_purge_mode(self, clean_feedback_env):
        fb, _ = clean_feedback_env
        fb.add_feedback("test-purge", rating=3)
        assert len(fb._read_all()) == 1
        with mock.patch.object(sys, "argv", ["feedback.py", "--purge"]):
            try:
                fb.main()
            except SystemExit:
                pass
        assert len(fb._read_all()) == 0

import pytest
import io
import json
import sys
from unittest import mock


@pytest.fixture
def feedback_env_with_usage(clean_feedback_env):
    fb, fb_file = clean_feedback_env
    usage_file = fb_file.parent / ".usage.jsonl"
    fb.USAGE_FILE = usage_file
    return fb, fb_file, usage_file


class TestRecordUsage:
    def test_creates_file(self, feedback_env_with_usage):
        fb, _, usage_file = feedback_env_with_usage
        entry = fb.record_usage("agent-x")
        assert usage_file.exists()
        assert entry["agent"] == "agent-x"
        assert "timestamp" in entry

    def test_appends_multiple_entries(self, feedback_env_with_usage):
        fb, _, _ = feedback_env_with_usage
        fb.record_usage("agent-x")
        fb.record_usage("agent-x")
        fb.record_usage("agent-y")
        usage = fb._read_usage()
        assert usage == {"agent-x": 2, "agent-y": 1}


class TestReadUsage:
    def test_empty_when_no_file(self, feedback_env_with_usage):
        fb, _, _ = feedback_env_with_usage
        assert fb._read_usage() == {}

    def test_reads_usage_counts(self, feedback_env_with_usage):
        fb, _, _ = feedback_env_with_usage
        fb.record_usage("agent-x")
        fb.record_usage("agent-x")
        fb.record_usage("agent-y")
        result = fb._read_usage()
        assert result["agent-x"] == 2
        assert result["agent-y"] == 1

    def test_skips_corrupted_lines(self, feedback_env_with_usage):
        fb, _, usage_file = feedback_env_with_usage
        fb.record_usage("agent-x")
        with open(usage_file, "a", encoding="utf-8") as f:
            f.write("{invalid}\n")
        result = fb._read_usage()
        assert result["agent-x"] == 1


class TestPromptForFeedback:
    def test_all_rated_when_used_3plus(self, feedback_env_with_usage):
        fb, _, _ = feedback_env_with_usage
        for _ in range(3):
            fb.record_usage("agent-x")
        fb.add_feedback("agent-x", rating=4)
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            fb.prompt_for_feedback()
        output = buf.getvalue()
        assert "All frequently used agents" in output

    def test_lists_unrated_agents_used_3plus(self, feedback_env_with_usage):
        fb, _, _ = feedback_env_with_usage
        for _ in range(5):
            fb.record_usage("needs-rating")
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            fb.prompt_for_feedback()
        output = buf.getvalue()
        assert "needs-rating" in output
        assert "used 5 times" in output

    def test_skips_low_usage_unrated(self, feedback_env_with_usage):
        fb, _, _ = feedback_env_with_usage
        fb.record_usage("low-agent")
        fb.record_usage("low-agent")
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            fb.prompt_for_feedback()
        assert "All frequently used agents" in buf.getvalue()

    def test_shows_rated_vs_unrated_summary(self, feedback_env_with_usage):
        fb, _, _ = feedback_env_with_usage
        for _ in range(3):
            fb.record_usage("rated-agent")
        fb.add_feedback("rated-agent", rating=5)
        for _ in range(4):
            fb.record_usage("unrated-agent")
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            fb.prompt_for_feedback()
        output = buf.getvalue()
        assert "Rated: 1/2" in output


class TestMainCLIUsedPrompt:
    def test_used_flag(self, feedback_env_with_usage):
        fb, _, _ = feedback_env_with_usage
        with mock.patch.object(sys, "argv", ["feedback.py", "--used", "agent-x"]):
            fb.main()
        usage = fb._read_usage()
        assert usage.get("agent-x") == 1

    def test_prompt_flag_empty(self, feedback_env_with_usage):
        fb, _, _ = feedback_env_with_usage
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf),              mock.patch.object(sys, "argv", ["feedback.py", "--prompt"]):
            fb.main()
        assert "All frequently used agents" in buf.getvalue()
