"""Tests for scripts/install.py — install/uninstall/verify scope and safety."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _load_mod():
    spec = importlib.util.spec_from_file_location(
        "install", str(SCRIPTS_DIR / "install.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def env(tmp_path, monkeypatch):
    mod = _load_mod()
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(mod, "REPO", repo)
    monkeypatch.setattr(mod, "INDEX_PATH", repo / "AGENTS.json")
    monkeypatch.setattr(mod, "TOOLS_PATH", repo / "tools.json")
    return mod, repo


def _write_index(repo, agents):
    (repo / "AGENTS.json").write_text(
        json.dumps({"agents": agents}), encoding="utf-8"
    )


def _agent(aid="one", name="One", category="engineering"):
    return {
        "id": aid,
        "name": name,
        "path": f"{category}/{aid}.md",
        "category": category,
    }


def _write_source(repo, agent):
    path = repo / agent["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\nname: x\n---\n", encoding="utf-8")


class TestSlugAndValidation:
    def test_agent_slug_applies_prefix(self, env):
        mod, _repo = env
        assert mod._agent_slug(
            {"id": "one", "name": "One"},
            {"slugFrom": "source", "slugPrefix": "agency-"},
        ) == "agency-one"
        assert mod._agent_slug(
            {"id": "x", "name": "My Agent"},
            {"slugFrom": "name", "slugPrefix": ""},
        ) == "my-agent"

    @pytest.mark.parametrize("agent", [
        {"id": "../evil", "path": "engineering/a.md"},
        {"id": "evil", "path": "../a.md"},
        {"id": "evil", "path": "/a.md"},
        {"id": "evil", "path": "engineering/a\\b.md"},
        {"id": "evil", "path": "engineering/a.txt"},
        {"id": "Evil", "path": "engineering/a.md"},
    ])
    def test_validate_rejects_unsafe_entries(self, env, agent):
        mod, _repo = env
        with pytest.raises(ValueError):
            mod._validate_agent_entry(agent)

    def test_validate_accepts_solution_id(self, env):
        mod, repo = env
        agent = _agent("_solution-one")
        _write_source(repo, agent)
        source = mod._validate_agent_entry(agent)
        assert source.exists()

    def test_safe_dest_rejects_traversal(self, env):
        mod, repo = env
        with pytest.raises(ValueError):
            mod._safe_dest(repo / "dest", "{slug}.md", "../evil")

    def test_safe_dest_keeps_final_symlink_but_not_dir_symlink(
            self, env, tmp_path):
        mod, _repo = env
        base = tmp_path / "base"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        final = base / "one.md"
        try:
            final.symlink_to(outside / "x.md")
            (base / "linkdir").symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("symlinks not supported")
        assert mod._safe_dest(base, "{slug}.md", "one") == final
        with pytest.raises(ValueError):
            mod._safe_dest(base, "{slug}/SKILL.md", "linkdir")


class TestInstall:
    def test_install_agent_applies_prefix(self, env):
        mod, repo = env
        agent = _agent("one")
        _write_source(repo, agent)
        integ = repo / "integrations" / "antigravity" / "agency-one"
        integ.mkdir(parents=True)
        (integ / "SKILL.md").write_text("converted-body", encoding="utf-8")

        cfg = {
            "kebab": "antigravity",
            "format": "skill-md",
            "slugFrom": "source",
            "slugPrefix": "agency-",
        }
        dest_dir = repo / "home" / "skills"
        n = mod.install_agent(
            agent,
            cfg,
            [(dest_dir, "{slug}/SKILL.md")],
            source_index=mod._build_source_index(
                repo / "integrations" / "antigravity"
            ),
        )
        assert n == 1
        assert (dest_dir / "agency-one" / "SKILL.md").read_text(
            encoding="utf-8"
        ) == "converted-body"

    def test_install_roster_copies_once(self, env, monkeypatch):
        mod, repo = env
        (repo / "integrations" / "aider").mkdir(parents=True)
        (repo / "integrations" / "aider" / "CONVENTIONS.md").write_text(
            "rules", encoding="utf-8"
        )
        _write_index(repo, [_agent("one"), _agent("two")])
        cfg = {
            "kebab": "aider",
            "format": "aider-conventions",
            "installKind": "roster",
            "slugFrom": None,
            "scope": {"user": False, "project": True},
        }
        monkeypatch.setattr(mod, "get_tool_cfg", lambda _tool: cfg)
        dest = repo / "project"
        dest.mkdir()
        monkeypatch.setattr(
            mod, "resolve_dest", lambda _tool, _scope: [(dest, "CONVENTIONS.md")]
        )
        calls = []
        original = mod._atomic_copy

        def counting_copy(src, dst):
            calls.append((src, dst))
            original(src, dst)

        monkeypatch.setattr(mod, "_atomic_copy", counting_copy)
        n = mod.install_tool("aider", None, None, scope="project")
        assert n == 1
        assert len(calls) == 1
        assert (dest / "CONVENTIONS.md").read_text(encoding="utf-8") == "rules"

    def test_find_source_in_subdirectory(self, env):
        mod, repo = env
        integ = repo / "integrations" / "gemini-cli"
        (integ / "agents").mkdir(parents=True)
        (integ / "agents" / "one.md").write_text("x", encoding="utf-8")
        index = mod._build_source_index(integ)
        found = mod._find_source(integ, "one", "{slug}.md", index)
        assert found == integ / "agents" / "one.md"


class TestUninstall:
    def test_uninstall_all_preserves_unknown_files(self, env, monkeypatch):
        mod, repo = env
        dest = repo / "agents"
        dest.mkdir()
        (dest / "one.md").write_text("installed", encoding="utf-8")
        (dest / "my-custom.md").write_text("mine", encoding="utf-8")
        _write_index(repo, [_agent("one")])
        cfg = {"installKind": "per-agent", "slugFrom": "source",
               "scope": {"user": True}}
        monkeypatch.setattr(mod, "get_tool_cfg", lambda _tool: cfg)
        monkeypatch.setattr(
            mod, "resolve_dest", lambda _tool, _scope: [(dest, "{slug}.md")]
        )
        removed = mod.uninstall_tool("claude-code", None, scope="user")
        assert removed == 1
        assert not (dest / "one.md").exists()
        assert (dest / "my-custom.md").exists()

    def test_uninstall_removes_only_owned_prefixed_dirs(self, env, monkeypatch):
        mod, repo = env
        dest = repo / "skills"
        (dest / "agency-one").mkdir(parents=True)
        (dest / "agency-one" / "SKILL.md").write_text("x", encoding="utf-8")
        (dest / "my-custom").mkdir()
        (dest / "my-custom" / "SKILL.md").write_text("mine", encoding="utf-8")
        _write_index(repo, [_agent("one")])
        cfg = {
            "installKind": "per-agent",
            "slugFrom": "source",
            "slugPrefix": "agency-",
            "scope": {"user": True},
        }
        monkeypatch.setattr(mod, "get_tool_cfg", lambda _tool: cfg)
        monkeypatch.setattr(
            mod, "resolve_dest", lambda _tool, _scope: [(dest, "{slug}/SKILL.md")]
        )
        removed = mod.uninstall_tool("osaurus", None, scope="user")
        assert removed == 1
        assert not (dest / "agency-one").exists()
        assert (dest / "my-custom" / "SKILL.md").exists()

    def test_uninstall_unknown_agent_preserves_user_file(self, env, monkeypatch):
        mod, repo = env
        dest = repo / "agents"
        dest.mkdir()
        (dest / "agency-one.md").write_text("user-file", encoding="utf-8")
        _write_index(repo, [_agent("other")])
        cfg = {"installKind": "per-agent", "slugFrom": "source",
               "scope": {"user": True}}
        monkeypatch.setattr(mod, "get_tool_cfg", lambda _tool: cfg)
        monkeypatch.setattr(
            mod, "resolve_dest", lambda _tool, _scope: [(dest, "{slug}.md")]
        )
        removed = mod.uninstall_tool("claude-code", "agency-one", scope="user")
        assert removed == -1
        assert (dest / "agency-one.md").exists()


class TestVerifyAndList:
    def test_verify_ignores_user_files_and_dotfiles(self, env, monkeypatch):
        mod, repo = env
        dest = repo / "agents"
        dest.mkdir()
        (dest / "one.md").write_text("x", encoding="utf-8")
        (dest / ".feedback.jsonl").write_text("{}\n", encoding="utf-8")
        (dest / "user.md").write_text("mine", encoding="utf-8")
        _write_index(repo, [_agent("one")])
        cfg = {"installKind": "per-agent", "slugFrom": "source",
               "scope": {"user": True}}
        monkeypatch.setattr(mod, "get_tool_cfg", lambda _tool: cfg)
        monkeypatch.setattr(
            mod, "resolve_dest", lambda _tool, _scope: [(dest, "{slug}.md")]
        )
        assert mod.verify_install("claude-code", scope="user") is True

    def test_verify_subset_agent(self, env, monkeypatch):
        mod, repo = env
        dest = repo / "agents"
        dest.mkdir()
        (dest / "one.md").write_text("x", encoding="utf-8")
        _write_index(repo, [_agent("one"), _agent("two")])
        cfg = {"installKind": "per-agent", "slugFrom": "source",
               "scope": {"user": True}}
        monkeypatch.setattr(mod, "get_tool_cfg", lambda _tool: cfg)
        monkeypatch.setattr(
            mod, "resolve_dest", lambda _tool, _scope: [(dest, "{slug}.md")]
        )
        assert mod.verify_install("claude-code", agent_id="one", scope="user") is True
        assert mod.verify_install("claude-code", scope="user") is False

    def test_list_installed_counts_owned_only(self, env, monkeypatch):
        mod, repo = env
        dest = repo / "agents"
        dest.mkdir()
        (dest / "one.md").write_text("x", encoding="utf-8")
        (dest / "user.md").write_text("mine", encoding="utf-8")
        _write_index(repo, [_agent("one")])
        cfg = {"installKind": "per-agent", "slugFrom": "source",
               "scope": {"user": True}}
        monkeypatch.setattr(mod, "get_tool_cfg", lambda _tool: cfg)
        monkeypatch.setattr(
            mod, "resolve_dest", lambda _tool, _scope: [(dest, "{slug}.md")]
        )
        assert mod.list_installed("claude-code", scope="user") == 1

    def test_symlinked_agent_lists_verifies_and_unlinks(self, env, monkeypatch):
        mod, repo = env
        dest = repo / "agents"
        dest.mkdir()
        target = repo / "source.md"
        target.write_text("x", encoding="utf-8")
        link = dest / "one.md"
        try:
            link.symlink_to(target)
        except OSError:
            pytest.skip("symlinks not supported")
        _write_index(repo, [_agent("one")])
        cfg = {"installKind": "per-agent", "slugFrom": "source",
               "scope": {"user": True}}
        monkeypatch.setattr(mod, "get_tool_cfg", lambda _tool: cfg)
        monkeypatch.setattr(
            mod, "resolve_dest", lambda _tool, _scope: [(dest, "{slug}.md")]
        )
        assert mod.list_installed("claude-code", scope="user") == 1
        assert mod.verify_install("claude-code", scope="user") is True
        assert mod.uninstall_tool("claude-code", None, scope="user") == 1
        assert not link.is_symlink()
        assert target.exists()


class TestRosterOwnership:
    def _cfg(self):
        return {
            "installKind": "roster",
            "slugFrom": None,
            "scope": {"user": False, "project": True},
        }

    def test_uninstall_roster_refuses_user_authored_file(
            self, env, monkeypatch, capsys):
        mod, repo = env
        _write_index(repo, [_agent("one")])
        dest = repo / "project"
        dest.mkdir()
        roster = dest / "CONVENTIONS.md"
        roster.write_text("# my own rules\n", encoding="utf-8")
        monkeypatch.setattr(mod, "get_tool_cfg", lambda _tool: self._cfg())
        monkeypatch.setattr(
            mod, "resolve_dest",
            lambda _tool, _scope: [(dest, "CONVENTIONS.md")],
        )
        assert mod.uninstall_tool("aider", None, scope="project") == 0
        assert roster.exists()
        assert "refusing" in capsys.readouterr().err

    def test_uninstall_roster_removes_generated_file(self, env, monkeypatch):
        mod, repo = env
        _write_index(repo, [_agent("one")])
        dest = repo / "project"
        dest.mkdir()
        roster = dest / "CONVENTIONS.md"
        roster.write_text(
            "# The Agency\n# Generated by scripts/convert.py — do not edit manually.\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "get_tool_cfg", lambda _tool: self._cfg())
        monkeypatch.setattr(
            mod, "resolve_dest",
            lambda _tool, _scope: [(dest, "CONVENTIONS.md")],
        )
        assert mod.uninstall_tool("aider", None, scope="project") == 1
        assert not roster.exists()


class TestPluginTools:
    def test_plugin_present_user_scope(self, env, tmp_path, monkeypatch):
        mod, _repo = env
        home = tmp_path / "home"
        plugin = home / ".hermes" / "plugins" / "agency-agents-router"
        plugin.mkdir(parents=True)
        (plugin / "plugin.yaml").write_text("name: agency\n", encoding="utf-8")
        monkeypatch.setattr(mod.Path, "home", classmethod(lambda cls: home))
        assert mod._plugin_present(
            {"dest": {"user": [".hermes/plugins/agency-agents-router"]}}, "user"
        ) is True
        assert mod._plugin_present(
            {"dest": {"user": [".hermes/plugins/other"]}}, "user"
        ) is False

    def test_plugin_present_glob_template(self, env, tmp_path, monkeypatch):
        mod, _repo = env
        monkeypatch.chdir(tmp_path)
        skill = tmp_path / ".claude" / "skills" / "nexus-architect"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("x", encoding="utf-8")
        assert mod._plugin_present(
            {"dest": {"project": [".claude/skills/nexus-*/SKILL.md"]}}, "project"
        ) is True
        assert mod._plugin_present(
            {"dest": {"project": [".claude/skills/none-*/SKILL.md"]}}, "project"
        ) is False

    def test_list_and_verify_plugin(self, env, tmp_path, monkeypatch):
        mod, _repo = env
        home = tmp_path / "home"
        plugin = home / ".hermes" / "plugins" / "agency-agents-router"
        cfg = {
            "installKind": "plugin",
            "scope": {"user": True},
            "dest": {"user": [".hermes/plugins/agency-agents-router"]},
        }
        monkeypatch.setattr(mod, "get_tool_cfg", lambda _tool: cfg)
        monkeypatch.setattr(
            mod, "resolve_dest",
            lambda _tool, _scope: [(home / ".hermes" / "plugins",
                                    "agency-agents-router")],
        )
        monkeypatch.setattr(mod.Path, "home", classmethod(lambda cls: home))
        assert mod.list_installed("hermes", scope="user") == 0
        assert mod.verify_install("hermes", scope="user") is False
        plugin.mkdir(parents=True)
        (plugin / "plugin.yaml").write_text("x", encoding="utf-8")
        assert mod.list_installed("hermes", scope="user") == 1
        assert mod.verify_install("hermes", scope="user") is True

    def test_plugin_install_exits_zero(self, env, monkeypatch):
        mod, _repo = env
        monkeypatch.setattr(sys, "argv", ["install.py", "--tool", "hermes"])
        monkeypatch.setattr(
            mod, "get_tool_cfg", lambda _tool: {"installKind": "plugin"}
        )
        monkeypatch.setattr(mod, "install_tool", lambda *a, **k: 0)
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 0


def test_remote_installer_accepts_solution_ids():
    spec = importlib.util.spec_from_file_location(
        "install_remote", str(SCRIPTS_DIR / "install-remote.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.is_safe_agent_id("_solution-one")
    assert not mod.is_safe_agent_id("../evil")
