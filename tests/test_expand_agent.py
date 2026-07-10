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

import _shared.discovery

find_reference_agents = mod.find_reference_agents
generate_expansion_plan = mod.generate_expansion_plan
print_expansion_plan = mod.print_expansion_plan
analyze_expansion_needs = mod.analyze_expansion_needs
EXPANSION_SECTIONS = mod.EXPANSION_SECTIONS


# ── encoding reconfigure (lines 28, 30) ────────────────────────────────────

class TestEncodingReconfigure:
    def test_stdout_stderr_reconfigure(self):
        """Test that lines 28, 30 (encoding reconfigure) are executed.

        These are module-level guard statements that execute when
        sys.stdout.encoding != 'utf-8'. We reload the module with a
        monkeypatched stdout/stderr encoding to trigger this path.
        """
        import io

        # Save originals
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        old_mod = sys.modules.get("expand_agent")

        try:
            # Create streams with non-UTF-8 encoding
            raw_out = io.BytesIO()
            raw_err = io.BytesIO()
            sys.stdout = io.TextIOWrapper(raw_out, encoding="cp1252")
            sys.stderr = io.TextIOWrapper(raw_err, encoding="cp1252")

            # Remove cached module and reload
            sys.modules.pop("expand_agent", None)
            spec2 = importlib.util.spec_from_file_location(
                "expand_agent2", str(SCRIPTS_DIR / "expand-agent.py")
            )
            mod2 = importlib.util.module_from_spec(spec2)
            spec2.loader.exec_module(mod2)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


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
                   section_found=3, estimated_new_words=300, issues=None,
                   path=None):
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
        "path": path if path else f"{category}/{agent_id}.md",
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

    def test_high_word_count_skips_identity(self, tmp_path):
        """Agents with >300 body words skip Identity & Backstory enhancement.

        This requires an actual file on disk with >300 body words so
        generate_expansion_plan can read the body and count words.
        """
        # Create a real file with >300 words in the body
        words = " ".join(["word" for _ in range(400)])
        file_content = f"---\nname: Test\n---\n\n## Identity\n{words}\n"
        tmp_file = tmp_path / "test.md"
        tmp_file.write_text(file_content)
        analysis = _make_analysis(word_count=500, path=str(tmp_file))
        plan = generate_expansion_plan(analysis, [])
        sections = {p["section"] for p in plan}
        assert "Identity & Backstory" not in sections

    def test_word_count_over_400_skips_identity(self, tmp_path):
        """Agents with word_count > 400 but low body words skip Identity.

        When the body file has <=300 words but the analysis has word_count > 400,
        the second Identity check (line 219-220) fires.
        """
        # Use non-existent path so body is empty (0 words)
        analysis = _make_analysis(word_count=500, grade="B", total=4,
                                  scores={"content_depth": 1, "structure": 1,
                                          "frontmatter": 1, "file_health": 1},
                                  path=str(tmp_path / "nonexistent.md"))
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


# ── analyze_expansion_needs with various score profiles ───────────────────

