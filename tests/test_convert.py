"""Comprehensive tests for scripts/convert.py."""

import importlib.util
from pathlib import Path

import pytest

# ── Import the script as a module ──────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
spec = importlib.util.spec_from_file_location(
    "convert", str(SCRIPTS_DIR / "convert.py")
)
convert = importlib.util.module_from_spec(spec)
spec.loader.exec_module(convert)

# Aliases
get_field = convert.get_field
get_frontmatter_text = convert.get_frontmatter_text
get_body = convert.get_body
slugify = convert.slugify
discover_agents = convert.discover_agents
_write_frontmatter = convert._write_frontmatter
convert_cursor = convert.convert_cursor
convert_gemini_cli = convert.convert_gemini_cli
convert_codex = convert.convert_codex
convert_opencode = convert.convert_opencode
convert_kimi = convert.convert_kimi
convert_antigravity = convert.convert_antigravity
convert_osaurus = convert.convert_osaurus
convert_qwen = convert.convert_qwen
convert_openclaw = convert.convert_openclaw
build_aider_windsurf = convert.build_aider_windsurf
clean_tool_output = convert.clean_tool_output
run_tool = convert.run_tool
resolve_opencode_color = convert.resolve_opencode_color
progress_bar = convert.progress_bar
_toml_escape = convert._toml_escape

# ── Shared helpers ─────────────────────────────────────────────────────────────

from tests.conftest import make_agent_file

# Minimal agent data for converter tests
AGENT_NAME = "Test Agent"
AGENT_DESC = "A test agent for unit testing"
AGENT_BODY = "## Identity\nYou are a test agent.\n\n## Mission\nHelp with testing.\n"
AGENT_FM_TEXT = 'name: "Test Agent"\ndescription: "A test agent for unit testing"\nemoji: X\ncolor: red\n'

FULL_AGENT_CONTENT = """\
---
name: "Test Agent"
description: "A test agent for unit testing"
emoji: X
color: red
---

## Identity
You are a test agent.

## Mission
Help with testing.

## Critical Rules
1. Be thorough.
2. Test everything.
"""


class TestGetField:
    def test_extracts_field(self):
        assert get_field("name", 'name: "Test Agent"\ndescription: Desc\n') == '"Test Agent"'

    def test_missing_returns_empty(self):
        assert get_field("nonexistent", "name: Test") == ""

    def test_multiline_safe(self):
        fm = "name: Test\ndescription: A longer\n  description here"
        # get_field with .*?$ captures only first line
        assert get_field("description", fm) == "A longer"


class TestGetFrontmatterText:
    def test_returns_frontmatter(self):
        assert get_frontmatter_text("---\nname: T\n---\nbody") == "\nname: T\n"

    def test_no_delimiters(self):
        assert get_frontmatter_text("plain") == ""


class TestGetBody:
    def test_returns_body(self):
        assert get_body("---\nfm\n---\n\nbody here") == "\n\nbody here"

    def test_no_delimiters_returns_content(self):
        assert get_body("just text") == "just text"


class TestSlugify:
    def test_basic(self):
        assert slugify("Test Agent") == "test-agent"

    def test_special_characters(self):
        assert slugify("Hello, World!") == "hello-world"

    def test_multiple_special_chars(self):
        assert slugify("Foo & Bar: Baz") == "foo-bar-baz"

    def test_multiple_dashes_collapsed(self):
        assert slugify("a---b") == "a-b"

    def test_leading_trailing_dashes_removed(self):
        assert slugify("-hello-") == "hello"

    def test_already_kebab(self):
        assert slugify("already-kebab") == "already-kebab"

    def test_uppercase(self):
        assert slugify("UPPERCASE NAME") == "uppercase-name"

    def test_numbers_preserved(self):
        assert slugify("Agent 3000") == "agent-3000"


