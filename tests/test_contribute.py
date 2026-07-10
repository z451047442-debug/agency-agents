"""Tests for scripts/contribute.py — contribution dashboard."""

import importlib.util
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


# ── estimate_effort ──────────────────────────────────────────────────────────

class TestEstimateEffort:
    def test_no_issues_all_good_scores_returns_done(self):
        scores = {"content_depth": 3, "structure": 3, "frontmatter": 2, "file_health": 2}
        assert estimate_effort([], scores, 800) == "done"

    def test_done_when_enough_scores(self):
        # The function checks: content_depth >= 2, structure >= 3, frontmatter >= 2, file_health >= 2
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
        """word_count is accepted but doesn't affect the current logic."""
        scores = {"content_depth": 3, "structure": 3, "frontmatter": 2, "file_health": 2}
        # Same result regardless of word_count
        assert estimate_effort([], scores, 100) == "done"
        assert estimate_effort([], scores, 10000) == "done"