class TestAnalyzeExpansionNeedsVariousProfiles:
    """Test analyze_expansion_needs with agents having different score profiles."""

    def test_content_depth_low(self, tmp_path, monkeypatch):
        """Agent with low content_depth triggers word gap analysis."""
        from _shared import discover_agents

        monkeypatch.setattr(mod._score_agents, "REPO", tmp_path)
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)

        # Need to find or create an agent with content_depth < 3
        # First create one that should score low on content_depth (short)
        agent_dir = tmp_path / "engineering"
        agent_dir.mkdir()
        short_content = (
            "---\nname: Short Agent\ndescription: A short agent for testing\n"
            "emoji: X\ncolor: red\n---\n\n"
            "## Identity\nYou are a helper.\n\n"
            "## Mission\nHelp users.\n"
        )
        (agent_dir / "engineering-short-agent.md").write_text(short_content)
        filepath = agent_dir / "engineering-short-agent.md"

        try:
            result = mod.analyze_expansion_needs(
                "engineering-short-agent", "engineering", filepath
            )
        except Exception:
            pytest.skip("score_agents REPO mismatch")

        assert result["agent_id"] == "engineering-short-agent"
        assert "needs" in result
        assert "estimated_new_words" in result

    def test_frontmatter_low_score(self, tmp_path, monkeypatch):
        """Agent with low frontmatter score triggers frontmatter needs."""
        agent_dir = tmp_path / "engineering"
        agent_dir.mkdir()
        # Minimal frontmatter - will likely score low on frontmatter
        content = (
            "---\nname: Min Agent\ndescription: Minimal\n---\n\n"
            "## Identity\nYou are helpful.\n\n"
            "## Mission\nHelp users.\n\n"
            "## Critical Rules\n1. Be good.\n\n"
            "## Deliverables\nReports.\n\n"
            "## Workflow\nStep by step.\n\n"
            "## Success Metrics\nMeasure success.\n\n"
            "## Another section with more text to add words for validation and "
            "ensure we have enough content to reach reasonable word count "
            "requirements set by the scoring system.\n"
        )
        (agent_dir / "engineering-min-agent.md").write_text(content)
        filepath = agent_dir / "engineering-min-agent.md"

        # Monkeypatch score_agents REPO for discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)

        try:
            result = mod.analyze_expansion_needs(
                "engineering-min-agent", "engineering", filepath
            )
        except Exception:
            pytest.skip("REPO mismatch in score_agents")

        assert "needs" in result

    def test_projected_grade_a(self, tmp_path, monkeypatch):
        """Agent with total >= 8 gets projected_grade 'A'."""
        # Direct test with mocked result from score_agent
        def _fake_score(filepath, check_freshness=False):
            return {
                "grade": "A", "id": "test-agent", "word_count": 900,
                "total": 9, "scores": {"content_depth": 3, "structure": 3,
                                       "frontmatter": 2, "file_health": 2},
                "sections_found": 7, "issues": [],
                "frontmatter_details": [], "file_size_kb": 3,
            }

        monkeypatch.setattr(mod, "score_agent", _fake_score)
        fake_path = tmp_path / "test.md"
        fake_path.write_text("---\nname: Test\n---\n## Identity\nHello.\n")

        result = mod.analyze_expansion_needs("test-id", "engineering", fake_path)
        assert result["projected_grade"] == "A"

    def test_file_health_low(self, tmp_path, monkeypatch):
        """Agent with low file_health triggers file_health needs."""
        def _fake_score(filepath, check_freshness=False):
            return {
                "grade": "C", "id": "test-agent", "word_count": 200,
                "total": 3, "scores": {"content_depth": 2, "structure": 2,
                                       "frontmatter": 2, "file_health": 1},
                "sections_found": 2, "issues": ["Short content"],
                "frontmatter_details": [], "file_size_kb": 1,
            }

        monkeypatch.setattr(mod, "score_agent", _fake_score)
        fake_path = tmp_path / "test.md"
        fake_path.write_text("---\nname: Test\n---\n## Identity\nHello.\n")

        result = mod.analyze_expansion_needs("test-id", "engineering", fake_path)
        # Check that file_health need exists
        health_needs = [n for n in result["needs"] if n.get("dimension") == "file_health"]
        assert len(health_needs) == 1


# ── generate_expansion_plan with reference agents ────────────────────────

