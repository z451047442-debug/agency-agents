"""Comprehensive tests for scripts/lint-agents.py."""

import importlib.util
from pathlib import Path

import pytest

# ── Import the script as a module ──────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
spec = importlib.util.spec_from_file_location(
    "lint_agents", str(SCRIPTS_DIR / "lint-agents.py")
)
lint_agents = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint_agents)

# Aliases for brevity
get_frontmatter_text = lint_agents.get_frontmatter_text
get_body = lint_agents.get_body
get_field = lint_agents.get_field
get_list_field = lint_agents.get_list_field
discover_agents = lint_agents.discover_agents
lint_file = lint_agents.lint_file
collect_files = lint_agents.collect_files

# ── Import shared helpers ──────────────────────────────────────────────────────

from tests.conftest import SAMPLE_AGENT_CONTENT, make_agent_file


class TestGetFrontmatterText:
    def test_returns_frontmatter(self):
        content = "---\nname: Test\n---\nbody"
        assert get_frontmatter_text(content) == "\nname: Test\n"

    def test_no_delimiters_returns_empty(self):
        assert get_frontmatter_text("plain text") == ""

    def test_only_one_delimiter(self):
        assert get_frontmatter_text("---\nname: Test") == ""


class TestGetBody:
    def test_returns_body(self):
        content = "---\nname: Test\n---\n\nbody text"
        assert get_body(content) == "\n\nbody text"

    def test_no_delimiters_returns_empty(self):
        assert get_body("plain text") == ""


class TestGetField:
    def test_extracts_field_value(self):
        fm = "name: Test Agent\ndescription: A helper"
        assert get_field("name", fm) == "Test Agent"

    def test_missing_field_returns_empty(self):
        assert get_field("nonexistent", "name: Test") == ""

    def test_field_with_colon_in_value(self):
        fm = "description: A: B testing tool"
        assert get_field("description", fm) == "A: B testing tool"


class TestGetListField:
    def test_extracts_list_items(self):
        fm = "nexus_roles:\n  - phase-0-discovery\n  - phase-1-strategy"
        assert get_list_field("nexus_roles", fm) == [
            "phase-0-discovery",
            "phase-1-strategy",
        ]

    def test_quoted_items_stripped(self):
        fm = 'depends_on:\n  - "agent-one"\n  - \'agent-two\''
        assert get_list_field("depends_on", fm) == ["agent-one", "agent-two"]

    def test_empty_list_returns_empty(self):
        fm = "depends_on:\n"
        assert get_list_field("depends_on", fm) == []

    def test_inline_value_not_list(self):
        fm = "depends_on: agent-one"
        assert get_list_field("depends_on", fm) == []

    def test_missing_field_returns_empty(self):
        assert get_list_field("nonexistent", "name: Test") == []

    def test_list_stops_at_non_indented_line(self):
        fm = "nexus_roles:\n  - phase-0-discovery\nnext_field: value"
        assert get_list_field("nexus_roles", fm) == ["phase-0-discovery"]


class TestDiscoverAgents:
    def test_discovers_agents_in_categories(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lint_agents, "REPO", tmp_path)
        # Create category dirs with agents
        (tmp_path / "engineering").mkdir()
        (tmp_path / "engineering" / "agent-a.md").write_text("---\nname: A\n---\nbody")
        (tmp_path / "engineering" / "agent-b.md").write_text("---\nname: B\n---\nbody")
        (tmp_path / "design").mkdir()
        (tmp_path / "design" / "agent-c.md").write_text("---\nname: C\n---\nbody")

        results = list(discover_agents())
        assert len(results) == 3
        categories = [cat for cat, _ in results]
        assert categories == ["design", "engineering", "engineering"]

    def test_excludes_special_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lint_agents, "REPO", tmp_path)
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "skip.md").write_text("---\nname: S\n---\nbody")
        (tmp_path / "engineering").mkdir()
        (tmp_path / "engineering" / "valid.md").write_text("---\nname: V\n---\nbody")

        results = list(discover_agents())
        assert len(results) == 1
        assert results[0][0] == "engineering"

    def test_skips_hidden_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lint_agents, "REPO", tmp_path)
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden" / "nope.md").write_text("---\nname: N\n---\nbody")
        assert list(discover_agents()) == []

    def test_skips_dot_prefix_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lint_agents, "REPO", tmp_path)
        (tmp_path / ".config").mkdir()
        (tmp_path / ".config" / "secret.md").write_text("---\nname: S\n---\nbody")
        assert list(discover_agents()) == []


