"""Tests for scripts/check-divisions.py — division consistency check."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "check_divisions", str(SCRIPTS_DIR / "check-divisions.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

load_canonical_divisions = mod.load_canonical_divisions
extract_agent_dirs_from_script = mod.extract_agent_dirs_from_script
has_agent_file = mod.has_agent_file
compare_sets = mod.compare_sets


class TestLoadCanonicalDivisions:
    def test_loads_divisions(self, tmp_path, monkeypatch):
        f = tmp_path / "divisions.json"
        f.write_text(json.dumps({
            "divisions": {"engineering": {}, "design": {}, "marketing": {}}
        }), encoding="utf-8")
        monkeypatch.setattr(mod, "DIVISIONS_JSON", f)
        divs = load_canonical_divisions()
        assert divs == ["design", "engineering", "marketing"]


class TestExtractAgentDirs:
    def test_extracts_array(self, tmp_path):
        f = tmp_path / "convert.sh"
        f.write_text('AGENT_DIRS=( engineering design "game-development" marketing )', encoding="utf-8")
        dirs = extract_agent_dirs_from_script(f)
        assert "engineering" in dirs
        assert "game-development" in dirs

    def test_no_array_returns_empty(self, tmp_path):
        f = tmp_path / "script.sh"
        f.write_text("echo hello", encoding="utf-8")
        assert extract_agent_dirs_from_script(f) == []


class TestHasAgentFile:
    def test_has_agent(self, tmp_path):
        d = tmp_path / "engineering"
        d.mkdir()
        (d / "agent.md").write_text("---\nname: A\n---\nBody", encoding="utf-8")
        assert has_agent_file(d) is True

    def test_no_agent_files(self, tmp_path):
        d = tmp_path / "engineering"
        d.mkdir()
        (d / "README.md").write_text("# README", encoding="utf-8")
        assert has_agent_file(d) is False

    def test_not_a_directory(self, tmp_path):
        assert has_agent_file(tmp_path / "nope") is False

    def test_oserror_during_read(self, tmp_path, monkeypatch):
        d = tmp_path / "eng"
        d.mkdir()
        (d / "agent.md").write_text("---\nname: A\n---\nBody", encoding="utf-8")

        original = mod.Path.read_text

        def _fail(path_self, *args, **kwargs):
            if path_self.name == "agent.md":
                raise OSError
            return original(path_self, *args, **kwargs)
        monkeypatch.setattr(mod.Path, "read_text", _fail)
        assert has_agent_file(d) is False


class TestCompareSets:
    def test_all_match(self):
        assert compare_sets("test", ["a", "b"], ["a", "b"]) == []

    def test_missing(self):
        errors = compare_sets("test", ["a", "b", "c"], ["a"])
        assert len(errors) == 1
        assert "missing" in errors[0]

    def test_extra(self):
        errors = compare_sets("test", ["a"], ["a", "b", "c"])
        assert len(errors) == 1
        assert "extra" in errors[0]

    def test_both_missing_and_extra(self):
        errors = compare_sets("test", ["a", "b"], ["b", "c"])
        assert len(errors) == 2


class TestMainFunction:
    def test_missing_divisions_json(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "DIVISIONS_JSON", tmp_path / "nonexistent.json")
        with patch.object(sys, "argv", ["check-divisions.py"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1
        assert "not found" in capsys.readouterr().out

    def test_all_passing(self, tmp_path, monkeypatch, capsys):
        d = tmp_path / "testdiv"
        d.mkdir()
        (d / "agent.md").write_text("---\nname: A\n---\nBody", encoding="utf-8")
        f = tmp_path / "divisions.json"
        f.write_text(json.dumps({
            "divisions": {
                "testdiv": {"label": "Test", "icon": "star", "color": "blue"},
            }
        }), encoding="utf-8")
        monkeypatch.setattr(mod, "DIVISIONS_JSON", f)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        def _fake_run(*args, **kwargs):
            class R:
                stdout = "testdiv/file.md"
            return R()
        monkeypatch.setattr(mod.subprocess, "run", _fake_run)

        with patch.object(sys, "argv", ["check-divisions.py"]):
            mod.main()
        assert "PASSED" in capsys.readouterr().out

    def test_missing_field_in_division(self, tmp_path, monkeypatch, capsys):
        d = tmp_path / "testdiv"
        d.mkdir()
        (d / "agent.md").write_text("---\nname: A\n---\nBody", encoding="utf-8")
        f = tmp_path / "divisions.json"
        f.write_text(json.dumps({
            "divisions": {
                "testdiv": {"label": "Test"},
            }
        }), encoding="utf-8")
        monkeypatch.setattr(mod, "DIVISIONS_JSON", f)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        def _fake_run(*args, **kwargs):
            class R:
                stdout = "testdiv/file.md"
            return R()
        monkeypatch.setattr(mod.subprocess, "run", _fake_run)

        with patch.object(sys, "argv", ["check-divisions.py"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1

    def test_div_has_dir_but_no_agent_files(self, tmp_path, monkeypatch, capsys):
        d = tmp_path / "testdiv"
        d.mkdir()
        (d / "README.md").write_text("not an agent", encoding="utf-8")
        f = tmp_path / "divisions.json"
        f.write_text(json.dumps({
            "divisions": {
                "testdiv": {"label": "Test", "icon": "star", "color": "blue"},
            }
        }), encoding="utf-8")
        monkeypatch.setattr(mod, "DIVISIONS_JSON", f)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        def _fake_run(*args, **kwargs):
            class R:
                stdout = "testdiv/file.md"
            return R()
        monkeypatch.setattr(mod.subprocess, "run", _fake_run)

        with patch.object(sys, "argv", ["check-divisions.py"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1

    def test_division_without_directory(self, tmp_path, monkeypatch, capsys):
        """Division in JSON has no matching directory on disk."""
        f = tmp_path / "divisions.json"
        f.write_text(json.dumps({
            "divisions": {
                "ghostdiv": {"label": "Ghost", "icon": "ghost", "color": "gray"},
            }
        }), encoding="utf-8")
        monkeypatch.setattr(mod, "DIVISIONS_JSON", f)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        def _fake_run(*args, **kwargs):
            class R:
                stdout = "other/file.md"
            return R()
        monkeypatch.setattr(mod.subprocess, "run", _fake_run)

        with patch.object(sys, "argv", ["check-divisions.py"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1
        assert "has no directory" in capsys.readouterr().out

    def test_with_scripts_and_workflow_checks(self, tmp_path, monkeypatch, capsys):
        d = tmp_path / "testdiv"
        d.mkdir()
        (d / "agent.md").write_text("---\nname: A\n---\nBody", encoding="utf-8")
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "convert.sh").write_text(
            'AGENT_DIRS=(\n  "testdiv"\n)', encoding="utf-8")
        (scripts_dir / "lint-agents.sh").write_text(
            'AGENT_DIRS=(\n  "testdiv"\n)', encoding="utf-8")
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "lint-agents.yml").write_text(
            "paths:\n  - testdiv/\n  - testdiv/**\n", encoding="utf-8")
        f = tmp_path / "divisions.json"
        f.write_text(json.dumps({
            "divisions": {
                "testdiv": {"label": "Test", "icon": "star", "color": "blue"},
            }
        }), encoding="utf-8")
        monkeypatch.setattr(mod, "DIVISIONS_JSON", f)
        monkeypatch.setattr(mod, "REPO", tmp_path)

        def _fake_run(*args, **kwargs):
            class R:
                stdout = "testdiv/file.md"
            return R()
        monkeypatch.setattr(mod.subprocess, "run", _fake_run)

        with patch.object(sys, "argv", ["check-divisions.py"]):
            mod.main()
        assert "PASSED" in capsys.readouterr().out

    def test_workflow_missing_path_filter(self, tmp_path, monkeypatch, capsys):
        """Workflow exists but doesn't mention the division."""
        d = tmp_path / "testdiv"
        d.mkdir()
        (d / "agent.md").write_text("---\nname: A\n---\nBody", encoding="utf-8")
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "lint-agents.yml").write_text("paths:\n  - other/\n", encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        f = tmp_path / "divisions.json"
        f.write_text(json.dumps({
            "divisions": {
                "testdiv": {"label": "Test", "icon": "star", "color": "blue"},
            }
        }), encoding="utf-8")
        monkeypatch.setattr(mod, "DIVISIONS_JSON", f)

        def _fake_run(*args, **kwargs):
            class R:
                stdout = "testdiv/file.md"
            return R()
        monkeypatch.setattr(mod.subprocess, "run", _fake_run)

        with patch.object(sys, "argv", ["check-divisions.py"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "has no path filter" in out
