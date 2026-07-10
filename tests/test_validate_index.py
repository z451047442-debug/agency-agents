"""Tests for scripts/validate-index.py — AGENTS.json validation."""

import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "validate_index", str(SCRIPTS_DIR / "validate-index.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

load_json = mod.load_json
load_schema = mod.load_schema
validate_schema = mod.validate_schema
discover_md_files = mod.discover_md_files
check_cross_reference = mod.check_cross_reference
EXCLUDE_DIRS = mod.EXCLUDE_DIRS


# ── load_json ─────────────────────────────────────────────────────────────────

class TestLoadJson:
    def test_valid_json_file(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text('{"key": "value"}', encoding="utf-8")
        data, err = load_json(str(p))
        assert data == {"key": "value"}
        assert err is None

    def test_invalid_json_syntax(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{invalid", encoding="utf-8")
        data, err = load_json(str(p))
        assert data is None
        assert "Invalid JSON" in err

    def test_file_not_found(self, tmp_path):
        data, err = load_json(str(tmp_path / "nope.json"))
        assert data is None
        assert "File not found" in err

    def test_empty_json_object(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text("{}", encoding="utf-8")
        data, err = load_json(str(p))
        assert data == {}
        assert err is None

    def test_json_array(self, tmp_path):
        p = tmp_path / "arr.json"
        p.write_text('[1, 2, 3]', encoding="utf-8")
        data, err = load_json(str(p))
        assert data == [1, 2, 3]
        assert err is None


# ── load_schema ───────────────────────────────────────────────────────────────

class TestLoadSchema:
    def test_loads_valid_schema(self, tmp_path):
        schema_content = json.dumps({
            "type": "object",
            "properties": {"agents": {"type": "array"}},
            "required": ["agents"]
        })
        p = tmp_path / "schema.json"
        p.write_text(schema_content, encoding="utf-8")
        data, err = load_schema(str(p))
        assert err is None
        assert data["type"] == "object"

    def test_file_not_found(self, tmp_path):
        data, err = load_schema(str(tmp_path / "nope.json"))
        assert data is None
        assert "File not found" in err


# ── validate_schema ───────────────────────────────────────────────────────────

class TestValidateSchema:
    def test_skip_when_jsonschema_not_installed(self):
        schema = {"type": "object"}
        data = {"agents": []}
        with patch.dict("sys.modules", {"jsonschema": None}):
            errors = validate_schema(data, schema)
        assert len(errors) == 1
        assert errors[0].startswith("SKIP:")

    def test_valid_data_passes(self):
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")
        schema = {
            "type": "object",
            "properties": {"agents": {"type": "array"}},
            "required": ["agents"]
        }
        data = {"agents": []}
        errors = validate_schema(data, schema)
        assert errors == []

    def test_missing_required_field(self):
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")
        schema = {
            "type": "object",
            "properties": {"agents": {"type": "array"}},
            "required": ["agents", "version"]
        }
        data = {"agents": []}
        errors = validate_schema(data, schema)
        assert len(errors) > 0
        assert any("version" in e for e in errors)

    def test_wrong_type(self):
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")
        schema = {
            "type": "object",
            "properties": {"agents": {"type": "array"}},
            "required": ["agents"]
        }
        data = {"agents": "not_an_array"}
        errors = validate_schema(data, schema)
        assert len(errors) > 0


# ── discover_md_files ─────────────────────────────────────────────────────────

class TestDiscoverMdFiles:
    def test_discovers_files_in_categories(self, tmp_path):
        (tmp_path / "engineering").mkdir()
        (tmp_path / "engineering" / "agent.md").write_text("", encoding="utf-8")
        (tmp_path / "design").mkdir()
        (tmp_path / "design" / "ui-expert.md").write_text("", encoding="utf-8")

        result = discover_md_files(str(tmp_path))
        assert "engineering/agent.md" in result
        assert "design/ui-expert.md" in result
        assert len(result) == 2

    def test_excludes_special_dirs(self, tmp_path):
        for d in EXCLUDE_DIRS:
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
            (tmp_path / d / "should_be_excluded.md").write_text("x", encoding="utf-8")

        result = discover_md_files(str(tmp_path))
        for path_key in result:
            for excluded in EXCLUDE_DIRS:
                assert not path_key.startswith(excluded + "/"), \
                    f"Should have excluded {path_key}"

    def test_excludes_hidden_dirs(self, tmp_path):
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden" / "secret.md").write_text("", encoding="utf-8")
        result = discover_md_files(str(tmp_path))
        assert len(result) == 0

    def test_empty_repo(self, tmp_path):
        result = discover_md_files(str(tmp_path))
        assert result == {}

    def test_ignores_non_md_files(self, tmp_path):
        (tmp_path / "engineering").mkdir()
        (tmp_path / "engineering" / "notes.txt").write_text("", encoding="utf-8")
        (tmp_path / "engineering" / "README.md").write_text("", encoding="utf-8")
        result = discover_md_files(str(tmp_path))
        assert len(result) == 1

    def test_recursive_subdirs(self, tmp_path):
        (tmp_path / "game-development").mkdir()
        (tmp_path / "game-development" / "blender").mkdir(parents=True)
        (tmp_path / "game-development" / "godot").mkdir()
        (tmp_path / "game-development" / "blender" / "artist.md").write_text(
            "", encoding="utf-8")
        (tmp_path / "game-development" / "godot" / "dev.md").write_text(
            "", encoding="utf-8")

        result = discover_md_files(str(tmp_path))
        assert "game-development/blender/artist.md" in result
        assert "game-development/godot/dev.md" in result
        assert len(result) == 2

    def test_uses_forward_slashes_in_paths(self, tmp_path):
        (tmp_path / "engineering").mkdir()
        (tmp_path / "engineering" / "agent.md").write_text("", encoding="utf-8")
        result = discover_md_files(str(tmp_path))
        for key in result:
            assert "\\" not in key
            assert "/" in key


# ── check_cross_reference ─────────────────────────────────────────────────────

class TestCheckCrossReference:
    def test_all_in_sync(self):
        data = {
            "agents": [
                {"id": "a", "path": "eng/a.md"},
                {"id": "b", "path": "eng/b.md"},
            ],
            "total_agents": 2
        }
        md_files = {
            "eng/a.md": Path("/fake/eng/a.md"),
            "eng/b.md": Path("/fake/eng/b.md")
        }
        has_err, orphan, missing, lines = check_cross_reference(data, md_files)
        assert not has_err
        assert orphan == set()
        assert missing == set()

    def test_orphan_entry_in_json(self):
        data = {
            "agents": [
                {"id": "a", "path": "eng/a.md"},
                {"id": "ghost", "path": "eng/ghost.md"},
            ],
            "total_agents": 2
        }
        md_files = {"eng/a.md": Path("/fake/eng/a.md")}
        has_err, orphan, missing, lines = check_cross_reference(data, md_files)
        assert has_err
        assert "eng/ghost.md" in orphan

    def test_missing_from_json(self):
        data = {
            "agents": [{"id": "a", "path": "eng/a.md"}],
            "total_agents": 1
        }
        md_files = {
            "eng/a.md": Path("/fake/eng/a.md"),
            "eng/b.md": Path("/fake/eng/b.md")
        }
        has_err, orphan, missing, lines = check_cross_reference(data, md_files)
        assert has_err
        assert "eng/b.md" in missing

    def test_total_agents_mismatch(self):
        data = {
            "agents": [{"id": "a", "path": "eng/a.md"}],
            "total_agents": 999
        }
        md_files = {"eng/a.md": Path("/fake/eng/a.md")}
        has_err, orphan, missing, lines = check_cross_reference(data, md_files)
        assert has_err
        assert any("total_agents" in line for line in lines)

    def test_empty_agents_list(self):
        data = {"agents": [], "total_agents": 0}
        md_files = {}
        has_err, orphan, missing, lines = check_cross_reference(data, md_files)
        assert not has_err

    def test_both_orphan_and_missing(self):
        data = {
            "agents": [{"id": "old", "path": "legacy/old.md"}],
            "total_agents": 1
        }
        md_files = {"active/current.md": Path("/fake/active/current.md")}
        has_err, orphan, missing, lines = check_cross_reference(data, md_files)
        assert has_err
        assert "legacy/old.md" in orphan
        assert "active/current.md" in missing

    def test_ok_messages_present_on_success(self):
        data = {"agents": [{"id": "a", "path": "a.md"}], "total_agents": 1}
        md_files = {"a.md": Path("/fake/a.md")}
        has_err, orphan, missing, lines = check_cross_reference(data, md_files)
        assert any("No orphan entries" in l for l in lines)
        assert any("No missing entries" in l for l in lines)
        assert any("total_agents" in l for l in lines)