class TestLintFileValid:
    """Tests where a valid agent file passes clean."""

    def test_valid_agent_passes(self, tmp_path):
        filepath = make_agent_file(tmp_path, SAMPLE_AGENT_CONTENT)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert len(errors) == 0
        # Valid agent should still have infos for missing sections and word count
        # Actually, the SAMPLE has all sections and >100 words, so no warnings either.
        # But SOUL/AGENTS header checks may trigger depending on exact headers
        # Just verify no errors
        assert "ERROR" not in str(errors)

    def test_non_existent_file(self, tmp_path):
        errors, warnings, infos = [], [], []
        lint_file(tmp_path / "does_not_exist.md", errors, warnings, infos)
        assert any("not a file" in e for e in errors)


class TestLintFileCrlf:
    def test_crlf_detected(self, tmp_path):
        content = SAMPLE_AGENT_CONTENT.replace("\n", "\r\n")
        filepath = make_agent_file(tmp_path, content)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("CRLF" in e for e in errors)


class TestLintFileFrontmatter:
    def test_missing_frontmatter_delimiters(self, tmp_path):
        filepath = make_agent_file(tmp_path, "# No frontmatter\n\nJust body text.")
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("missing frontmatter" in e for e in errors)

    def test_empty_frontmatter(self, tmp_path):
        filepath = make_agent_file(tmp_path, "---\n\n---\nbody text here")
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("empty frontmatter" in e for e in errors)

    def test_invalid_yaml(self, tmp_path):
        filepath = make_agent_file(
            tmp_path,
            "---\nname: [unclosed bracket\n---\n\n## Identity\nYou are helpful.\n",
        )
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("invalid YAML" in e for e in errors)

    def test_missing_required_field_name(self, tmp_path):
        content = SAMPLE_AGENT_CONTENT.replace('name: "Test Agent"', "")
        filepath = make_agent_file(tmp_path, content)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("missing frontmatter 'name'" in e for e in errors)

    def test_missing_required_field_description(self, tmp_path):
        content = SAMPLE_AGENT_CONTENT.replace(
            'description: "A test agent for unit testing purposes"', ""
        )
        filepath = make_agent_file(tmp_path, content)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("missing frontmatter 'description'" in e for e in errors)

    def test_missing_required_field_emoji(self, tmp_path):
        import re
        content = re.sub(r'^emoji:.*\n', '', SAMPLE_AGENT_CONTENT, flags=re.MULTILINE)
        filepath = make_agent_file(tmp_path, content)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("missing frontmatter 'emoji'" in e for e in errors)

    def test_missing_required_field_color(self, tmp_path):
        content = SAMPLE_AGENT_CONTENT.replace("color: teal", "")
        filepath = make_agent_file(tmp_path, content)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("missing frontmatter 'color'" in e for e in errors)


class TestLintFileSections:
    def test_missing_identity_section(self, tmp_path):
        content = SAMPLE_AGENT_CONTENT.replace("Identity & Memory", "Something Else")
        filepath = make_agent_file(tmp_path, content)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("missing section 'Identity'" in w for w in warnings)

    def test_missing_mission_section(self, tmp_path):
        content = SAMPLE_AGENT_CONTENT.replace("Core Mission", "Something Else")
        filepath = make_agent_file(tmp_path, content)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("missing section 'Core Mission'" in w for w in warnings)

    def test_missing_rules_section(self, tmp_path):
        content = SAMPLE_AGENT_CONTENT.replace("Critical Rules", "Something Else")
        filepath = make_agent_file(tmp_path, content)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("missing section 'Critical Rules'" in w for w in warnings)


class TestLintFileShortContent:
    def test_short_content_warns(self, tmp_path):
        filepath = make_agent_file(
            tmp_path,
            "---\nname: Short\nemoji: X\ncolor: red\ndescription: Tiny\n---\n\n"
            "## Identity\nJust a few words here.\n",
        )
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("too short" in w for w in warnings)


class TestLintFileNexusRoles:
    def test_invalid_nexus_roles(self, tmp_path):
        content = SAMPLE_AGENT_CONTENT.replace(
            "color: teal", "color: teal\nnexus_roles:\n  - phase-99-invalid"
        )
        filepath = make_agent_file(tmp_path, content)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("unknown nexus_roles" in w for w in warnings)

    def test_valid_nexus_roles_no_warning(self, tmp_path):
        content = SAMPLE_AGENT_CONTENT.replace(
            "color: teal",
            "color: teal\nnexus_roles:\n  - phase-0-discovery\n  - phase-3-build",
        )
        filepath = make_agent_file(tmp_path, content)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        nexus_warnings = [w for w in warnings if "nexus_roles" in w]
        assert len(nexus_warnings) == 0


