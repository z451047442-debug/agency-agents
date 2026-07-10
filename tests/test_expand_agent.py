"""Tests for scripts/expand-agent.py — agent expansion planning."""

import importlib.util
import io
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

find_reference_agents = mod.find_reference_agents
generate_expansion_plan = mod.generate_expansion_plan
print_expansion_plan = mod.print_expansion_plan
analyze_expansion_needs = mod.analyze_expansion_needs
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
                   section_found=3, estimated_new_words=300, issues=None):
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
        "issues": issues if issues is not None else [],
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


# ── find_reference_agents ────────────────────────────────────────────────────

class TestFindReferenceAgents:
    def test_returns_list_of_tuples(self):
        refs = find_reference_agents("engineering", "zzz_nonexistent_zzz")
        assert isinstance(refs, list)
        if refs:
            wc, total, ref_id, filepath = refs[0]
            assert isinstance(wc, int)
            assert isinstance(total, int)
            assert isinstance(ref_id, str)
            assert isinstance(filepath, Path)

    def test_excludes_self(self):
        refs = find_reference_agents("engineering", "engineering-frontend-developer")
        ids = [r[2] for r in refs]
        assert "engineering-frontend-developer" not in ids

    def test_returns_at_most_top_n(self):
        refs = find_reference_agents("engineering", "zzz_nonexistent_zzz", top_n=2)
        assert len(refs) <= 2

    def test_empty_for_small_category(self):
        """Very small categories may have no A-grade agents."""
        refs = find_reference_agents("aviation", "aviation_nonexistent")
        assert isinstance(refs, list)


# ── analyze_expansion_needs ──────────────────────────────────────────────────

class TestAnalyzeExpansionNeeds:
    def test_returns_expected_keys(self):
        """Test with a real agent file from a small category."""
        agent_file = SCRIPTS_DIR.parent / "aviation" / "aviation-flight-test-engineer.md"
        if not agent_file.exists():
            pytest.skip("aviation agent file not found")
        result = analyze_expansion_needs(
            "aviation-flight-test-engineer", "aviation", agent_file
        )
        for key in ("agent_id", "category", "current_grade", "current_total",
                     "word_count", "needs", "estimated_new_words", "projected_grade"):
            assert key in result, f"Missing key: {key}"

    def test_agent_id_matches_input(self):
        agent_file = SCRIPTS_DIR.parent / "aviation" / "aviation-flight-test-engineer.md"
        if not agent_file.exists():
            pytest.skip("aviation agent file not found")
        result = analyze_expansion_needs(
            "test-id-123", "aviation", agent_file
        )
        assert result["agent_id"] == "test-id-123"


# ── print_expansion_plan ─────────────────────────────────────────────────────

class TestPrintExpansionPlan:
    def test_prints_agent_info(self):
        analysis = _make_analysis(agent_id="test-expand-me", category="testing")
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_expansion_plan(analysis, [], [])
        finally:
            sys.stdout = old_stdout
        output = buf.getvalue()
        assert "test-expand-me" in output
        assert "testing" in output

    def test_shows_reference_agents(self):
        analysis = _make_analysis()
        refs = [_make_ref_agent("ref-expert", word_count=600, total=9)]
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_expansion_plan(analysis, refs, [])
        finally:
            sys.stdout = old_stdout
        assert "ref-expert" in buf.getvalue()

    def test_shows_expansion_steps(self):
        analysis = _make_analysis(word_count=100, grade="B", total=4)
        plan = generate_expansion_plan(analysis, [])
        if not plan:
            pytest.skip("no expansion plan generated")
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_expansion_plan(analysis, [], plan)
        finally:
            sys.stdout = old_stdout
        output = buf.getvalue()
        assert "Expansion Steps" in output
        assert "Estimated total" in output

    def test_shows_current_issues(self):
        analysis = _make_analysis(issues=["Missing sections", "Too short"])
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_expansion_plan(analysis, [], [])
        finally:
            sys.stdout = old_stdout
        output = buf.getvalue()
        assert "Missing sections" in output
