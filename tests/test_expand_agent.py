"""Tests for scripts/expand-agent.py — agent expansion planning."""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "expand_agent", str(SCRIPTS_DIR / "expand-agent.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

generate_expansion_plan = mod.generate_expansion_plan
EXPANSION_SECTIONS = mod.EXPANSION_SECTIONS


# ── EXPANSION_SECTIONS ───────────────────────────────────────────────────────

class TestExpansionSections:
    def test_all_sections_have_required_keys(self):
        for name, config in EXPANSION_SECTIONS.items():
            assert "priority" in config, f"Missing priority in {name}"
            assert "target_words" in config, f"Missing target_words in {name}"
            assert "description" in config, f"Missing description in {name}"
            assert "template" in config, f"Missing template in {name}"
            assert isinstance(config["priority"], int)
            assert isinstance(config["target_words"], int)
            assert config["target_words"] > 0

    def test_priorities_are_unique(self):
        priorities = [c["priority"] for c in EXPANSION_SECTIONS.values()]
        assert len(priorities) == len(set(priorities))

    def test_templates_are_non_empty(self):
        for name, config in EXPANSION_SECTIONS.items():
            assert len(config["template"]) > 20, \
                f"Template for {name} is too short"


# ── generate_expansion_plan ──────────────────────────────────────────────────

def _make_analysis(agent_id="test-agent", category="engineering",
                   grade="B", total=5, word_count=200, scores=None,
                   section_found=3, estimated_new_words=300):
    if scores is None:
        scores = {
            "content_depth": 2,
            "structure": 2,
            "frontmatter": 2,
            "file_health": 2,
        }
    return {
        "agent_id": agent_id,
        "category": category,
        "path": f"{category}/{agent_id}.md",
        "current_grade": grade,
        "current_total": total,
        "current_scores": scores,
        "word_count": word_count,
        "needs": [],
        "estimated_new_words": estimated_new_words,
        "projected_grade": "A" if total >= 8 else "B",
        "issues": [],
    }


def _make_ref_agent(ref_id, word_count=500, total=9):
    return (word_count, total, ref_id, Path(f"/fake/{ref_id}.md"))


class TestGenerateExpansionPlan:
    def test_returns_list(self):
        analysis = _make_analysis()
        plan = generate_expansion_plan(analysis, [])
        assert isinstance(plan, list)

    def test_each_plan_item_has_required_keys(self):
        plan = generate_expansion_plan(_make_analysis(), [])
        for item in plan:
            for key in ("section", "priority", "target_words", "description", "template"):
                assert key in item

    def test_sorted_by_priority(self):
        plan = generate_expansion_plan(_make_analysis(), [])
        priorities = [p["priority"] for p in plan]
        assert priorities == sorted(priorities)

    def test_a_grade_agents_skip_expansion(self):
        analysis = _make_analysis(grade="A", total=9, word_count=900)
        plan = generate_expansion_plan(analysis, [])
        assert plan == []

    def test_high_word_count_skips_identity(self):
        """Agents with >400 words skip Identity & Backstory enhancement."""
        analysis = _make_analysis(word_count=500)
        plan = generate_expansion_plan(analysis, [])
        sections = {p["section"] for p in plan}
        assert "Identity & Backstory" not in sections

    def test_good_structure_skips_critical_rules(self):
        """Agents with structure >= 3 skip Critical Rules Enhancement."""
        analysis = _make_analysis(
            scores={"content_depth": 2, "structure": 3, "frontmatter": 2, "file_health": 2}
        )
        plan = generate_expansion_plan(analysis, [])
        sections = {p["section"] for p in plan}
        assert "Critical Rules Enhancement" not in sections

    def test_templates_match_expansion_sections(self):
        plan = generate_expansion_plan(_make_analysis(), [])
        for item in plan:
            expected_template = EXPANSION_SECTIONS[item["section"]]["template"]
            assert item["template"] == expected_template

    def test_low_word_count_gets_identity(self):
        """Agents with low word count get Identity suggestion."""
        analysis = _make_analysis(word_count=100, grade="B", total=4)
        plan = generate_expansion_plan(analysis, [])
        sections = {p["section"] for p in plan}
        assert "Identity & Backstory" in sections

    def test_exemplars_empty_without_ref_agents(self):
        plan = generate_expansion_plan(_make_analysis(), [])
        for item in plan:
            assert item["exemplars"] == []

    def test_plan_includes_success_metrics(self):
        """B-grade agents with low word count get all 5 section types."""
        analysis = _make_analysis(word_count=150, grade="B", total=4,
                                  scores={"content_depth": 1, "structure": 1,
                                          "frontmatter": 1, "file_health": 1})
        plan = generate_expansion_plan(analysis, [])
        section_names = {p["section"] for p in plan}
        for name in EXPANSION_SECTIONS:
            assert name in section_names, f"Missing section: {name}"