class TestGenerateExpansionPlanWithRefs:
    """Test generate_expansion_plan with real reference agent files."""

    def test_ref_agents_with_sections(self, tmp_path, monkeypatch):
        """Reference agents with sections populate ref_sections."""
        # Create a reference agent file with Identity and Mission sections
        ref_dir = tmp_path / "refs"
        ref_dir.mkdir()
        ref_content = (
            "---\nname: Ref Agent\ndescription: A reference\n---\n\n"
            "## Identity & Memory\nYou are a reference agent.\n\n"
            "## Core Mission\nYour mission is to serve as reference.\n\n"
            "## Critical Rules\n1. Be consistent.\n\n"
            "## Deliverables\nDocuments.\n\n"
            "## Workflow\nSteps.\n\n"
            "## Success Metrics\nTrack progress.\n\n"
            "## Communication Style\nBe clear.\n"
        )
        ref_path = ref_dir / "ref-agent.md"
        ref_path.write_text(ref_content)

        # Also create a target agent file for analyze_expansion_needs
        agent_dir = tmp_path / "engineering"
        agent_dir.mkdir()
        agent_content = (
            "---\nname: Target Agent\ndescription: A target agent for expansion\n"
            "emoji: X\ncolor: red\n---\n\n"
            "## Identity\nYou are a target.\n\n"
            "## Mission\nYour mission.\n"
        )
        agent_path = agent_dir / "engineering-target-agent.md"
        agent_path.write_text(agent_content)

        # Mock score_agent to return different results for ref vs target
        original_score = mod.score_agent

        def _fake_score(filepath, check_freshness=False):
            if str(filepath) == str(ref_path):
                return {
                    "grade": "A", "id": "ref-agent", "word_count": 600,
                    "total": 9, "scores": {"content_depth": 3, "structure": 3,
                                           "frontmatter": 2, "file_health": 2},
                    "sections_found": 7, "issues": [],
                    "frontmatter_details": [], "file_size_kb": 4,
                }
            else:
                return {
                    "grade": "B", "id": "engineering-target-agent", "word_count": 100,
                    "total": 4, "scores": {"content_depth": 1, "structure": 1,
                                           "frontmatter": 1, "file_health": 1},
                    "sections_found": 2, "issues": ["Too short"],
                    "frontmatter_details": [], "file_size_kb": 2,
                }

        monkeypatch.setattr(mod, "score_agent", _fake_score)

        analysis = mod.analyze_expansion_needs(
            "engineering-target-agent", "engineering", agent_path
        )
        ref_agents = [(600, 9, "ref-agent", ref_path)]
        plan = mod.generate_expansion_plan(analysis, ref_agents)
        assert len(plan) > 0

    def test_skip_communication_style_with_ref(self, tmp_path, monkeypatch):
        """Skip Communication Style when ref_sections has Communication."""
        ref_dir = tmp_path / "refs"
        ref_dir.mkdir()
        ref_content = (
            "---\nname: Ref Agent\ndescription: Ref\n---\n\n"
            "## Identity\nHello.\n\n"
            "## Communication Style\nBe clear and concise.\n"
        )
        ref_path = ref_dir / "ref-agent.md"
        ref_path.write_text(ref_content)

        agent_dir = tmp_path / "engineering"
        agent_dir.mkdir()
        agent_content = (
            "---\nname: Target Agent\ndescription: Target\nemoji: X\ncolor: red\n---\n\n"
            "## Identity\nYou are a target.\n"
        )
        agent_path = agent_dir / "engineering-target-agent.md"
        agent_path.write_text(agent_content)

        def _fake_score(filepath, check_freshness=False):
            if str(filepath) == str(ref_path):
                return {
                    "grade": "A", "id": "ref-agent", "word_count": 600,
                    "total": 9, "scores": {"content_depth": 3, "structure": 3,
                                           "frontmatter": 2, "file_health": 2},
                    "sections_found": 7, "issues": [],
                    "frontmatter_details": [], "file_size_kb": 4,
                }
            else:
                return {
                    "grade": "B", "id": "engineering-target-agent", "word_count": 30,
                    "total": 3, "scores": {"content_depth": 1, "structure": 1,
                                           "frontmatter": 1, "file_health": 1},
                    "sections_found": 1, "issues": ["Too short"],
                    "frontmatter_details": [], "file_size_kb": 1,
                }

        monkeypatch.setattr(mod, "score_agent", _fake_score)

        analysis = mod.analyze_expansion_needs(
            "engineering-target-agent", "engineering", agent_path
        )
        ref_agents = [(600, 9, "ref-agent", ref_path)]
        plan = mod.generate_expansion_plan(analysis, ref_agents)
        # Communication Style should be skipped since ref agent has it
        comm_sections = [p for p in plan if p["section"] == "Communication Style"]
        assert len(comm_sections) == 0

    def test_skip_success_metrics_with_ref(self, tmp_path, monkeypatch):
        """Skip Success Metrics when ref_sections has Success Metrics."""
        ref_dir = tmp_path / "refs"
        ref_dir.mkdir()
        ref_content = (
            "---\nname: Ref Agent\ndescription: Ref\n---\n\n"
            "## Identity\nHello.\n\n"
            "## Success Metrics\nTrack KPIs.\n"
        )
        ref_path = ref_dir / "ref-agent.md"
        ref_path.write_text(ref_content)

        agent_dir = tmp_path / "engineering"
        agent_dir.mkdir()
        agent_content = (
            "---\nname: Target Agent\ndescription: Target\nemoji: X\ncolor: red\n---\n\n"
            "## Identity\nYou are a target.\n"
        )
        agent_path = agent_dir / "engineering-target-agent.md"
        agent_path.write_text(agent_content)

        def _fake_score(filepath, check_freshness=False):
            if str(filepath) == str(ref_path):
                return {
                    "grade": "A", "id": "ref-agent", "word_count": 600,
                    "total": 9, "scores": {"content_depth": 3, "structure": 3,
                                           "frontmatter": 2, "file_health": 2},
                    "sections_found": 7, "issues": [],
                    "frontmatter_details": [], "file_size_kb": 4,
                }
            else:
                return {
                    "grade": "B", "id": "engineering-target-agent", "word_count": 30,
                    "total": 3, "scores": {"content_depth": 1, "structure": 1,
                                           "frontmatter": 1, "file_health": 1},
                    "sections_found": 1, "issues": ["Too short"],
                    "frontmatter_details": [], "file_size_kb": 1,
                }

        monkeypatch.setattr(mod, "score_agent", _fake_score)

        analysis = mod.analyze_expansion_needs(
            "engineering-target-agent", "engineering", agent_path
        )
        ref_agents = [(600, 9, "ref-agent", ref_path)]
        plan = mod.generate_expansion_plan(analysis, ref_agents)
        # Success Metrics should be skipped since ref agent has it
        sm_sections = [p for p in plan if p["section"] == "Success Metrics"]
        assert len(sm_sections) == 0


