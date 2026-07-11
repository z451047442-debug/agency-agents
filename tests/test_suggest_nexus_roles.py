"""Tests for scripts/suggest-nexus-roles.py — NEXUS role suggestion."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "suggest_nexus_roles", str(SCRIPTS_DIR / "suggest-nexus-roles.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

is_agent_file = mod.is_agent_file
get_body = mod.get_body
count_keywords = mod.count_keywords
analyze_agent = mod.analyze_agent
discover_agents = mod.discover_agents


class TestIsAgentFile:
    def test_agent_file(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("---\nname: A\n---\nBody", encoding="utf-8")
        assert is_agent_file(f) is True

    def test_non_agent(self, tmp_path):
        f = tmp_path / "readme.md"
        f.write_text("# README", encoding="utf-8")
        assert is_agent_file(f) is False

    def test_missing_file(self, tmp_path):
        assert is_agent_file(tmp_path / "nope.md") is False


class TestGetBody:
    def test_extracts_body_after_frontmatter(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("---\nname: A\n---\n\nActual body content.", encoding="utf-8")
        assert "Actual body content" in get_body(f)

    def test_no_frontmatter_returns_whole_text(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("Just plain text.", encoding="utf-8")
        assert get_body(f) == "Just plain text."


class TestCountKeywords:
    def test_matches_single_keywords(self):
        assert count_keywords("testing code review linting",
                              ["testing", "code review", "linting"]) == 3

    def test_matches_multi_word_phrase(self):
        assert count_keywords("continuous improvement is key",
                              ["continuous improvement"]) == 1

    def test_no_matches(self):
        assert count_keywords("unrelated text", ["ci/cd", "testing"]) == 0


class TestAnalyzeAgent:
    def test_returns_matching_phases(self, tmp_path):
        f = tmp_path / "agent.md"
        f.write_text(
            "---\nname: Tester\n---\n"
            "I handle testing and qa with code review and linting. "
            "I also manage deployment and launch.",
            encoding="utf-8",
        )
        matches = analyze_agent(f, min_confidence=2)
        phases = {m[0] for m in matches}
        assert "phase-4-hardening" in phases

    def test_respects_min_confidence(self, tmp_path):
        f = tmp_path / "agent.md"
        f.write_text("---\nname: Dev\n---\nI do testing and code review.", encoding="utf-8")
        matches = analyze_agent(f, min_confidence=5)
        assert len(matches) == 0

    def test_no_matches(self, tmp_path):
        f = tmp_path / "agent.md"
        f.write_text(
            "---\nname: Odd\n---\n"
            "I do uniquely specialized things that dont match any phase keywords.",
            encoding="utf-8",
        )
        matches = analyze_agent(f, min_confidence=2)
        assert len(matches) == 0


class TestDiscoverAgents:
    def test_discovers_in_category(self, tmp_path, monkeypatch):
        d = tmp_path / "engineering"
        d.mkdir()
        f = d / "agent.md"
        f.write_text("---\nname: A\n---\nBody", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        agents = discover_agents("engineering")
        assert len(agents) == 1

    def test_skips_dot_dirs(self, tmp_path, monkeypatch):
        (tmp_path / ".dotdir").mkdir()
        (tmp_path / "engineering").mkdir()
        f = tmp_path / "engineering" / "agent.md"
        f.write_text("---\nname: A\n---\nBody", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        agents = discover_agents()
        assert len(agents) == 1

    def test_category_filter_mismatch(self, tmp_path, monkeypatch):
        (tmp_path / "engineering").mkdir()
        f = tmp_path / "engineering" / "agent.md"
        f.write_text("---\nname: A\n---\nBody", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        agents = discover_agents("science")
        assert len(agents) == 0

    def test_skips_non_agent_dirs(self, tmp_path, monkeypatch):
        (tmp_path / "scripts").mkdir()
        (tmp_path / "engineering").mkdir()
        f = tmp_path / "engineering" / "agent.md"
        f.write_text("---\nname: A\n---\nBody", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        agents = discover_agents()
        assert len(agents) == 1


class TestMainFunction:
    def test_file_flag(self, tmp_path, monkeypatch, capsys):
        f = tmp_path / "agent.md"
        f.write_text(
            "---\nname: Dev\n---\n"
            "I do testing, qa, code review and linting for the team.",
            encoding="utf-8",
        )
        with patch.object(sys, "argv", ["suggest-nexus-roles.py", "--file", str(f)]):
            mod.main()
        out = capsys.readouterr().out
        assert "agent" in out

    def test_file_not_found(self, monkeypatch, capsys):
        with patch.object(sys, "argv",
                          ["suggest-nexus-roles.py", "--file", "/nonexistent/file.md"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1

    def test_category_flag_empty(self, tmp_path, monkeypatch, capsys):
        d = tmp_path / "engineering"
        d.mkdir()
        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv",
                          ["suggest-nexus-roles.py", "--category", "engineering"]):
            mod.main()
        assert "Analyzed:" in capsys.readouterr().out

    def test_no_flags_discovers_all(self, tmp_path, monkeypatch, capsys):
        d = tmp_path / "engineering"
        d.mkdir()
        f = d / "agent.md"
        f.write_text(
            "---\nname: A\n---\nI do testing and qa for deployment and launch.",
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["suggest-nexus-roles.py"]):
            mod.main()
        out = capsys.readouterr().out
        assert "agent" in out

    def test_skips_non_agent_in_discovered(self, tmp_path, monkeypatch, capsys):
        d = tmp_path / "engineering"
        d.mkdir()
        (d / "README.md").write_text("not an agent", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv",
                          ["suggest-nexus-roles.py", "--category", "engineering"]):
            mod.main()
        assert "Analyzed: 0" in capsys.readouterr().out

    def test_file_flag_non_agent(self, tmp_path, capsys):
        f = tmp_path / "notes.md"
        f.write_text("not an agent file", encoding="utf-8")
        with patch.object(sys, "argv", ["suggest-nexus-roles.py", "--file", str(f)]):
            mod.main()
        assert "Analyzed: 0" in capsys.readouterr().out
