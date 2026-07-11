"""Tests for scripts/clean.py — cleanup generated and temporary files."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "clean", str(SCRIPTS_DIR / "clean.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

format_bytes = mod.format_bytes
count_size = mod.count_size
collect_integration_paths = mod.collect_integration_paths
collect_deep_paths = mod.collect_deep_paths


class TestFormatBytes:
    def test_bytes(self):
        assert format_bytes(500) == "500B"

    def test_kb(self):
        assert "KB" in format_bytes(2048)

    def test_mb(self):
        assert "MB" in format_bytes(5 * 1048576)

    def test_gb(self):
        assert "GB" in format_bytes(2 * 1073741824)


class TestCountSize:
    def test_file(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("hello", encoding="utf-8")
        fc, sz = count_size(f)
        assert fc == 1
        assert sz == 5

    def test_directory(self, tmp_path):
        (tmp_path / "a.txt").write_text("a", encoding="utf-8")
        (tmp_path / "b.txt").write_text("bb", encoding="utf-8")
        fc, sz = count_size(tmp_path)
        assert fc == 2
        assert sz == 3

    def test_nonexistent(self, tmp_path):
        fc, sz = count_size(tmp_path / "nope")
        assert fc == 0
        assert sz == 0

    def test_file_stat_oserror(self, tmp_path, monkeypatch):
        f = tmp_path / "x.txt"
        f.write_text("hello", encoding="utf-8")

        # is_file() must succeed but stat must fail
        def _bad_stat(*args, **kwargs):
            raise OSError
        monkeypatch.setattr(mod.Path, "is_file", lambda self: True)
        monkeypatch.setattr(mod.Path, "stat", _bad_stat)
        fc, sz = count_size(f)
        assert fc == 0
        assert sz == 0

    def test_dir_rglob_stat_oserror(self, tmp_path, monkeypatch):
        f = tmp_path / "x.txt"
        f.write_text("hello", encoding="utf-8")

        class _BadFile:
            @staticmethod
            def is_file():
                return True
            @staticmethod
            def stat():
                raise OSError

        def _bad_rglob(path_self, pattern):
            return [_BadFile()]
        monkeypatch.setattr(mod.Path, "rglob", _bad_rglob)
        fc, sz = count_size(tmp_path)
        assert fc == 0


class TestCollectIntegrationPaths:
    def test_empty_integrations(self, tmp_path, monkeypatch):
        (tmp_path / "integrations").mkdir()
        monkeypatch.setattr(mod, "REPO", tmp_path)
        paths = collect_integration_paths()
        assert paths == []

    def test_collects_glob_dirs(self, tmp_path, monkeypatch):
        base = tmp_path / "integrations"
        base.mkdir()
        ag = base / "antigravity"
        ag.mkdir()
        (ag / "agency-myagent").mkdir()
        monkeypatch.setattr(mod, "REPO", tmp_path)
        paths = collect_integration_paths()
        assert len(paths) >= 1

    def test_collects_subdirs(self, tmp_path, monkeypatch):
        base = tmp_path / "integrations"
        base.mkdir()
        kimi = base / "kimi"
        kimi.mkdir()
        (kimi / "sub1").mkdir()
        monkeypatch.setattr(mod, "REPO", tmp_path)
        paths = collect_integration_paths()
        kimi_dirs = [p for p in paths if p.parent.name == "kimi"]
        assert len(kimi_dirs) == 1

    def test_collects_existing_file(self, tmp_path, monkeypatch):
        base = tmp_path / "integrations"
        base.mkdir()
        (base / "aider").mkdir()
        f = base / "aider" / "CONVENTIONS.md"
        f.write_text("content", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        paths = collect_integration_paths()
        assert len(paths) == 1

    def test_collects_dir_contents_except_readme(self, tmp_path, monkeypatch):
        base = tmp_path / "integrations"
        base.mkdir()
        oc = base / "openclaw"
        oc.mkdir()
        (oc / "README.md").write_text("keep", encoding="utf-8")
        (oc / "data").mkdir()
        monkeypatch.setattr(mod, "REPO", tmp_path)
        paths = collect_integration_paths()
        names = {p.name for p in paths if "openclaw" in str(p)}
        assert "data" in names
        assert "README.md" not in names

    def test_collects_existing_dirs(self, tmp_path, monkeypatch):
        base = tmp_path / "integrations"
        base.mkdir()
        (base / "cursor" / "rules").mkdir(parents=True)
        (base / "opencode" / "agents").mkdir(parents=True)
        monkeypatch.setattr(mod, "REPO", tmp_path)
        paths = collect_integration_paths()
        assert len(paths) == 2


class TestCollectDeepPaths:
    def test_collects_pycache(self, tmp_path, monkeypatch):
        d = tmp_path / "__pycache__"
        d.mkdir()
        monkeypatch.setattr(mod, "REPO", tmp_path)
        paths = collect_deep_paths()
        assert len(paths) >= 1

    def test_collects_ds_store(self, tmp_path, monkeypatch):
        f = tmp_path / ".DS_Store"
        f.write_text("", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        paths = collect_deep_paths()
        ds = [p for p in paths if p.name == ".DS_Store"]
        assert len(ds) == 1

    def test_collects_tmp_files(self, tmp_path, monkeypatch):
        f = tmp_path / "test.tmp"
        f.write_text("", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        paths = collect_deep_paths()
        assert len([p for p in paths if p.suffix == ".tmp"]) == 1

    def test_skips_env_and_git(self, tmp_path, monkeypatch):
        (tmp_path / "env").mkdir()
        (tmp_path / "env" / "__pycache__").mkdir()
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / ".DS_Store").write_text("", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        paths = collect_deep_paths()
        assert all("env" not in p.parts for p in paths)
        assert all(".git" not in p.parts for p in paths)


class TestMainFunction:
    def test_nothing_to_clean(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "integrations").mkdir()
        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["clean.py"]):
            mod.main()
        assert "Nothing to clean" in capsys.readouterr().out

    def test_dry_run(self, tmp_path, monkeypatch, capsys):
        base = tmp_path / "integrations"
        base.mkdir()
        (base / "aider").mkdir()
        f = base / "aider" / "CONVENTIONS.md"
        f.write_text("content", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["clean.py", "--dry-run"]):
            mod.main()
        out = capsys.readouterr().out
        assert f.is_file()
        assert "Run without --dry-run" in out

    def test_dry_run_all(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "integrations").mkdir()
        d = tmp_path / "__pycache__"
        d.mkdir()
        (d / "module.pyc").write_text("", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["clean.py", "--dry-run", "--all"]):
            mod.main()
        assert "Run without --dry-run" in capsys.readouterr().out

    def test_actual_delete(self, tmp_path, monkeypatch, capsys):
        base = tmp_path / "integrations"
        base.mkdir()
        (base / "aider").mkdir()
        f = base / "aider" / "CONVENTIONS.md"
        f.write_text("content", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["clean.py"]):
            mod.main()
        assert not f.exists()
        assert "freed" in capsys.readouterr().out

    def test_actual_delete_all(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "integrations").mkdir()
        d = tmp_path / "__pycache__"
        d.mkdir()
        (d / "module.pyc").write_text("", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        with patch.object(sys, "argv", ["clean.py", "--all"]):
            mod.main()
        assert not d.exists()
        assert "Done" in capsys.readouterr().out

    def test_dry_run_valueerror(self, tmp_path, monkeypatch, capsys):
        """Trigger ValueError when relative_to fails during display."""
        base = tmp_path / "integrations"
        base.mkdir()
        d = base / "gemini-cli"
        d.mkdir()
        f = d / "gemini-extension.json"
        f.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)

        original = mod.Path.relative_to

        def _bad_rel(path_self, *args):
            if path_self.name == "gemini-extension.json":
                raise ValueError
            return original(path_self, *args)
        monkeypatch.setattr(mod.Path, "relative_to", _bad_rel)
        with patch.object(sys, "argv", ["clean.py", "--dry-run"]):
            mod.main()
        assert "Run without --dry-run" in capsys.readouterr().out
