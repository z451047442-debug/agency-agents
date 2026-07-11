"""Tests for scripts/batch-version.py — bulk version insertion."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "batch_version", str(SCRIPTS_DIR / "batch-version.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

is_agent = mod.is_agent
discover_files = mod.discover_files
has_field = mod.has_field
insert_version = mod.insert_version


class TestIsAgent:
    def test_agent(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("---\nname: A\n---\nBody", encoding="utf-8")
        assert is_agent(f) is True

    def test_not_agent(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("plain", encoding="utf-8")
        assert is_agent(f) is False


class TestHasField:
    def test_has_version(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text('---\nname: A\nversion: "1.0.0"\ncolor: blue\n---\nBody', encoding="utf-8")
        assert has_field(f, "version") is True

    def test_no_version(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("---\nname: A\ncolor: blue\n---\nBody", encoding="utf-8")
        assert has_field(f, "version") is False


class TestInsertVersion:
    def test_inserts_after_color(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("---\nname: A\ncolor: blue\n---\nBody", encoding="utf-8")
        insert_version(f)
        content = f.read_text(encoding="utf-8")
        assert 'version: "1.0.0"' in content
        lines = content.split("\n")
        ver_idx = next(i for i, l in enumerate(lines) if l.startswith("version:"))
        assert lines[ver_idx - 1].startswith("color:")


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
                          ["batch-version.py", "--file", "/nonexistent.md"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1

    def test_dry_run(self, tmp_path, monkeypatch, capsys):
        d = tmp_path / "engineering"
        d.mkdir()
        f = d / "agent.md"
        f.write_text("---\nname: A\ncolor: blue\n---\nBody", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "NON_AGENT_DIRS", frozenset())

        with patch.object(sys, "argv", ["batch-version.py", "--dry-run"]):
            mod.main()
        out = capsys.readouterr().out
        assert "Run without --dry-run" in out
        assert 'version:' not in f.read_text(encoding="utf-8")

    def test_no_agent_files(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "NON_AGENT_DIRS", frozenset())
        with patch.object(sys, "argv", ["batch-version.py"]):
            mod.main()
        assert "No agent files found" in capsys.readouterr().out

    def test_category_errors(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv",
                          ["batch-version.py", "--category", "nonexistent"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1

    def test_actual_insert(self, tmp_path, monkeypatch, capsys):
        d = tmp_path / "eng"
        d.mkdir()
        f = d / "agent.md"
        f.write_text("---\nname: A\ncolor: blue\n---\nBody", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "NON_AGENT_DIRS", frozenset())
        with patch.object(sys, "argv", ["batch-version.py"]):
            mod.main()
        assert 'version: "1.0.0"' in f.read_text(encoding="utf-8")
        assert "files updated" in capsys.readouterr().out

    def test_agent_already_has_version(self, tmp_path, monkeypatch, capsys):
        d = tmp_path / "eng"
        d.mkdir()
        f = d / "agent.md"
        f.write_text('---\nname: A\nversion: "2.0.0"\ncolor: blue\n---\nBody', encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "NON_AGENT_DIRS", frozenset())
        with patch.object(sys, "argv", ["batch-version.py"]):
            mod.main()
        assert "already have version" in capsys.readouterr().out

    def test_agent_missing_color(self, tmp_path, monkeypatch, capsys):
        d = tmp_path / "eng"
        d.mkdir()
        f = d / "agent.md"
        f.write_text("---\nname: A\n---\nBody", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "NON_AGENT_DIRS", frozenset())
        with patch.object(sys, "argv", ["batch-version.py"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1
        assert "no color:" in capsys.readouterr().out

    def test_category_mode_valid(self, tmp_path, monkeypatch, capsys):
        d = tmp_path / "eng"
        d.mkdir()
        f = d / "agent.md"
        f.write_text("---\nname: A\ncolor: blue\n---\nBody", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv",
                          ["batch-version.py", "--category", "eng"]):
            mod.main()
        assert "files updated" in capsys.readouterr().out

    def test_file_mode(self, tmp_path, monkeypatch, capsys):
        f = tmp_path / "agent.md"
        f.write_text("---\nname: A\ncolor: blue\n---\nBody", encoding="utf-8")
        with patch.object(sys, "argv",
                          ["batch-version.py", "--file", str(f)]):
            mod.main()
        assert 'version: "1.0.0"' in f.read_text(encoding="utf-8")

    def test_non_agent_file_in_loop(self, tmp_path, monkeypatch, capsys):
        """File without frontmatter via --file triggers error."""
        f = tmp_path / "bad.md"
        f.write_text("no frontmatter", encoding="utf-8")
        with patch.object(sys, "argv",
                          ["batch-version.py", "--file", str(f)]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1
        assert "missing frontmatter" in capsys.readouterr().out

    def test_insert_version_oserror(self, tmp_path, monkeypatch, capsys):
        """OSError during write triggers error path."""
        d = tmp_path / "eng"
        d.mkdir()
        f = d / "agent.md"
        f.write_text("---\nname: A\ncolor: blue\n---\nBody", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "NON_AGENT_DIRS", frozenset())

        def _fail(path_self, *args, **kwargs):
            raise OSError
        monkeypatch.setattr(mod.Path, "write_text", _fail)

        with patch.object(sys, "argv", ["batch-version.py"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1
        assert "write failed" in capsys.readouterr().out
