"""Tests for scripts/expand-thin-agents.py — batch content expansion for thin agents."""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Module import will fail until expand-thin-agents.py exists
spec = importlib.util.spec_from_file_location(
    "expand_thin_agents", str(SCRIPTS_DIR / "expand-thin-agents.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

from _shared.validators import CORE_SECTIONS, count_substantive_sections


# ── helpers ──────────────────────────────────────────────────────────────────

def _section_body(text: str, min_words: int = 30) -> str:
    """Repeat text until it has at least *min_words* words (for threshold tests)."""
    words = text.split()
    repeats = (min_words // len(words)) + 1
    return " ".join(words * repeats)


# ── count_substantive_sections ──────────────────────────────────────────────

class TestCountSubstantiveSections:
    """Direct tests of the existing count_substantive_sections utility."""

    def test_counts_correctly(self):
        text = _section_body("I am a tester with enough words to qualify.")
        body = (
            f"## Identity\n{text}\n\n"
            f"## Core Mission\n{_section_body('I test things thoroughly every single time.')}\n\n"
            f"## Critical Rules\n{_section_body('Be thorough and complete in all tasks.')}"
        )
        assert count_substantive_sections(body) == 3

    def test_zero_for_empty(self):
        assert count_substantive_sections("") == 0

    def test_ignores_short_sections(self):
        body = "## Identity\nHi.\n## Core Mission\nOK."
        assert count_substantive_sections(body) == 0


# ── identify_missing_sections ──────────────────────────────────────────────

class TestIdentifyMissingSections:
    def test_identifies_missing(self, tmp_path):
        """Missing sections like Deliverables, Workflow are detected."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text(
            "---\nname: Test\n---\n"
            f"## Identity\n{_section_body('I am a tester with enough words to qualify.')}\n\n"
            f"## Critical Rules\n{_section_body('Be thorough and complete in all tasks.')}",
            encoding="utf-8",
        )
        missing = mod.identify_missing_sections(agent_file)
        assert "Core Mission" in missing
        assert "Deliverables" in missing
        assert "Workflow" in missing

    def test_no_missing_for_complete(self, tmp_path):
        """Agent with all 7 substantive sections returns empty list."""
        agent_file = tmp_path / "full-agent.md"
        agent_file.write_text(
            "---\nname: Complete\n---\n"
            f"## Identity\n{_section_body('I am a complete agent with enough content here.')}\n\n"
            f"## Core Mission\n{_section_body('My mission is to be a complete test agent.')}\n\n"
            f"## Critical Rules\n{_section_body('I must have enough content in each section.')}\n\n"
            f"## Deliverables\n{_section_body('I produce test cases with thorough detail.')}\n\n"
            f"## Workflow\n{_section_body('I follow a structured process for all tasks.')}\n\n"
            f"## Success Metrics\n{_section_body('Quality and accuracy are my primary measures.')}\n\n"
            f"## Communication Style\n{_section_body('I communicate clearly and effectively.')}",
            encoding="utf-8",
        )
        missing = mod.identify_missing_sections(agent_file)
        assert len(missing) == 0


# ── generate_section_template ──────────────────────────────────────────────

class TestGenerateSectionTemplate:
    def test_produces_content_for_existing_section(self):
        agent = {"name": "Test Agent", "category": "testing", "body": "Content."}
        template = mod.generate_section_template(agent, "Core Mission")
        assert "Mission" in template
        assert len(template) > 50

    def test_all_core_sections_produce_templates(self):
        agent = {"name": "Full Agent", "category": "general", "body": "Content."}
        for section_name in CORE_SECTIONS:
            template = mod.generate_section_template(agent, section_name)
            assert template, f"Empty template for {section_name}"
            assert len(template) > 50, f"Template too short for {section_name}"


# ── dry-run mode ────────────────────────────────────────────────────────────

class TestDryRunNoWrite:
    def test_dry_run_does_not_modify_file(self, tmp_path):
        """Dry-run mode expands in memory only — file content is unchanged."""
        d = tmp_path / "testing"
        d.mkdir()
        f = d / "testing-example.md"
        original = (
            "---\nname: Example\ndate_added: '2026-07-01'\n---\n"
            f"## Identity\n{_section_body('I am an example agent with enough words.')}\n\n"
            f"## Core Mission\n{_section_body('I help test things thoroughly.')}\n\n"
            f"## Communication Style\n{_section_body('I am clear and direct at all times.')}"
        )
        f.write_text(original, encoding="utf-8")

        mod.expand_agent(f, dry_run=True)
        assert f.read_text(encoding="utf-8") == original


# ── expansion (non-dry-run) ─────────────────────────────────────────────────

class TestExpandAgent:
    def test_expands_thin_agent(self, tmp_path):
        """A thin agent (3 sections) gets new sections added."""
        d = tmp_path / "testing"
        d.mkdir()
        f = d / "testing-thin.md"
        f.write_text(
            "---\nname: Thin Agent\ndescription: Testing expansion\nemoji: X\ncolor: red\n---\n"
            f"## Identity\n{_section_body('I am a thin agent with enough content to qualify.')}\n\n"
            f"## Core Mission\n{_section_body('My mission is to be expanded with new sections.')}\n\n"
            f"## Critical Rules\n{_section_body('I must grow and become more complete over time.')}",
            encoding="utf-8",
        )

        added = mod.expand_agent(f, dry_run=False)
        assert len(added) >= 1, "At least one section should be added"

        content = f.read_text(encoding="utf-8")
        found_new = any(s in content for s in ["Success Metrics", "Deliverables", "Workflow"])
        assert found_new, f"No new sections found. Added: {added}"

    def test_skips_full_agent(self, tmp_path):
        """An agent with all 7 sections (each with >=30 words) gets nothing added."""
        d = tmp_path / "testing"
        d.mkdir()
        f = d / "testing-full.md"
        f.write_text(
            "---\nname: Full Agent\n---\n"
            f"## Identity\n{_section_body('I am a full agent with enough content here.')}\n\n"
            f"## Core Mission\n{_section_body('My mission is comprehensive and complete.')}\n\n"
            f"## Critical Rules\n{_section_body('I have enough rules to guide my behavior.')}\n\n"
            f"## Deliverables\n{_section_body('I produce deliverables of the highest quality.')}\n\n"
            f"## Workflow\n{_section_body('My workflow is systematic and thorough.')}\n\n"
            f"## Success Metrics\n{_section_body('I measure success by quality and completeness.')}\n\n"
            f"## Communication Style\n{_section_body('I communicate clearly and effectively.')}",
            encoding="utf-8",
        )

        added = mod.expand_agent(f, dry_run=False)
        assert added == [], f"Expected no additions but got: {added}"

    def test_adds_sections_before_last_heading(self, tmp_path):
        """New sections should be inserted before the last existing heading."""
        d = tmp_path / "testing"
        d.mkdir()
        f = d / "testing-order.md"
        original = (
            "---\nname: Order Test\n---\n"
            f"## Identity\n{_section_body('I am the first section with enough words to count.')}\n\n"
            f"## Core Mission\n{_section_body('I am the second section with enough words to count.')}\n\n"
            "## Professional Scope\nI should remain at the end of the file.\n"
        )
        f.write_text(original, encoding="utf-8")

        added = mod.expand_agent(f, dry_run=False)
        content = f.read_text(encoding="utf-8")

        # "Professional Scope" should still be at the end (new sections inserted before it)
        scope_pos = content.index("Professional Scope")
        # All new section content should appear before "Professional Scope"
        new_sections_found = [s for s in added if s in content]
        for section in new_sections_found:
            assert content.index(section) < scope_pos, (
                f"{section} appears after Professional Scope"
            )
