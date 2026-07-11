"""Tests for scripts/batch-date-added.py — bulk date_added insertion."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "batch_date_added", str(SCRIPTS_DIR / "batch-date-added.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

is_agent = mod.is_agent
discover_files = mod.discover_files
has_date_added = mod.has_date_added
insert_date_added = mod.insert_date_added


class TestIsAgent:
    def test_agent_file(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("---\nname: A\n---\nBody", encoding="utf-8")
        assert is_agent(f) is True

    def test_not_agent(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("plain text", encoding="utf-8")
        assert is_agent(f) is False


class TestHasDateAdded:
    def test_has_field(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("---\nname: A\ndate_added: \"2026-01-01\"\n---\nBody", encoding="utf-8")
        assert has_date_added(f) is True

    def test_no_field(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("---\nname: A\n---\nBody", encoding="utf-8")
        assert has_date_added(f) is False


class TestInsertDateAdded:
    def test_inserts_after_version(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("---\nname: A\nversion: \"1.0.0\"\ncolor: blue\n---\nBody", encoding="utf-8")
        assert insert_date_added(f, "2026-07-01") is True
        content = f.read_text(encoding="utf-8")
        lines = content.split("\n")
        date_idx = next(i for i, l in enumerate(lines) if l.startswith("date_added:"))
        assert lines[date_idx - 1].startswith("version:")

    def test_inserts_after_color_fallback(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("---\nname: A\ncolor: blue\n---\nBody", encoding="utf-8")
        assert insert_date_added(f, "2026-07-01") is True
        content = f.read_text(encoding="utf-8")
        lines = content.split("\n")
        date_idx = next(i for i, l in enumerate(lines) if l.startswith("date_added:"))
        assert lines[date_idx - 1].startswith("color:")

    def test_no_anchor_returns_false(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("---\nname: A\n---\nBody", encoding="utf-8")
        assert insert_date_added(f, "2026-07-01") is False


class TestDiscoverFiles:
    def test_skips_dot_dirs(self, tmp_path, monkeypatch):
        (tmp_path / ".dotdir").mkdir()
        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "NON_AGENT_DIRS", frozenset())
        files = discover_files()
        assert files == []

    def test_skips_non_agent_dirs(self, tmp_path, monkeypatch):
        (tmp_path / "scripts").mkdir()
        monkeypatch.setattr(mod, "REPO", tmp_path)
        files = discover_files()
        assert files == []

    def test_category_mismatch(self, tmp_path, monkeypatch):
        d = tmp_path / "eng"
        d.mkdir()
        (d / "agent.md").write_text("---\nname: A\n---\nBody", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "NON_AGENT_DIRS", frozenset())
        files = discover_files(category="other")
        assert files == []


    def test_is_agent_oserror(self, tmp_path, monkeypatch):
        f = tmp_path / "a.md"
        f.write_text("---\nname: A\n---\nBody", encoding="utf-8")

        def _fail(path_self, *args, **kwargs):
            raise OSError
        monkeypatch.setattr(mod.Path, "read_text", _fail)
        assert is_agent(f) is False


class TestMainFunction:
    def test_file_not_found(self, monkeypatch, capsys):
        with patch.object(sys, "argv",
                          ["batch-date-added.py", "--file", "/nonexistent.md"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1

    def test_dry_run(self, tmp_path, monkeypatch, capsys):
        d = tmp_path / "engineering"
        d.mkdir()
        f = d / "agent.md"
        f.write_text("---\nname: A\nversion: \"1.0.0\"\ncolor: blue\n---\nBody", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "NON_AGENT_DIRS", frozenset())

        def _fake_run(*args, **kwargs):
            class R:
                stdout = "2026-01-15"
            return R()
        monkeypatch.setattr(mod.subprocess, "run", _fake_run)

        with patch.object(sys, "argv", ["batch-date-added.py", "--dry-run"]):
            mod.main()
        out = capsys.readouterr().out
        assert "DRY-RUN" in out
        assert "date_added:" not in f.read_text(encoding="utf-8")

    def test_file_mode_has_date_added(self, tmp_path, monkeypatch, capsys):
        """--file with agent that already has date_added — skipped."""
        f = tmp_path / "agent.md"
        f.write_text("---\nname: A\ndate_added: \"2026-01-01\"\nversion: \"1.0.0\"\ncolor: blue\n---\nBody", encoding="utf-8")
        with patch.object(sys, "argv",
                          ["batch-date-added.py", "--file", str(f)]):
            mod.main()
        assert "Skipped: 1" in capsys.readouterr().out

    def test_no_commit_date(self, tmp_path, monkeypatch, capsys):
        """Git returns no commit date — skipped."""
        d = tmp_path / "engineering"
        d.mkdir()
        f = d / "agent.md"
        f.write_text("---\nname: A\nversion: \"1.0.0\"\ncolor: blue\n---\nBody", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "NON_AGENT_DIRS", frozenset())

        def _empty_git(*args, **kwargs):
            class R:
                stdout = ""
            return R()
        monkeypatch.setattr(mod.subprocess, "run", _empty_git)

        with patch.object(sys, "argv", ["batch-date-added.py"]):
            mod.main()
        assert "Skipped: 1" in capsys.readouterr().out

    def test_actual_insert(self, tmp_path, monkeypatch, capsys):
        """Full flow: discover agent, get git date, insert field."""
        d = tmp_path / "engineering"
        d.mkdir()
        f = d / "agent.md"
        f.write_text("---\nname: A\nversion: \"1.0.0\"\ncolor: blue\n---\nBody", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "NON_AGENT_DIRS", frozenset())

        def _date_git(*args, **kwargs):
            class R:
                stdout = "2026-01-15"
            return R()
        monkeypatch.setattr(mod.subprocess, "run", _date_git)

        with patch.object(sys, "argv", ["batch-date-added.py"]):
            mod.main()
        content = f.read_text(encoding="utf-8")
        assert 'date_added: "2026-01-15"' in content