class TestLintFileFilenamePrefix:
    def test_filename_prefix_mismatch(self, tmp_path):
        filepath = make_agent_file(
            tmp_path, SAMPLE_AGENT_CONTENT,
            category="engineering", filename="wrong-prefix-agent.md",
        )
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("should start with" in w for w in warnings)

    def test_filename_prefix_match(self, tmp_path):
        filepath = make_agent_file(
            tmp_path, SAMPLE_AGENT_CONTENT,
            category="engineering", filename="engineering-test-agent.md",
        )
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        prefix_warnings = [w for w in warnings if "should start with" in w]
        assert len(prefix_warnings) == 0


class TestLintFileBrokenLinks:
    def test_broken_relative_link(self, tmp_path):
        content = SAMPLE_AGENT_CONTENT + "\nSee [other](missing-file.md) for more.\n"
        filepath = make_agent_file(tmp_path, content)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("broken link" in w for w in warnings)

    def test_valid_relative_link(self, tmp_path):
        # Create the target file so the link resolves
        cat_dir = tmp_path / "engineering"
        cat_dir.mkdir(parents=True, exist_ok=True)
        (cat_dir / "target.md").write_text("---\nname: T\n---\nbody")
        content = SAMPLE_AGENT_CONTENT + "\nSee [other](target.md) for more.\n"
        filepath = cat_dir / "engineering-test-agent.md"
        filepath.write_text(content, encoding="utf-8")
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        link_warnings = [w for w in warnings if "broken link" in w]
        assert len(link_warnings) == 0

    def test_http_link_skipped(self, tmp_path):
        content = (
            SAMPLE_AGENT_CONTENT
            + "\nSee [docs](https://example.com/guide.md) for more.\n"
        )
        filepath = make_agent_file(tmp_path, content)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        link_warnings = [w for w in warnings if "broken link" in w]
        assert len(link_warnings) == 0


class TestLintFileDependsOn:
    def test_empty_depends_on_list(self, tmp_path):
        content = SAMPLE_AGENT_CONTENT.replace(
            "color: teal", "color: teal\ndepends_on: []\n"
        )
        filepath = make_agent_file(tmp_path, content)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("depends_on" in i and "empty" in i for i in infos)

    def test_non_empty_depends_on(self, tmp_path):
        content = SAMPLE_AGENT_CONTENT.replace(
            "color: teal",
            "color: teal\ndepends_on:\n  - some-agent\n",
        )
        filepath = make_agent_file(tmp_path, content)
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        dep_infos = [i for i in infos if "depends_on" in i and "empty" in i]
        assert len(dep_infos) == 0


class TestLintFileSoulAgentsHeaders:
    def test_missing_soul_headers(self, tmp_path):
        # Content with no Identity/Rules-style headers (all headers are AGENTS.md)
        filepath = make_agent_file(
            tmp_path,
            "---\nname: Test\nemoji: X\ncolor: red\ndescription: A tester\n---\n\n"
            "## Deliverables\nSome content here.\n\n"
            "## Workflow\nDo this then that.\n\n"
            "## Success Metrics\nMeasure things well.\n\n"
            "## Another Section\nMore content here that adds words to avoid "
            "the short content warning and provides enough text to make this "
            "agent description sufficiently long for validation purposes.\n",
        )
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("no SOUL.md-mapped section headers" in w for w in warnings)

    def test_missing_agents_headers(self, tmp_path):
        # Content with only SOUL.md-mapped headers
        filepath = make_agent_file(
            tmp_path,
            "---\nname: Test\nemoji: X\ncolor: red\ndescription: A tester\n---\n\n"
            "## Your Identity\nYou are a helper.\n\n"
            "## Critical Rules You Must Follow\n1. Be good.\n\n"
            "## Learning & Memory\nRemember everything.\n\n"
            "## Communication Style\nBe concise and clear in your responses "
            "and always provide helpful information to users who ask questions "
            "about the system and its capabilities and limitations.\n",
        )
        errors, warnings, infos = [], [], []
        lint_file(filepath, errors, warnings, infos)
        assert any("no AGENTS.md-mapped section headers" in w for w in warnings)


class TestCollectFiles:
    def test_with_paths_relative(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lint_agents, "REPO", tmp_path)
        filepath = make_agent_file(tmp_path, SAMPLE_AGENT_CONTENT)
        rel = str(filepath.relative_to(tmp_path))
        files = collect_files([rel], all_mode=False)
        assert len(files) == 1
        assert files[0].resolve() == filepath.resolve()

    def test_with_paths_absolute(self, tmp_path):
        filepath = make_agent_file(tmp_path, SAMPLE_AGENT_CONTENT)
        files = collect_files([str(filepath)], all_mode=False)
        assert len(files) == 1
        assert files[0] == filepath

    def test_with_all_mode(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lint_agents, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir()
        (tmp_path / "engineering" / "agent.md").write_text(
            "---\nname: Test\n---\nbody"
        )
        files = collect_files([], all_mode=True)
        assert len(files) == 1