class TestDiscoverAgents:
    def test_discovers_agents(self, tmp_path, monkeypatch):
        monkeypatch.setattr(convert, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir()
        (tmp_path / "engineering" / "agent.md").write_text(
            '---\nname: "Test"\ndescription: "Desc"\n---\n\nBody text.\n',
            encoding="utf-8",
        )
        results = list(discover_agents())
        assert len(results) == 1
        category, filepath, fm_text, body = results[0]
        assert category == "engineering"
        assert body.startswith("Body text.")

    def test_skips_invalid_agents(self, tmp_path, monkeypatch):
        monkeypatch.setattr(convert, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir()
        # Missing frontmatter
        (tmp_path / "engineering" / "no-fm.md").write_text("Just text.", encoding="utf-8")
        # Missing name field
        (tmp_path / "engineering" / "no-name.md").write_text(
            "---\ndescription: Desc\n---\nBody.", encoding="utf-8"
        )
        # Valid agent
        (tmp_path / "engineering" / "valid.md").write_text(
            '---\nname: "Valid"\ndescription: "Desc"\n---\nBody.', encoding="utf-8"
        )
        results = list(discover_agents())
        assert len(results) == 1

    def test_excludes_special_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(convert, "REPO", tmp_path)
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "skip.md").write_text(
            '---\nname: "Skip"\ndescription: "Desc"\n---\nBody.', encoding="utf-8"
        )
        assert list(discover_agents()) == []


class TestWriteFrontmatter:
    def test_writes_correctly(self, tmp_path):
        out = tmp_path / "test.md"
        _write_frontmatter(out, {"name": "Test", "description": "Desc"}, "Body text.\n")
        content = out.read_text(encoding="utf-8")
        assert "---" in content
        assert "name: Test" in content
        assert "description: Desc" in content
        assert "Body text." in content

    def test_creates_parent_dirs(self, tmp_path):
        out = tmp_path / "deep" / "nested" / "file.md"
        _write_frontmatter(out, {"key": "val"}, "Body.\n")
        assert out.exists()

    def test_body_without_trailing_newline(self, tmp_path):
        out = tmp_path / "test.md"
        _write_frontmatter(out, {"key": "val"}, "No newline")
        content = out.read_text(encoding="utf-8")
        assert content.endswith("\n")


# ── Converter tests ────────────────────────────────────────────────────────────

class TestConvertCursor:
    def test_creates_rule_file(self, tmp_path):
        out_dir = tmp_path / "cursor"
        convert_cursor(AGENT_NAME, AGENT_DESC, AGENT_BODY, out_dir)
        rule_file = out_dir / "rules" / "test-agent.mdc"
        assert rule_file.exists()
        content = rule_file.read_text(encoding="utf-8")
        assert "description: A test agent for unit testing" in content
        assert "globs:" in content
        assert "alwaysApply: false" in content
        assert "You are a test agent." in content


class TestConvertGeminiCli:
    def test_creates_agent_file(self, tmp_path):
        out_dir = tmp_path / "gemini-cli"
        convert_gemini_cli(AGENT_NAME, AGENT_DESC, AGENT_BODY, out_dir)
        agent_file = out_dir / "agents" / "test-agent.md"
        assert agent_file.exists()
        content = agent_file.read_text(encoding="utf-8")
        assert "name: test-agent" in content
        assert "description: A test agent for unit testing" in content
        assert "You are a test agent." in content


class TestConvertCodex:
    def test_creates_toml_file(self, tmp_path):
        out_dir = tmp_path / "codex"
        convert_codex(AGENT_NAME, AGENT_DESC, AGENT_BODY, out_dir)
        toml_file = out_dir / "agents" / "test-agent.toml"
        assert toml_file.exists()
        content = toml_file.read_text(encoding="utf-8")
        assert 'name = "Test Agent"' in content
        assert "description = " in content
        # Body should be escaped
        assert "developer_instructions = " in content


class TestConvertOpencode:
    def test_creates_agent_file(self, tmp_path):
        out_dir = tmp_path / "opencode"
        convert_opencode(AGENT_NAME, AGENT_DESC, AGENT_BODY, out_dir)
        agent_file = out_dir / "agents" / "test-agent.md"
        assert agent_file.exists()
        content = agent_file.read_text(encoding="utf-8")
        assert "name: Test Agent" in content
        assert "mode: subagent" in content
        assert "color: '#6B7280'" in content


class TestConvertKimi:
    def test_creates_yaml_and_system_md(self, tmp_path):
        out_dir = tmp_path / "kimi"
        convert_kimi(AGENT_NAME, AGENT_DESC, AGENT_BODY, out_dir)
        yaml_file = out_dir / "test-agent" / "agent.yaml"
        system_file = out_dir / "test-agent" / "system.md"
        assert yaml_file.exists()
        assert system_file.exists()
        yaml_content = yaml_file.read_text(encoding="utf-8")
        assert "name: test-agent" in yaml_content
        assert "system_prompt_path: ./system.md" in yaml_content
        system_content = system_file.read_text(encoding="utf-8")
        assert "# Test Agent" in system_content
        assert AGENT_BODY in system_content


class TestConvertAntigravity:
    def test_creates_skill_file(self, tmp_path):
        out_dir = tmp_path / "antigravity"
        convert_antigravity(AGENT_NAME, AGENT_DESC, AGENT_BODY, out_dir)
        skill_file = out_dir / "agency-test-agent" / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text(encoding="utf-8")
        assert "name: agency-test-agent" in content
        assert "risk: low" in content
        assert "source: community" in content


class TestConvertOsaurus:
    def test_creates_skill_file(self, tmp_path):
        out_dir = tmp_path / "osaurus"
        convert_osaurus(AGENT_NAME, AGENT_DESC, AGENT_BODY, out_dir)
        skill_file = out_dir / "agency-test-agent" / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text(encoding="utf-8")
        assert "name: agency-test-agent" in content
        assert "description: A test agent for unit testing" in content


class TestConvertQwen:
    def test_creates_agent_file_without_tools(self, tmp_path):
        out_dir = tmp_path / "qwen"
        convert_qwen(AGENT_NAME, AGENT_DESC, AGENT_BODY, out_dir, "")
        agent_file = out_dir / "agents" / "test-agent.md"
        assert agent_file.exists()
        content = agent_file.read_text(encoding="utf-8")
        assert "name: test-agent" in content
        assert "tools:" not in content

    def test_creates_agent_file_with_tools(self, tmp_path):
        out_dir = tmp_path / "qwen"
        fm = 'tools: "search, code_execution"\n'
        convert_qwen(AGENT_NAME, AGENT_DESC, AGENT_BODY, out_dir, fm)
        agent_file = out_dir / "agents" / "test-agent.md"
        content = agent_file.read_text(encoding="utf-8")
        assert "tools:" in content


class TestConvertOpenclaw:
    def test_creates_split_files(self, tmp_path):
        out_dir = tmp_path / "openclaw"
        fm_text = "emoji: X\nvibe: Friendly and helpful\n"
        body = (
            "## \U0001f9e0 Your Identity\nYou are a test agent.\n\n"
            "## Critical Rules You Must Follow\n1. Be thorough.\n\n"
            "## Mission\nHelp with testing.\n\n"
            "## Deliverables\nReports and analysis.\n"
        )
        convert_openclaw(AGENT_NAME, AGENT_DESC, body, out_dir, fm_text)
        agent_dir = out_dir / "test-agent"
        assert agent_dir.exists()
        # SOUL.md should have identity + rules
        soul = (agent_dir / "SOUL.md").read_text(encoding="utf-8")
        assert "Your Identity" in soul
        assert "Critical Rules" in soul
        # AGENTS.md should have mission + deliverables
        agents = (agent_dir / "AGENTS.md").read_text(encoding="utf-8")
        assert "Mission" in agents
        assert "Deliverables" in agents
        # IDENTITY.md should have emoji + name + vibe
        identity = (agent_dir / "IDENTITY.md").read_text(encoding="utf-8")
        assert "Friendly and helpful" in identity

    def test_creates_identity_without_emoji_vibe(self, tmp_path):
        out_dir = tmp_path / "openclaw"
        body = "## Identity\nYou are a test agent.\n\n## Mission\nHelp with testing.\n"
        convert_openclaw(AGENT_NAME, AGENT_DESC, body, out_dir, "")
        identity = (out_dir / "test-agent" / "IDENTITY.md").read_text(encoding="utf-8")
        assert AGENT_DESC in identity


class TestBuildAiderWindsurf:
    def test_build_aider(self, tmp_path):
        out_dir = tmp_path / "aider"
        agents = [("Agent One", "First agent", "Body of first.\n")]
        build_aider_windsurf(agents, out_dir, "aider")
        output_file = out_dir / "aider" / "CONVENTIONS.md"
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "# The Agency" in content
        assert "---" in content
        assert "Agent One" in content
        assert "First agent" in content
        assert "Body of first." in content

    def test_build_windsurf(self, tmp_path):
        out_dir = tmp_path / "windsurf"
        agents = [("Agent Two", "Second agent", "Body of second.\n")]
        build_aider_windsurf(agents, out_dir, "windsurf")
        output_file = out_dir / "windsurf" / ".windsurfrules"
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "Agent Two" in content
        assert "Second agent" in content
        assert "=" * 80 in content

    def test_multiple_agents(self, tmp_path):
        out_dir = tmp_path / "aider"
        agents = [
            ("Agent A", "First", "Body A.\n"),
            ("Agent B", "Second", "Body B.\n"),
        ]
        build_aider_windsurf(agents, out_dir, "aider")
        content = (out_dir / "aider" / "CONVENTIONS.md").read_text(encoding="utf-8")
        # header has no ---, each pair is joined by a --- separator: 2 separators expected
        assert content.count("---") >= 2


class TestCleanToolOutput:
    def test_removes_output_preserves_readme(self, tmp_path):
        tool_dir = tmp_path / "cursor"
        tool_dir.mkdir(parents=True)
        (tool_dir / "README.md").write_text("Keep me.")
        (tool_dir / "rules").mkdir()
        (tool_dir / "rules" / "agent.mdc").write_text("Remove me.")
        (tool_dir / "other_file.txt").write_text("Remove me too.")

        clean_tool_output("cursor", tmp_path)

        assert (tool_dir / "README.md").exists()
        assert not (tool_dir / "rules").exists()
        assert not (tool_dir / "other_file.txt").exists()

    def test_noop_if_dir_missing(self, tmp_path):
        # Should not raise
        clean_tool_output("nonexistent", tmp_path)


class TestRunTool:
    def test_run_tool_cursor(self, tmp_path, monkeypatch):
        monkeypatch.setattr(convert, "REPO", tmp_path)
        # Create a mock agent file
        (tmp_path / "engineering").mkdir()
        (tmp_path / "engineering" / "agent.md").write_text(
            '---\nname: "Test Agent"\ndescription: "A test agent"\n---\n\nBody.\n',
            encoding="utf-8",
        )
        agents = list(discover_agents())
        assert len(agents) == 1

        out_dir = tmp_path / "integrations"
        count = run_tool("cursor", agents, out_dir)
        assert count == 1
        rule_file = out_dir / "cursor" / "rules" / "test-agent.mdc"
        assert rule_file.exists()

    def test_run_tool_aider(self, tmp_path, monkeypatch):
        monkeypatch.setattr(convert, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir()
        (tmp_path / "engineering" / "agent.md").write_text(
            '---\nname: "Test Agent"\ndescription: "A test agent"\n---\n\nBody.\n',
            encoding="utf-8",
        )
        agents = list(discover_agents())
        out_dir = tmp_path / "integrations"
        count = run_tool("aider", agents, out_dir)
        assert count == 1
        conventions = out_dir / "aider" / "CONVENTIONS.md"
        assert conventions.exists()

    def test_run_tool_skips_missing_fields(self, tmp_path, monkeypatch):
        monkeypatch.setattr(convert, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir()
        # Agent with no description
        (tmp_path / "engineering" / "bad.md").write_text(
            '---\nname: "Bad Agent"\n---\n\nBody.\n', encoding="utf-8"
        )
        agents = list(discover_agents())
        out_dir = tmp_path / "integrations"
        count = run_tool("cursor", agents, out_dir)
        assert count == 0


# ── resolve_opencode_color ───────────────────────────────────────────────────

class TestResolveOpencodeColor:
    def test_returns_default_when_empty(self):
        assert resolve_opencode_color("") == "#6B7280"

    def test_returns_default_when_none(self):
        assert resolve_opencode_color(None) == "#6B7280"

    def test_known_color_returns_hex(self):
        assert resolve_opencode_color("red") == "#E74C3C"

    def test_known_color_case_insensitive(self):
        assert resolve_opencode_color("BLUE") == "#3498DB"

    def test_unknown_color_falls_back(self):
        assert resolve_opencode_color("chartreuse") == "#6B7280"

    def test_hex_with_hash_normalized_uppercase(self):
        result = resolve_opencode_color("#a1b2c3")
        assert result == "#A1B2C3"

    def test_hex_without_hash_gets_prefixed(self):
        result = resolve_opencode_color("a1b2c3")
        assert result == "#A1B2C3"

    def test_whitespace_stripped(self):
        assert resolve_opencode_color("  cyan  ") == "#00FFFF"


# ── progress_bar ─────────────────────────────────────────────────────────────

class TestProgressBar:
    def test_zero_total_no_output(self, capfd):
        progress_bar(1, 0)
        captured = capfd.readouterr()
        assert captured.err == ""

    def test_full_completion_bar(self, capfd):
        progress_bar(10, 10, width=10)
        captured = capfd.readouterr()
        assert "10/10" in captured.err

    def test_empty_bar(self, capfd):
        progress_bar(0, 10, width=10)
        captured = capfd.readouterr()
        assert "0/10" in captured.err

    def test_includes_progress_fraction(self, capfd):
        progress_bar(5, 10, width=10)
        captured = capfd.readouterr()
        assert "5/10" in captured.err


# ── _toml_escape ─────────────────────────────────────────────────────────────

class TestTomlEscape:
    def test_plain_text_unchanged(self):
        assert _toml_escape("hello world") == "hello world"

    def test_escapes_backslash(self):
        assert _toml_escape("a\\b") == "a\\\\b"

    def test_escapes_double_quote(self):
        assert _toml_escape('say "hi"') == 'say \\"hi\\"'

    def test_escapes_newline(self):
        assert _toml_escape("a\nb") == "a\\nb"

    def test_escapes_carriage_return(self):
        assert _toml_escape("a\rb") == "a\\rb"

    def test_escapes_tab(self):
        assert _toml_escape("a\tb") == "a\\tb"

    def test_escapes_backspace(self):
        assert _toml_escape("a\x08b") == "a\\bb"

    def test_escapes_control_characters(self):
        # Null byte
        result = _toml_escape("a\x00b")
        assert "\\u0000" in result

    def test_escapes_del_character(self):
        result = _toml_escape("a\x7Fb")
        assert "\\u007F" in result
