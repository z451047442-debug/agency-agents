"""Tests for scripts/build-hermes-plugin.py — Hermes plugin builder."""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "build_hermes_plugin", str(SCRIPTS_DIR / "build-hermes-plugin.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

slugify = mod.slugify
parse_agent = mod.parse_agent
collect_agents = mod.collect_agents
plugin_yaml = mod.plugin_yaml
init_py = mod.init_py
readme = mod.readme

MINIMAL_AGENT = (
    "---\n"
    'name: "Graphic Designer"\n'
    'description: "Creates visual designs and layouts"\n'
    'emoji: "\U0001f3a8"\n'
    "color: purple\n"
    "vibe: creative, detail-oriented\n"
    "---\n"
    "\n"
    "## Identity\n"
    "You are a graphic designer with 10 years of experience.\n"
    "\n"
    "## Mission\n"
    "Create beautiful, functional designs.\n"
    "\n"
    "## Rules\n"
    "Always follow brand guidelines.\n"
)


# ── slugify ──────────────────────────────────────────────────────────────────

class TestSlugify:
    def test_basic_lowercase(self):
        assert slugify("Graphic Designer") == "graphic-designer"

    def test_special_characters(self):
        assert slugify("C++ Developer & Architect") == "c-developer-architect"

    def test_multiple_special_chars(self):
        assert slugify("Hey!!! --- World") == "hey-world"

    def test_leading_trailing_dashes_removed(self):
        assert slugify("---hello---") == "hello"

    def test_already_kebab(self):
        assert slugify("already-kebab-case") == "already-kebab-case"

    def test_uppercase(self):
        assert slugify("UPPERCASE NAME") == "uppercase-name"

    def test_numbers_preserved(self):
        assert slugify("test 123 agent v2") == "test-123-agent-v2"

    def test_chinese_characters_removed(self):
        # Non-ASCII characters are stripped by the regex
        result = slugify("设计师 agent")
        assert "agent" in result
        # Only ASCII a-z0-9 remain
        assert all(c.isascii() for c in result.replace("-", ""))


# ── parse_agent ──────────────────────────────────────────────────────────────

class TestParseAgent:
    def test_parses_valid_agent(self, tmp_path):
        repo = tmp_path / "repo"
        design_dir = repo / "design"
        design_dir.mkdir(parents=True)
        agent_path = design_dir / "design-graphic-designer.md"
        agent_path.write_text(MINIMAL_AGENT, encoding="utf-8")

        result = parse_agent(agent_path, repo)
        assert result is not None
        assert result["name"] == "Graphic Designer"
        assert result["slug"] == "design-graphic-designer"
        assert result["division"] == "design"
        assert result["color"] == "purple"
        assert result["emoji"] == "🎨"
        assert result["description"] == "Creates visual designs and layouts"

    def test_no_frontmatter_returns_none(self, tmp_path):
        repo = tmp_path / "repo"
        (repo / "design").mkdir(parents=True)
        path = repo / "design" / "bad.md"
        path.write_text("# No frontmatter\nJust content.", encoding="utf-8")
        assert parse_agent(path, repo) is None

    def test_only_one_delimiter_returns_none(self, tmp_path):
        repo = tmp_path / "repo"
        (repo / "design").mkdir(parents=True)
        path = repo / "design" / "bad.md"
        path.write_text("---\nname: Test\nno closing", encoding="utf-8")
        assert parse_agent(path, repo) is None

    def test_missing_name_returns_none(self, tmp_path):
        repo = tmp_path / "repo"
        (repo / "design").mkdir(parents=True)
        path = repo / "design" / "noname.md"
        path.write_text("---\ndescription: No name here\n---\n\n## Body", encoding="utf-8")
        assert parse_agent(path, repo) is None

    def test_source_path_is_relative(self, tmp_path):
        repo = tmp_path / "repo"
        (repo / "design").mkdir(parents=True)
        path = repo / "design" / "design-agent.md"
        path.write_text(MINIMAL_AGENT, encoding="utf-8")
        result = parse_agent(path, repo)
        assert result["source_path"].replace("\\", "/") == "design/design-agent.md"

    def test_body_preserved(self, tmp_path):
        repo = tmp_path / "repo"
        (repo / "design").mkdir(parents=True)
        path = repo / "design" / "design-agent.md"
        path.write_text(MINIMAL_AGENT, encoding="utf-8")
        result = parse_agent(path, repo)
        assert "## Identity" in result["body"]
        assert "graphic designer" in result["body"].lower()


# ── collect_agents ───────────────────────────────────────────────────────────

class TestCollectAgents:
    def test_collects_from_multiple_directories(self, tmp_path):
        repo = tmp_path / "repo"
        for cat in ("engineering", "design"):
            (repo / cat).mkdir(parents=True)
            agent = (
                f"---\n"
                f'name: "{cat} Agent"\n'
                f'description: "A {cat} agent"\n'
                f"emoji: V\n"
                f"color: blue\n"
                f"---\n\n## Body\n"
            )
            (repo / cat / f"{cat}-agent.md").write_text(agent, encoding="utf-8")

        # Override AGENT_DIRS to only include our test dirs
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(mod, "AGENT_DIRS", ["engineering", "design"])
            agents = collect_agents(repo)

        assert len(agents) == 2
        divisions = {a["division"] for a in agents}
        assert divisions == {"engineering", "design"}

    def test_skips_nonexistent_dirs(self, tmp_path):
        repo = tmp_path / "repo"
        (repo / "design").mkdir(parents=True)
        agent_path = repo / "design" / "design-agent.md"
        agent_path.write_text(MINIMAL_AGENT, encoding="utf-8")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(mod, "AGENT_DIRS", ["design", "fake-dir"])
            agents = collect_agents(repo)

        assert len(agents) > 0
        assert all(a["division"] == "design" for a in agents)

    def test_skips_invalid_files(self, tmp_path):
        repo = tmp_path / "repo"
        (repo / "design").mkdir(parents=True)
        (repo / "design" / "good.md").write_text(MINIMAL_AGENT, encoding="utf-8")
        (repo / "design" / "bad.md").write_text("No frontmatter here.", encoding="utf-8")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(mod, "AGENT_DIRS", ["design"])
            agents = collect_agents(repo)

        assert len(agents) == 1

    def test_sorts_by_division_then_slug(self, tmp_path):
        repo = tmp_path / "repo"
        for cat in ("design", "engineering"):
            (repo / cat).mkdir(parents=True)
        (repo / "design" / "design-zeta.md").write_text(
            '---\nname: "Zeta"\ndescription: "desc"\nemoji: Z\ncolor: blue\n---\n\nbody', encoding="utf-8")
        (repo / "design" / "design-alpha.md").write_text(
            '---\nname: "Alpha"\ndescription: "desc"\nemoji: A\ncolor: blue\n---\n\nbody', encoding="utf-8")
        (repo / "engineering" / "engineering-beta.md").write_text(
            '---\nname: "Beta"\ndescription: "desc"\nemoji: B\ncolor: blue\n---\n\nbody', encoding="utf-8")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(mod, "AGENT_DIRS", ["design", "engineering"])
            agents = collect_agents(repo)

        slugs = [a["slug"] for a in agents]
        # design comes before engineering, alpha before zeta within design
        assert slugs[0] == "design-alpha"
        assert slugs[1] == "design-zeta"
        assert slugs[2] == "engineering-beta"

    def test_accepts_same_name_across_divisions(self, tmp_path):
        repo = tmp_path / "repo"
        (repo / "engineering").mkdir(parents=True)
        (repo / "design").mkdir(parents=True)
        content = '---\nname: "Same Name"\ndescription: "desc"\nemoji: X\ncolor: blue\n---\n\nbody'
        (repo / "engineering" / "engineering-agent.md").write_text(content, encoding="utf-8")
        (repo / "design" / "design-agent.md").write_text(content, encoding="utf-8")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(mod, "AGENT_DIRS", ["engineering", "design"])
            agents = collect_agents(repo)
        # Slugs are derived from unique file stems, so no duplicate error
        assert len(agents) == 2
        assert agents[0]["slug"] == "design-agent"
        assert agents[1]["slug"] == "engineering-agent"

    def test_empty_dirs_returns_empty_list(self, tmp_path):
        repo = tmp_path / "repo"
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(mod, "AGENT_DIRS", ["engineering"])
            agents = collect_agents(repo)
        assert agents == []

    def test_recursive_subdirs(self, tmp_path):
        repo = tmp_path / "repo"
        blender_dir = repo / "game-development" / "blender"
        blender_dir.mkdir(parents=True)
        content = '---\nname: "Blender Artist"\ndescription: "3D artist"\nemoji: B\ncolor: teal\n---\n\nbody'
        (blender_dir / "game-dev-blender-artist.md").write_text(content, encoding="utf-8")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(mod, "AGENT_DIRS", ["game-development"])
            agents = collect_agents(repo)

        assert len(agents) == 1
        assert agents[0]["slug"] == "game-dev-blender-artist"


# ── plugin_yaml ──────────────────────────────────────────────────────────────

class TestPluginYaml:
    def test_returns_string_with_name(self):
        result = plugin_yaml()
        assert isinstance(result, str)
        assert "agency-agents-router" in result

    def test_includes_all_tools(self):
        result = plugin_yaml()
        assert "agency_agents_search" in result
        assert "agency_agents_inspect" in result
        assert "agency_agents_load" in result
        assert "agency_agents_delegate" in result

    def test_includes_version(self):
        assert "1.0.0" in plugin_yaml()


# ── init_py ──────────────────────────────────────────────────────────────────

class TestInitPy:
    def test_returns_python_source(self):
        result = init_py()
        assert isinstance(result, str)
        assert "def register(ctx):" in result

    def test_contains_all_tool_handlers(self):
        result = init_py()
        assert "def search(" in result
        assert "def read(" in result
        assert "def prompt(" in result
        assert "def delegate(" in result

    def test_contains_register_tool_calls(self):
        result = init_py()
        assert "ctx.register_tool(" in result
        assert 'name="agency_agents_search"' in result
        assert 'name="agency_agents_inspect"' in result
        assert 'name="agency_agents_load"' in result
        assert 'name="agency_agents_delegate"' in result


# ── readme ───────────────────────────────────────────────────────────────────

class TestReadme:
    def test_includes_agent_count(self):
        result = readme(42)
        assert "42" in result

    def test_includes_plugin_name(self):
        result = readme(0)
        assert "agency-agents-router" in result

    def test_includes_tool_names(self):
        result = readme(0)
        assert "agency_agents_search" in result
        assert "agency_agents_delegate" in result

    def test_zero_agents(self):
        result = readme(0)
        assert "0" in result


# ── parse_agent edge cases (line 58: skip non-key-value lines) ──────────────

class TestParseAgentEdgeCases:
    def test_skips_blank_lines_in_frontmatter(self, tmp_path):
        """Lines without ':' are skipped (covered by line 58 continue)."""
        repo = tmp_path / "repo"
        (repo / "engineering").mkdir(parents=True)
        path = repo / "engineering" / "eng-agent.md"
        path.write_text(
            "---\n"
            'name: "Test Agent"\n'
            'description: "A test"\n'
            "\n"  # blank line — no colon
            'emoji: "\U0001f680"\n'
            "color: blue\n"
            "---\n\n## Body\n",
            encoding="utf-8",
        )
        result = parse_agent(path, repo)
        assert result is not None
        assert result["name"] == "Test Agent"

    def test_skips_indented_yaml_lines(self, tmp_path):
        """Lines starting with space/tab are skipped (line 58 startswith check)."""
        repo = tmp_path / "repo"
        (repo / "engineering").mkdir(parents=True)
        path = repo / "engineering" / "eng-agent.md"
        path.write_text(
            "---\n"
            'name: "Test Agent"\n'
            'description: "A test"\n'
            "  indented_field: should_skip\n"  # starts with space
            'emoji: "\U0001f680"\n'
            "color: blue\n"
            "---\n\n## Body\n",
            encoding="utf-8",
        )
        result = parse_agent(path, repo)
        assert result is not None
        assert result["name"] == "Test Agent"
        # indented_field should NOT be in the result
        assert "indented_field" not in result


# ── build ──────────────────────────────────────────────────────────────────

class TestBuild:
    def test_creates_all_files(self, tmp_path, monkeypatch):
        """build() creates plugin dir, plugin.yaml, __init__.py, agents.json, README."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        # Mock collect_agents to return known data
        mock_agents = [
            {
                "slug": "test-agent",
                "name": "Test Agent",
                "description": "A test agent",
                "division": "engineering",
                "color": "blue",
                "emoji": "🚀",
                "vibe": "helpful",
                "source_path": "engineering/test-agent.md",
                "body": "## Identity\nYou are a test agent.\n",
            }
        ]
        monkeypatch.setattr(mod, "collect_agents", lambda _repo_root: mock_agents)

        count = mod.build(tmp_path / "repo", out_dir)
        assert count == 1

        plugin_dir = out_dir / "agency-agents-router"
        assert plugin_dir.is_dir()
        assert (plugin_dir / "plugin.yaml").exists()
        assert (plugin_dir / "__init__.py").exists()
        assert (plugin_dir / "data" / "agents.json").exists()
        assert (out_dir / "README.md").exists()

    def test_removes_existing_plugin_dir(self, tmp_path, monkeypatch):
        """build() removes an existing plugin directory before recreating."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        # Pre-create the plugin dir with a stale file
        plugin_dir = out_dir / "agency-agents-router"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "stale.txt").write_text("old", encoding="utf-8")

        monkeypatch.setattr(mod, "collect_agents", lambda _repo_root: [])

        mod.build(tmp_path / "repo", out_dir)

        # The stale file should be gone
        assert not (plugin_dir / "stale.txt").exists()

    def test_creates_readme_with_count(self, tmp_path, monkeypatch):
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        mock_agents = [
            {
                "slug": f"agent-{i}",
                "name": f"Agent {i}",
                "description": "desc",
                "division": "eng",
                "color": "blue",
                "emoji": "X",
                "vibe": "",
                "source_path": f"eng/agent-{i}.md",
                "body": "body",
            }
            for i in range(3)
        ]
        monkeypatch.setattr(mod, "collect_agents", lambda _repo_root: mock_agents)

        mod.build(tmp_path / "repo", out_dir)
        readme_content = (out_dir / "README.md").read_text(encoding="utf-8")
        assert "3" in readme_content


