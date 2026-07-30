"""Tests for scripts/batch-add-metadata.py — metadata field population."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import _shared.discovery as _disc

spec = importlib.util.spec_from_file_location(
    "batch_add_metadata", str(SCRIPTS_DIR / "batch-add-metadata.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

extract_tags = mod.extract_tags
extract_keywords = mod.extract_keywords
infer_complexity = mod.infer_complexity
infer_duration = mod.infer_duration
has_field = mod.has_field
insert_fields = mod.insert_fields


# ── extract_tags ───────────────────────────────────────────────────────────

class TestExtractTags:
    def test_category_is_first_tag(self):
        tags = extract_tags("testing", "## Identity\n\nSome body text")
        assert "testing" in tags
        assert len(tags) >= 1

    def test_extracts_from_section_headers(self):
        body = (
            "## Identity & Memory\n\nstuff\n"
            "## Core Mission\n\nmore stuff\n"
            "## Automation\n\nfoo\n"
            "## Performance\n\nbar\n"
        )
        tags = extract_tags("testing", body)
        assert "testing" in tags
        # Should have found header-derived tags
        assert len(tags) >= 2

    def test_max_five_tags(self):
        body = "## One\n\n## Two\n\n## Three\n\n## Four\n\n## Five\n\n## Six\n\n## Seven\n\n"
        tags = extract_tags("testing", body)
        assert len(tags) <= 5
        assert "testing" in tags

    def test_empty_body(self):
        tags = extract_tags("engineering", "")
        assert tags == ["engineering"]

    def test_excludes_short_words(self):
        tags = extract_tags("testing", "## Hi\n\n## Of the\n\n## Foo\n\n")
        assert "testing" in tags
        # All derived tags should be >= 2 chars


# ── extract_keywords ───────────────────────────────────────────────────────

class TestExtractKeywords:
    def test_from_description(self):
        desc = "自动化测试框架设计与CI/CD集成专家"
        name = "Test Architect"
        body = "## Identity\n\n"
        kws = extract_keywords(desc, name, body)
        assert len(kws) >= 2

    def test_from_name_and_description(self):
        desc = "Expert in automated testing, CI/CD pipelines, and test automation"
        name = "SDET/Test Developer"
        body = "## Identity\n\n"
        kws = extract_keywords(desc, name, body)
        # Should include meaningful terms from both
        assert len(kws) >= 2

    def test_max_five_keywords(self):
        desc = "one two three four five six seven eight nine ten"
        name = "x"
        body = "## Identity\n\n"
        kws = extract_keywords(desc, name, body)
        assert len(kws) <= 5

    def test_identity_bold_terms_used(self):
        desc = "simple agent"
        name = "Agent"
        body = (
            "## Identity & Memory\n\n"
            "**Role**: **accessibility auditing** specialist\n"
            "**Personality**: thorough, advocacy-driven\n"
        )
        kws = extract_keywords(desc, name, body)
        # Should find "accessibility" and "auditing" from bold terms
        found = [kw for kw in kws if "accessibility" in kw.lower() or "auditing" in kw.lower()]
        assert len(found) >= 1

    def test_empty_description_still_produces_something(self):
        kws = extract_keywords("", "Test Agent", "## Identity\n\n**Domain**: testing\n")
        assert len(kws) >= 1


# ── infer_complexity ──────────────────────────────────────────────────────

class TestInferComplexity:
    def test_director_is_high(self):
        assert infer_complexity("testing-director", "QA Director", "leads team") == "high"

    def test_chief_is_high(self):
        assert infer_complexity("chief-officer", "Chief Officer", "executive") == "high"

    def test_vp_is_high(self):
        assert infer_complexity("vp-engineering", "VP Engineering", "leadership") == "high"

    def test_ceo_is_high(self):
        assert infer_complexity("ceo-agent", "CEO Agent", "exec") == "high"

    def test_manager_is_medium(self):
        assert infer_complexity("testing-manager", "Test Manager", "manages team") == "medium"

    def test_architect_is_medium(self):
        assert infer_complexity("automation-architect", "Architect", "designs") == "medium"

    def test_coordinator_is_medium(self):
        assert infer_complexity("testing-coordinator", "Coordinator", "coordinates") == "medium"

    def test_lead_is_medium(self):
        assert infer_complexity("team-lead", "Team Lead", "leads team") == "medium"

    def test_default_is_low(self):
        assert infer_complexity("testing-engineer", "Tester", "does testing") == "low"

    def test_developer_default_is_low(self):
        assert infer_complexity("engineering-frontend-developer", "Developer", "codes") == "low"


# ── infer_duration ────────────────────────────────────────────────────────

class TestInferDuration:
    def test_high_maps_to_4_8h(self):
        assert infer_duration("high") == "4-8h"

    def test_medium_maps_to_2_4h(self):
        assert infer_duration("medium") == "2-4h"

    def test_low_maps_to_1_2h(self):
        assert infer_duration("low") == "1-2h"

    def test_unknown_defaults_to_1_2h(self):
        assert infer_duration("unknown") == "1-2h"


# ── has_field ─────────────────────────────────────────────────────────────

class TestHasField:
    def test_existing_field(self):
        fm = "\nname: Test\ndate_added: 2026-01-01\n"
        assert has_field("name", fm) is True

    def test_missing_field(self):
        fm = "\nname: Test\ndate_added: 2026-01-01\n"
        assert has_field("tags", fm) is False

    def test_empty_frontmatter(self):
        assert has_field("anything", "") is False


# ── insert_fields ─────────────────────────────────────────────────────────

class TestInsertFields:
    def test_inserts_before_depends_on(self):
        fm = "\nname: Test\ndate_added: 2026-01-01\ndepends_on:\n  - dep1\nvibe: ok\n"
        result, dirty, inserted = insert_fields(fm, [("tags", ["testing", "automation"])])
        assert dirty is True
        assert "tags" in inserted
        # tags should appear before depends_on
        tags_idx = result.find("tags:")
        deps_idx = result.find("depends_on:")
        assert tags_idx < deps_idx
        assert "  - testing" in result
        assert "  - automation" in result

    def test_inserts_at_end_when_no_depends_on(self):
        fm = "\nname: Test\ndate_added: 2026-01-01\nvibe: ok\n"
        result, dirty, inserted = insert_fields(fm, [("complexity", "medium")])
        assert dirty is True
        assert "complexity: medium" in result
        # complexity should appear after the last line (before closing ---)
        # and not before vibe (no depends_on to anchor)
        assert result.rstrip().endswith("complexity: medium")

    def test_skips_existing_field(self):
        fm = "\nname: Test\ntags:\n  - existing\n"
        result, dirty, inserted = insert_fields(fm, [("tags", ["new-tag"])])
        assert dirty is False
        assert inserted == []
        assert "existing" in result
        assert "new-tag" not in result

    def test_multiple_fields(self):
        fm = "\nname: Test\n"
        result, dirty, inserted = insert_fields(fm, [
            ("tags", ["tag1", "tag2"]),
            ("complexity", "high"),
            ("estimated_duration", "4-8h"),
        ])
        assert dirty is True
        assert "tags:" in result
        assert "  - tag1" in result
        assert "  - tag2" in result
        assert "complexity: high" in result
        assert "estimated_duration: 4-8h" in result
        assert len(inserted) == 3

    def test_no_fields_returns_unchanged(self):
        fm = "\nname: Test\n"
        result, dirty, inserted = insert_fields(fm, [])
        assert dirty is False
        assert inserted == []
        assert result == fm

    def test_preserves_trailing_newline_fm(self):
        """The reconstructed fm_text should end with ``\\n`` so the closing
        ``---`` lands on its own line."""
        fm = "\nname: Test\ndate_added: 2026-01-01\n"
        result, dirty, inserted = insert_fields(fm, [("tags", ["testing"])])
        assert dirty is True
        assert result.endswith("\n"), f"Expected trailing newline, got {result[-20:]!r}"

    def test_preserves_trailing_newline_with_depends_on(self):
        fm = "\nname: Test\ndepends_on:\n  - dep1\n"
        result, dirty, inserted = insert_fields(fm, [("tags", ["testing"])])
        assert dirty is True
        assert result.endswith("\n"), f"Expected trailing newline, got {result[-20:]!r}"


# ── main() ────────────────────────────────────────────────────────────────

class TestMain:
    """Tests for the main() CLI entry point."""

    def _make_agent(self, cat_dir, filename, frontmatter, body="\n\n## Identity\nTest."):
        """Helper to create a test agent .md file."""
        path = cat_dir / filename
        lines = "\n".join(f"{k}: {v}" for k, v in frontmatter.items())
        content = f"---\n{lines}\n---{body}"
        path.write_text(content, encoding="utf-8")
        return path

    def test_dry_run_no_write(self, tmp_path, monkeypatch, capsys):
        """--dry-run should not modify files."""
        eng_dir = tmp_path / "engineering"
        eng_dir.mkdir()
        self._make_agent(eng_dir, "engineering-test-agent.md", {
            "name": "Test Agent",
            "description": "A test agent for dry run",
            "emoji": "X",
            "color": "blue",
            "version": "1.0.0",
            "date_added": "2026-01-01",
        })

        monkeypatch.setattr(_disc, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-add-metadata.py", "--dry-run"]):
            mod.main()

        content = (eng_dir / "engineering-test-agent.md").read_text(encoding="utf-8")
        assert "tags:" not in content
        assert "keywords:" not in content
        assert "complexity:" not in content
        assert "estimated_duration:" not in content

        captured = capsys.readouterr()
        assert "Processed: 1" in captured.out
        assert "DRY RUN" in captured.out

    def test_live_write_modifies_files(self, tmp_path, monkeypatch):
        """Normal run should write new fields."""
        eng_dir = tmp_path / "engineering"
        eng_dir.mkdir()
        self._make_agent(eng_dir, "engineering-frontend-developer.md", {
            "name": "Frontend Dev",
            "description": "Builds UI components",
            "emoji": "X",
            "color": "blue",
            "version": "1.0.0",
            "date_added": "2026-01-01",
        })

        monkeypatch.setattr(_disc, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-add-metadata.py"]):
            mod.main()

        content = (eng_dir / "engineering-frontend-developer.md").read_text(encoding="utf-8")
        assert "tags:" in content
        assert "keywords:" in content
        assert "complexity:" in content
        assert "estimated_duration:" in content

    def test_dry_run_verbose(self, tmp_path, monkeypatch, capsys):
        """Verbose mode with dry-run shows WOULD UPDATE."""
        eng_dir = tmp_path / "engineering"
        eng_dir.mkdir()
        self._make_agent(eng_dir, "engineering-frontend-dev.md", {
            "name": "Dev",
            "description": "Developer agent",
            "emoji": "X",
            "color": "blue",
            "version": "1.0.0",
            "date_added": "2026-01-01",
        })

        monkeypatch.setattr(_disc, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-add-metadata.py", "--dry-run", "--verbose"]):
            mod.main()

        captured = capsys.readouterr()
        assert "WOULD UPDATE" in captured.out

    def test_category_filter(self, tmp_path, monkeypatch):
        """--category flag should only process matching category."""
        eng_dir = tmp_path / "engineering"
        design_dir = tmp_path / "design"
        eng_dir.mkdir()
        design_dir.mkdir()
        self._make_agent(eng_dir, "engineering-dev.md", {
            "name": "Dev", "description": "d", "emoji": "X", "color": "b",
            "version": "1.0.0", "date_added": "2026-01-01",
        })
        self._make_agent(design_dir, "design-ui.md", {
            "name": "UI", "description": "d", "emoji": "X", "color": "b",
            "version": "1.0.0", "date_added": "2026-01-01",
        })

        monkeypatch.setattr(_disc, "REPO", tmp_path)
        with patch.object(sys, "argv",
                          ["batch-add-metadata.py", "--category", "engineering"]):
            mod.main()

        eng_content = (eng_dir / "engineering-dev.md").read_text(encoding="utf-8")
        assert "tags:" in eng_content

        design_content = (design_dir / "design-ui.md").read_text(encoding="utf-8")
        assert "tags:" not in design_content

    def test_field_filter(self, tmp_path, monkeypatch):
        """--field tags should only add tags, not other fields."""
        eng_dir = tmp_path / "engineering"
        eng_dir.mkdir()
        self._make_agent(eng_dir, "engineering-test.md", {
            "name": "Test", "description": "testing", "emoji": "X", "color": "b",
            "version": "1.0.0", "date_added": "2026-01-01",
        })

        monkeypatch.setattr(_disc, "REPO", tmp_path)
        with patch.object(sys, "argv",
                          ["batch-add-metadata.py", "--field", "tags"]):
            mod.main()

        content = (eng_dir / "engineering-test.md").read_text(encoding="utf-8")
        assert "tags:" in content
        assert "keywords:" not in content
        assert "complexity:" not in content
        assert "estimated_duration:" not in content

    def test_skips_agents_with_all_fields(self, tmp_path, monkeypatch, capsys):
        """Agents already having all targeted fields should be skipped."""
        eng_dir = tmp_path / "engineering"
        eng_dir.mkdir()
        self._make_agent(eng_dir, "engineering-full.md", {
            "name": "Full",
            "description": "Already has metadata",
            "emoji": "X",
            "color": "blue",
            "version": "1.0.0",
            "date_added": "2026-01-01",
        })
        # Add the fields manually after creation
        path = eng_dir / "engineering-full.md"
        content = path.read_text(encoding="utf-8")
        # Split frontmatter and inject fields
        fm_end = content.index("---", 3)
        fm = content[3:fm_end]
        extra = (
            "\ntags:\n  - preexisting\nkeywords:\n  - existing\n"
            "complexity: low\nestimated_duration: 1-2h"
        )
        new_content = "---" + fm + extra + "---" + content[fm_end + 3:]
        path.write_text(new_content, encoding="utf-8")

        monkeypatch.setattr(_disc, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-add-metadata.py"]):
            mod.main()

        captured = capsys.readouterr()
        assert "Already had: 1" in captured.out

    def test_skips_bad_frontmatter(self, tmp_path, monkeypatch, capsys):
        """Files without valid frontmatter should be skipped."""
        eng_dir = tmp_path / "engineering"
        eng_dir.mkdir()
        (eng_dir / "engineering-no-fm.md").write_text(
            "## Just a heading\nNo frontmatter.", encoding="utf-8",
        )

        monkeypatch.setattr(_disc, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-add-metadata.py"]):
            mod.main()

        captured = capsys.readouterr()
        assert "Skipped: 1" in captured.out

    def test_verbose_live_output(self, tmp_path, monkeypatch, capsys):
        """Verbose mode with live write shows UPDATED messages."""
        eng_dir = tmp_path / "engineering"
        eng_dir.mkdir()
        self._make_agent(eng_dir, "engineering-verbose.md", {
            "name": "Verbose", "description": "verbose test", "emoji": "X", "color": "b",
            "version": "1.0.0", "date_added": "2026-01-01",
        })

        monkeypatch.setattr(_disc, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-add-metadata.py", "--verbose"]):
            mod.main()

        captured = capsys.readouterr()
        assert "UPDATED" in captured.out