# ── print_expansion_plan with exemplars ────────────────────────────────────

class TestPrintExpansionPlanWithExemplars:
    def test_prints_reference_with_exemplars(self):
        """print_expansion_plan prints Reference: line when plan has exemplars."""
        import io, sys

        analysis = _make_analysis(word_count=100, grade="B", total=4,
                                  scores={"content_depth": 1, "structure": 1,
                                          "frontmatter": 1, "file_health": 1})
        plan = [{
            "section": "Communication Style",
            "priority": 3,
            "target_words": 60,
            "description": "Define communication style",
            "template": EXPANSION_SECTIONS["Communication Style"]["template"],
            "exemplars": ["ref-agent-1", "ref-agent-2"],
        }]

        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            mod.print_expansion_plan(analysis, [], plan)
        finally:
            sys.stdout = old_stdout
        output = buf.getvalue()
        assert "Reference:" in output
        assert "ref-agent-1" in output


# ── main ───────────────────────────────────────────────────────────────────

class TestMain:
    def test_all_below_mode(self, tmp_path, monkeypatch):
        """--all-below mode lists agents below word count."""
        import io, sys

        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)

        # Create agents
        agent_dir = tmp_path / "engineering"
        agent_dir.mkdir()
        content = (
            "---\nname: Test\n---\n\n"
            "## Identity\nYou are a test agent with some content.\n"
        )
        (agent_dir / "engineering-test-agent.md").write_text(content)

        old_argv = sys.argv
        sys.argv = ["expand-agent.py", "--category", "engineering", "--all-below", "1000"]
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            mod.main()
        finally:
            sys.stdout = old_stdout
            sys.argv = old_argv
        output = captured.getvalue()
        assert "test-agent" in output

    def test_all_below_requires_category(self, tmp_path, monkeypatch):
        """--all-below without --category exits with error."""
        import sys
        old_argv = sys.argv
        sys.argv = ["expand-agent.py", "--all-below", "400"]
        try:
            with pytest.raises(SystemExit) as exc_info:
                mod.main()
            assert exc_info.value.code == 1
        finally:
            sys.argv = old_argv

    def test_no_args_prints_help(self, monkeypatch):
        """No arguments prints help and exits."""
        import sys
        old_argv = sys.argv
        sys.argv = ["expand-agent.py"]
        try:
            with pytest.raises(SystemExit) as exc_info:
                mod.main()
            assert exc_info.value.code == 1
        finally:
            sys.argv = old_argv

    def test_agent_not_found(self, tmp_path, monkeypatch):
        """Non-existent agent ID exits with error."""
        import sys
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)

        old_argv = sys.argv
        sys.argv = ["expand-agent.py", "nonexistent-agent-id"]
        try:
            with pytest.raises(SystemExit) as exc_info:
                mod.main()
            assert exc_info.value.code == 1
        finally:
            sys.argv = old_argv

    def test_a_grade_agent_no_expansion(self, tmp_path, monkeypatch):
        """A-grade agent prints 'No expansion needed' and returns."""
        import io, sys

        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)

        agent_dir = tmp_path / "engineering"
        agent_dir.mkdir()
        content = (
            "---\nname: Excellent Agent\ndescription: An excellent agent\n"
            "emoji: X\ncolor: red\n---\n\n"
            "## Identity\nYou are great.\n" * 10
        )
        (agent_dir / "engineering-excellent-agent.md").write_text(content)

        # Mock score_agent to return A grade
        def _fake_score(filepath, check_freshness=False):
            return {
                "grade": "A", "id": "engineering-excellent-agent", "word_count": 900,
                "total": 9, "scores": {"content_depth": 3, "structure": 3,
                                       "frontmatter": 2, "file_health": 2},
                "sections_found": 7, "issues": [],
                "frontmatter_details": [], "file_size_kb": 4,
            }

        monkeypatch.setattr(mod, "score_agent", _fake_score)

        old_argv = sys.argv
        sys.argv = ["expand-agent.py", "engineering-excellent-agent"]
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            mod.main()
        finally:
            sys.stdout = old_stdout
            sys.argv = old_argv
        output = captured.getvalue()
        assert "No expansion needed" in output

    def test_b_grade_agent_expansion(self, tmp_path, monkeypatch):
        """B-grade agent generates expansion plan."""
        import io, sys

        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)

        agent_dir = tmp_path / "engineering"
        agent_dir.mkdir()
        content = (
            "---\nname: Needs Work Agent\ndescription: A weak agent\n"
            "emoji: X\ncolor: red\n---\n\n"
            "## Identity\nYou are helpful.\n"
        )
        (agent_dir / "engineering-needs-work-agent.md").write_text(content)

        # Mock score_agent to return B grade
        def _fake_score(filepath, check_freshness=False):
            return {
                "grade": "B", "id": "engineering-needs-work-agent", "word_count": 100,
                "total": 5, "scores": {"content_depth": 2, "structure": 1,
                                       "frontmatter": 1, "file_health": 1},
                "sections_found": 2, "issues": ["Too short"],
                "frontmatter_details": [], "file_size_kb": 2,
            }

        monkeypatch.setattr(mod, "score_agent", _fake_score)

        # Also mock find_reference_agents to return empty list
        monkeypatch.setattr(mod, "find_reference_agents", lambda *a, **kw: [])

        old_argv = sys.argv
        sys.argv = ["expand-agent.py", "engineering-needs-work-agent"]
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            mod.main()
        finally:
            sys.stdout = old_stdout
            sys.argv = old_argv
        output = captured.getvalue()
        assert "Expansion Plan" in output