# ── main ───────────────────────────────────────────────────────────────────

class TestMain:
    def test_default_args(self, tmp_path, monkeypatch):
        """main() resolves default repo_root and out_dir."""
        out_dir = tmp_path / "integrations" / "hermes"
        out_dir.mkdir(parents=True)

        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        monkeypatch.setattr(
            mod, "collect_agents", lambda _repo_root: []
        )
        monkeypatch.setattr(
            "sys.argv", ["build-hermes-plugin.py", "--repo-root", str(repo_root), "--out", str(out_dir)]
        )

        result = mod.main()
        assert result == 0
        # Should have created the plugin dir structure
        assert (out_dir / "agency-agents-router").is_dir()

    def test_custom_repo_root(self, tmp_path, monkeypatch):
        """main() accepts --repo-root argument."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        repo = tmp_path / "custom-repo"
        repo.mkdir()

        monkeypatch.setattr(mod, "collect_agents", lambda _repo_root: [])
        monkeypatch.setattr(
            "sys.argv",
            ["build-hermes-plugin.py", "--repo-root", str(repo), "--out", str(out_dir)],
        )

        result = mod.main()
        assert result == 0

    def test_prints_agent_count(self, tmp_path, monkeypatch, capsys):
        """main() prints the count of built agents."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        mock_agents = [
            {
                "slug": "a",
                "name": "A",
                "description": "d",
                "division": "e",
                "color": "blue",
                "emoji": "X",
                "vibe": "",
                "source_path": "e/a.md",
                "body": "b",
            }
            for _ in range(5)
        ]
        monkeypatch.setattr(mod, "collect_agents", lambda _repo_root: mock_agents)
        monkeypatch.setattr(
            "sys.argv",
            [
                "build-hermes-plugin.py",
                "--repo-root", str(tmp_path / "repo"),
                "--out", str(out_dir),
            ],
        )

        mod.main()
        captured = capsys.readouterr()
        assert "5" in captured.out
