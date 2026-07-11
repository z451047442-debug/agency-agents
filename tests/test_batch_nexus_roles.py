"""Tests for scripts/batch-nexus-roles.py — NEXUS role assignment logic."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "batch_nexus_roles", str(SCRIPTS_DIR / "batch-nexus-roles.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

parse_frontmatter = mod.parse_frontmatter
has_nexus_roles = mod.has_nexus_roles
add_nexus_roles = mod.add_nexus_roles
assign_roles = mod.assign_roles


# ── parse_frontmatter ────────────────────────────────────────────────────────

class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        content = "---\nname: Test\ndate_added: 2026-01-01\n---\n\n## Body\nSome text."
        result = parse_frontmatter(content)
        assert result is not None
        fm_text, body = result
        assert "name: Test" in fm_text
        assert "## Body" in body

    def test_no_frontmatter_delimiters(self):
        assert parse_frontmatter("# Just a heading\nNo frontmatter here.") is None

    def test_only_opening_delimiter(self):
        assert parse_frontmatter("---\nname: Test\nno closing") is None

    def test_empty_frontmatter_with_body(self):
        result = parse_frontmatter("---\n---\n\nBody content here.")
        assert result is not None
        fm_text, body = result
        assert fm_text.strip() == ""
        assert "Body content" in body

    def test_first_delimiter_pair_is_frontmatter(self):
        content = "---\nname: A\n---\n---\nnot frontmatter\n---"
        result = parse_frontmatter(content)
        assert result is not None
        fm_text, _body = result
        assert "name: A" in fm_text


# ── has_nexus_roles ──────────────────────────────────────────────────────────

class TestHasNexusRoles:
    def test_finds_nexus_roles_field(self):
        fm = "name: Test\ndate_added: 2026-01-01\nnexus_roles:\n  - phase-3-build"
        assert has_nexus_roles(fm) is True

    def test_no_nexus_roles_field(self):
        assert has_nexus_roles("name: Test\ndate_added: 2026-01-01") is False

    def test_empty_frontmatter(self):
        assert has_nexus_roles("") is False

    def test_field_with_inline_comment(self):
        fm = "name: Test\nnexus_roles: # already set\n  - phase-1-strategy"
        assert has_nexus_roles(fm) is True


# ── add_nexus_roles ──────────────────────────────────────────────────────────

class TestAddNexusRoles:
    def test_inserts_after_date_added(self):
        fm = "name: Test\ndate_added: 2026-01-01\ncolor: blue"
        result = add_nexus_roles(fm, ["phase-3-build"])
        lines = result.split("\n")
        idx_date = lines.index("date_added: 2026-01-01")
        idx_nexus = lines.index("nexus_roles:")
        assert idx_nexus == idx_date + 1
        assert "  - phase-3-build" in lines

    def test_multiple_roles(self):
        fm = "name: Test\ndate_added: 2026-01-01"
        result = add_nexus_roles(fm, ["phase-1-strategy", "phase-3-build"])
        lines = result.split("\n")
        assert "  - phase-1-strategy" in lines
        assert "  - phase-3-build" in lines

    def test_no_date_added_appends(self):
        fm = "name: Test\ncolor: blue"
        result = add_nexus_roles(fm, ["phase-6-operate"])
        assert result.endswith("\nnexus_roles:\n  - phase-6-operate")

    def test_empty_frontmatter(self):
        result = add_nexus_roles("", ["phase-0-discovery"])
        assert "nexus_roles:" in result
        assert "  - phase-0-discovery" in result

    def test_preserves_existing_fields(self):
        fm = "name: Agent X\ndate_added: 2026-01-01\ndescription: A helper"
        result = add_nexus_roles(fm, ["phase-5-launch"])
        assert "name: Agent X" in result
        assert "date_added: 2026-01-01" in result
        assert "description: A helper" in result
        assert "nexus_roles:" in result


# ── assign_roles ─────────────────────────────────────────────────────────────

class TestAssignRoles:
    def test_leadership_override_director(self):
        assert assign_roles("engineering-director", "engineering") == ["phase-1-strategy"]

    def test_leadership_override_chief(self):
        assert assign_roles("chief-financial-officer", "finance") == ["phase-1-strategy"]

    def test_leadership_override_ceo(self):
        assert assign_roles("ceo-founder-coach", "strategy") == ["phase-1-strategy"]

    def test_leadership_override_cto(self):
        assert assign_roles("cto-advisor", "engineering") == ["phase-1-strategy"]

    def test_keyword_match_first_rule_wins(self):
        result = assign_roles("engineering-sre-monitoring-engineer", "engineering")
        assert result == ["phase-2-foundation", "phase-6-operate"]

    def test_keyword_match_security(self):
        result = assign_roles("engineering-appsec-engineer", "engineering")
        assert result == ["phase-4-hardening"]

    def test_fallback_to_none_pattern(self):
        result = assign_roles("engineering-generic-helper", "engineering")
        assert result == ["phase-3-build"]

    def test_default_by_category(self):
        result = assign_roles("healthcare-nurse-consultant", "healthcare")
        assert result == ["phase-3-build", "phase-4-hardening"]

    def test_unknown_category_returns_none(self):
        assert assign_roles("some-agent", "nonexistent-category") is None

    def test_strategy_category_default(self):
        result = assign_roles("strategy-business-analyst", "strategy")
        assert result == ["phase-0-discovery", "phase-1-strategy"]

    def test_product_trend_gets_discovery(self):
        assert assign_roles("product-trend-researcher", "product") == ["phase-0-discovery"]

    def test_product_growth_gets_launch(self):
        assert assign_roles("product-growth-hacker", "product") == ["phase-5-launch"]

    def test_design_brand_gets_strategy_launch(self):
        result = assign_roles("design-brand-strategist", "design")
        assert result == ["phase-1-strategy", "phase-5-launch"]

    def test_marketing_seo_gets_launch(self):
        assert assign_roles("marketing-seo-specialist", "marketing") == ["phase-5-launch"]

    def test_legal_default(self):
        result = assign_roles("legal-compliance-attorney", "legal")
        assert result == ["phase-0-discovery", "phase-1-strategy"]

    def test_data_science_engineer_gets_build(self):
        result = assign_roles("data-science-machine-learning-engineer", "data-science")
        assert result == ["phase-2-foundation", "phase-3-build"]


# ── main() function ─────────────────────────────────────────────────────────

class TestMainFunction:
    """Tests for the main() function covering lines 250-309."""

    def _make_agent_file(self, cat_dir, filename, frontmatter, body="\n\n## Identity\nTest."):
        """Helper to create a test agent .md file."""
        path = cat_dir / filename
        fm_str = "\n".join(f"{k}: {v}" for k, v in frontmatter.items())
        content = f"---\n{fm_str}\n---{body}"
        path.write_text(content, encoding="utf-8")
        return path

    def test_dry_run_no_write(self, tmp_path, monkeypatch, capsys):
        """Lines 295-299: --dry-run does not modify files."""
        eng_dir = tmp_path / "engineering"
        eng_dir.mkdir()
        self._make_agent_file(eng_dir, "engineering-test-agent.md", {
            "name": "Test Agent",
            "description": "A test",
            "emoji": "X",
            "color": "blue",
            "version": "1.0.0",
            "date_added": "2026-01-01",
        })

        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-nexus-roles.py", "--dry-run"]):
            mod.main()

        # File should NOT have been modified (no nexus_roles added)
        content = (eng_dir / "engineering-test-agent.md").read_text(encoding="utf-8")
        assert "nexus_roles:" not in content

        captured = capsys.readouterr()
        assert "Assigned: 1" in captured.out
        assert "DRY RUN" in captured.out

    def test_dry_run_verbose(self, tmp_path, monkeypatch, capsys):
        """Verbose mode with dry-run shows WOULD UPDATE output."""
        eng_dir = tmp_path / "engineering"
        eng_dir.mkdir()
        self._make_agent_file(eng_dir, "engineering-dev-agent.md", {
            "name": "Dev Agent",
            "description": "Developer",
            "emoji": "X",
            "color": "blue",
            "version": "1.0.0",
            "date_added": "2026-01-01",
        })

        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv",
                          ["batch-nexus-roles.py", "--dry-run", "--verbose"]):
            mod.main()

        captured = capsys.readouterr()
        assert "WOULD UPDATE" in captured.out

    def test_live_write_modifies_files(self, tmp_path, monkeypatch):
        """Lines 300-305: Actual write modifies agent files."""
        eng_dir = tmp_path / "engineering"
        eng_dir.mkdir()
        self._make_agent_file(eng_dir, "engineering-dev-agent.md", {
            "name": "Dev Agent",
            "description": "Developer",
            "emoji": "X",
            "color": "blue",
            "version": "1.0.0",
            "date_added": "2026-01-01",
        })

        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-nexus-roles.py"]):
            mod.main()

        content = (eng_dir / "engineering-dev-agent.md").read_text(encoding="utf-8")
        assert "nexus_roles:" in content

    def test_live_write_verbose(self, tmp_path, monkeypatch, capsys):
        """Live write with verbose flag shows UPDATED messages."""
        eng_dir = tmp_path / "engineering"
        eng_dir.mkdir()
        self._make_agent_file(eng_dir, "engineering-dev-agent.md", {
            "name": "Dev Agent",
            "description": "Developer",
            "emoji": "X",
            "color": "blue",
            "version": "1.0.0",
            "date_added": "2026-01-01",
        })

        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv",
                          ["batch-nexus-roles.py", "--verbose"]):
            mod.main()

        captured = capsys.readouterr()
        assert "UPDATED" in captured.out

    def test_category_filter(self, tmp_path, monkeypatch):
        """--category flag only processes matching category."""
        eng_dir = tmp_path / "engineering"
        design_dir = tmp_path / "design"
        eng_dir.mkdir()
        design_dir.mkdir()
        self._make_agent_file(eng_dir, "engineering-dev.md", {
            "name": "Dev", "description": "d", "emoji": "X", "color": "b",
            "version": "1.0.0", "date_added": "2026-01-01",
        })
        self._make_agent_file(design_dir, "design-ui.md", {
            "name": "UI", "description": "d", "emoji": "X", "color": "b",
            "version": "1.0.0", "date_added": "2026-01-01",
        })

        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv",
                          ["batch-nexus-roles.py", "--category", "engineering"]):
            mod.main()

        # Only engineering file should be modified
        eng_content = (eng_dir / "engineering-dev.md").read_text(encoding="utf-8")
        assert "nexus_roles:" in eng_content

        design_content = (design_dir / "design-ui.md").read_text(encoding="utf-8")
        assert "nexus_roles:" not in design_content

    def test_already_has_roles(self, tmp_path, monkeypatch, capsys):
        """Agent with existing nexus_roles increments 'already' counter."""
        eng_dir = tmp_path / "engineering"
        eng_dir.mkdir()
        self._make_agent_file(eng_dir, "engineering-with-roles.md", {
            "name": "Has Roles",
            "description": "Already assigned",
            "emoji": "X",
            "color": "blue",
            "version": "1.0.0",
            "date_added": "2026-01-01",
            "nexus_roles": '  # already present\n  - phase-3-build',
        })

        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-nexus-roles.py"]):
            mod.main()

        captured = capsys.readouterr()
        assert "Already had: 1" in captured.out

    def test_skipped_unknown_category(self, tmp_path, monkeypatch, capsys):
        """Agent in unknown category gets skipped (assign_roles returns None)."""
        unknown_dir = tmp_path / "zzz-unknown"
        unknown_dir.mkdir()
        self._make_agent_file(unknown_dir, "zzz-unknown-agent.md", {
            "name": "Unknown",
            "description": "Unknown category",
            "emoji": "X",
            "color": "blue",
            "version": "1.0.0",
            "date_added": "2026-01-01",
        })

        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-nexus-roles.py"]):
            mod.main()

        captured = capsys.readouterr()
        assert "Skipped: 1" in captured.out

    def test_no_valid_md_files(self, tmp_path, monkeypatch, capsys):
        """No valid agent files — all counts zero."""
        (tmp_path / "empty-dir").mkdir()

        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-nexus-roles.py"]):
            mod.main()

        captured = capsys.readouterr()
        assert "Assigned: 0" in captured.out
        assert "Already had: 0" in captured.out
        assert "Skipped: 0" in captured.out

    def test_skips_non_directories(self, tmp_path, monkeypatch, capsys):
        """Line 268: skip files (non-directories) in REPO root."""
        (tmp_path / "README.txt").write_text("not a dir", encoding="utf-8")

        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-nexus-roles.py"]):
            mod.main()

        captured = capsys.readouterr()
        assert "Assigned: 0" in captured.out

    def test_skips_hidden_dirs(self, tmp_path, monkeypatch, capsys):
        """Line 268: skip directories starting with dot."""
        (tmp_path / ".hidden-dir").mkdir()
        self._make_agent_file(tmp_path / ".hidden-dir", "hidden-agent.md", {
            "name": "H", "description": "d", "emoji": "X", "color": "b",
            "version": "1.0.0", "date_added": "2026-01-01",
        })

        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-nexus-roles.py"]):
            mod.main()

        captured = capsys.readouterr()
        assert "Assigned: 0" in captured.out

    def test_skips_excluded_dirs(self, tmp_path, monkeypatch, capsys):
        """Line 270: skip directories in EXCLUDE set."""
        (tmp_path / "docs").mkdir()
        self._make_agent_file(tmp_path / "docs", "some-doc.md", {
            "name": "D", "description": "d", "emoji": "X", "color": "b",
            "version": "1.0.0", "date_added": "2026-01-01",
        })

        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-nexus-roles.py"]):
            mod.main()

        captured = capsys.readouterr()
        assert "Assigned: 0" in captured.out

    def test_skips_bad_frontmatter(self, tmp_path, monkeypatch, capsys):
        """Line 279: skip .md files without valid frontmatter."""
        eng_dir = tmp_path / "engineering"
        eng_dir.mkdir()
        # File without YAML frontmatter delimiters
        (eng_dir / "engineering-no-fm.md").write_text(
            "## Just a heading\nNo frontmatter here.", encoding="utf-8"
        )

        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["batch-nexus-roles.py"]):
            mod.main()

        captured = capsys.readouterr()
        assert "Assigned: 0" in captured.out
