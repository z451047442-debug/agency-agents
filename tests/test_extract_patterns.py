"""Tests for scripts/extract-patterns.py — feedback pattern analysis."""

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
    "extract_patterns", str(SCRIPTS_DIR / "extract-patterns.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

load_feedback = mod.load_feedback
analyze = mod.analyze
print_report = mod.print_report


class TestLoadFeedback:
    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "FEEDBACK_FILE", tmp_path / "nonexistent.jsonl")
        assert load_feedback() == []

    def test_parses_valid_lines(self, tmp_path, monkeypatch):
        fb = tmp_path / "fb.jsonl"
        fb.write_text(
            '{"agent": "a1", "rating": 5}\n'
            '{"agent": "a2", "rating": 3, "issue": "thin"}\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "FEEDBACK_FILE", fb)
        result = load_feedback()
        assert len(result) == 2

    def test_skips_corrupt_lines(self, tmp_path, monkeypatch):
        fb = tmp_path / "fb.jsonl"
        fb.write_text('NOT JSON\n{"agent": "ok", "rating": 4}\n', encoding="utf-8")
        monkeypatch.setattr(mod, "FEEDBACK_FILE", fb)
        result = load_feedback()
        assert len(result) == 1

    def test_skips_blank_lines(self, tmp_path, monkeypatch):
        fb = tmp_path / "fb.jsonl"
        fb.write_text('\n\n{"agent": "a", "rating": 2}\n\n', encoding="utf-8")
        monkeypatch.setattr(mod, "FEEDBACK_FILE", fb)
        assert len(load_feedback()) == 1


class TestAnalyze:
    def test_empty_feedback(self):
        result = analyze([])
        assert result["total"] == 0
        assert result["issues"] == []

    def test_low_rated_avg_below_3(self):
        fb = [{"agent": "bad", "rating": 1}, {"agent": "bad", "rating": 2}]
        result = analyze(fb)
        assert len(result["low_rated"]) == 1
        assert result["low_rated"][0][1]["avg"] == 1.5

    def test_top_rated_requires_min_2_ratings(self):
        fb = [
            {"agent": "good", "rating": 5}, {"agent": "good", "rating": 5},
            {"agent": "alone", "rating": 5},
        ]
        result = analyze(fb)
        top_ids = [a[0] for a in result["top_rated"]]
        assert "good" in top_ids
        assert "alone" not in top_ids

    def test_top_rated_requires_avg_ge_45(self):
        fb = [{"agent": "ok", "rating": 4}, {"agent": "ok", "rating": 4}]
        assert len(analyze(fb)["top_rated"]) == 0

    def test_issues_counted(self):
        fb = [
            {"agent": "a", "rating": 3, "issue": "outdated reference"},
            {"agent": "b", "rating": 3, "issue": "outdated reference"},
        ]
        assert ("outdated reference", 2) in analyze(fb)["issues"]

    def test_unknown_agent_id(self):
        fb = [{"rating": 3}]
        assert "unknown" in analyze(fb)["by_agent"]

    def test_missing_rating_still_counts_issue(self):
        fb = [{"agent": "x", "issue": "broken link"}]
        assert ("broken link", 1) in analyze(fb)["issues"]


class TestPrintReport:
    def test_empty_feedback_message(self):
        out = io.StringIO()
        with patch.object(sys, "stdout", out):
            print_report(analyze([]))
        assert "No feedback data yet" in out.getvalue()

    def test_all_positive_message(self):
        fb = [{"agent": "a", "rating": 5}, {"agent": "a", "rating": 5}]
        out = io.StringIO()
        with patch.object(sys, "stdout", out):
            print_report(analyze(fb))
        assert "All feedback is positive" in out.getvalue()

    def test_suggestions_for_outdated(self):
        fb = [{"agent": "x", "rating": 4, "issue": "outdated data"}]
        out = io.StringIO()
        with patch.object(sys, "stdout", out):
            print_report(analyze(fb))
        assert "Suggested actions" in out.getvalue()

    def test_suggestions_for_wrong(self):
        fb = [{"agent": "x", "rating": 2, "issue": "wrong methodology"}]
        out = io.StringIO()
        with patch.object(sys, "stdout", out):
            print_report(analyze(fb))
        assert "Verify agent accuracy" in out.getvalue()

    def test_suggestions_for_thin(self):
        fb = [{"agent": "x", "rating": 2, "issue": "thin content"}]
        out = io.StringIO()
        with patch.object(sys, "stdout", out):
            print_report(analyze(fb))
        assert "Expand agent content" in out.getvalue()


class TestMain:
    def test_json_output(self, monkeypatch, tmp_path):
        fb = tmp_path / "fb.jsonl"
        fb.write_text("", encoding="utf-8")
        monkeypatch.setattr(mod, "FEEDBACK_FILE", fb)
        out = io.StringIO()
        with patch.object(sys, "argv", ["extract-patterns.py", "--json"]), \
             patch.object(sys, "stdout", out):
            mod.main()
        data = json.loads(out.getvalue())
        assert data["total"] == 0

    def test_agent_not_found(self, monkeypatch, tmp_path):
        fb = tmp_path / "fb.jsonl"
        fb.write_text("", encoding="utf-8")
        monkeypatch.setattr(mod, "FEEDBACK_FILE", fb)
        out = io.StringIO()
        with patch.object(sys, "argv", ["extract-patterns.py", "--agent", "no-one"]), \
             patch.object(sys, "stdout", out):
            mod.main()
        assert "No feedback for no-one" in out.getvalue()

    def test_agent_found(self, monkeypatch, tmp_path):
        fb = tmp_path / "fb.jsonl"
        fb.write_text(
            '{"agent": "found_agent", "rating": 4}\n'
            '{"agent": "found_agent", "rating": 5}\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "FEEDBACK_FILE", fb)
        out = io.StringIO()
        with patch.object(sys, "argv", ["extract-patterns.py", "--agent", "found_agent"]), \
             patch.object(sys, "stdout", out):
            mod.main()
        assert "found_agent" in out.getvalue()
        assert "4.5/5" in out.getvalue()

    def test_default_no_flags(self, monkeypatch, tmp_path):
        fb = tmp_path / "fb.jsonl"
        fb.write_text(
            '{"agent": "x", "rating": 1, "issue": "thin content"}\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "FEEDBACK_FILE", fb)
        out = io.StringIO()
        with patch.object(sys, "argv", ["extract-patterns.py"]), \
             patch.object(sys, "stdout", out):
            mod.main()
        assert "Suggested actions" in out.getvalue()
