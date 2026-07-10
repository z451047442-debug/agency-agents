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


# ── load_json OSError (lines 37-38) ─────────────────────────────────────────

class TestLoadJsonOSError:
    """Test OSError handling in load_json (lines 37-38)."""

    def test_os_error(self, tmp_path):
        """Line 37-38: OSError raised by open is caught and returned as error."""
        p = tmp_path / "data.json"
        p.write_text('{"key": "value"}', encoding="utf-8")

        with patch("builtins.open", side_effect=OSError("permission denied")):
            data, err = load_json(str(p))
            assert data is None
            assert "Error reading" in err


# ── helpers for main() tests ────────────────────────────────────────────────

def _make_index(path, agents=None, total_agents=None):
    """Write a minimal AGENTS.json to a temp path."""
    if agents is None:
        agents = [{
            "id": "test-agent", "name": "Test Agent",
            "category": "test", "description": "A test agent",
            "path": "test/test-agent.md",
        }]
    if total_agents is None:
        total_agents = len(agents)
    data = {"agents": agents, "total_agents": total_agents}
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_schema(path):
    """Write a minimal valid JSON schema to a temp path."""
    path.write_text(json.dumps({
        "type": "object",
        "properties": {
            "agents": {"type": "array"},
            "total_agents": {"type": "integer"},
        },
        "required": ["agents"],
    }), encoding="utf-8")


def _setup_repo_schema(monkeypatch, tmp_path):
    """Setup temp REPO and SCHEMA_FILE for main() tests."""
    monkeypatch.setattr(mod, "REPO", tmp_path)
    schema_path = tmp_path / "schema.json"
    _make_schema(schema_path)
    monkeypatch.setattr(mod, "SCHEMA_FILE", schema_path)


# ── main() function ─────────────────────────────────────────────────────────

class TestMainFunction:
    """Tests for the main() function covering lines 128-201."""

    def test_main_all_checks_pass(self, tmp_path, monkeypatch):
        """All checks pass with valid AGENTS.json and matching filesystem."""
        index_path = tmp_path / "AGENTS.json"
        cat_dir = tmp_path / "test"
        cat_dir.mkdir()
        (cat_dir / "test-agent.md").write_text("content", encoding="utf-8")

        _make_index(index_path, [{
            "id": "test-agent", "name": "Test Agent",
            "category": "test", "description": "A test agent",
            "path": "test/test-agent.md",
        }])

        _setup_repo_schema(monkeypatch, tmp_path)
        with patch.object(sys, "argv",
                          ["validate-index.py", "--path", str(index_path)]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 0

    def test_main_invalid_json_syntax(self, tmp_path, monkeypatch, capsys):
        """Invalid JSON syntax → exits with code 1."""
        index_path = tmp_path / "AGENTS.json"
        index_path.write_text("{not valid json", encoding="utf-8")

        with patch.object(sys, "argv",
                          ["validate-index.py", "--path", str(index_path)]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1

        captured = capsys.readouterr()
        assert "FAIL:" in captured.out

    def test_main_schema_only_flag(self, tmp_path, monkeypatch):
        """--schema-only skips filesystem cross-reference."""
        index_path = tmp_path / "AGENTS.json"
        _make_index(index_path)

        _setup_repo_schema(monkeypatch, tmp_path)
        with patch.object(sys, "argv",
                          ["validate-index.py", "--path", str(index_path),
                           "--schema-only"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 0

    def test_main_sync_only_flag(self, tmp_path, monkeypatch):
        """--sync-only skips schema validation and duplicate check."""
        index_path = tmp_path / "AGENTS.json"
        cat_dir = tmp_path / "test"
        cat_dir.mkdir()
        (cat_dir / "test-agent.md").write_text("content", encoding="utf-8")

        _make_index(index_path, [{
            "id": "test-agent", "name": "Test Agent",
            "category": "test", "description": "A test agent",
            "path": "test/test-agent.md",
        }])

        _setup_repo_schema(monkeypatch, tmp_path)
        with patch.object(sys, "argv",
                          ["validate-index.py", "--path", str(index_path),
                           "--sync-only"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 0

    def test_main_schema_load_error(self, tmp_path, monkeypatch):
        """Schema file not found → schema validation error, exits 1."""
        index_path = tmp_path / "AGENTS.json"
        cat_dir = tmp_path / "test"
        cat_dir.mkdir()
        (cat_dir / "test-agent.md").write_text("content", encoding="utf-8")

        _make_index(index_path, [{
            "id": "test-agent", "name": "Test Agent",
            "category": "test", "description": "A test agent",
            "path": "test/test-agent.md",
        }])

        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "SCHEMA_FILE",
                            tmp_path / "nonexistent_schema.json")

        with patch.object(sys, "argv",
                          ["validate-index.py", "--path", str(index_path)]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1

    def test_main_duplicate_ids(self, tmp_path, monkeypatch):
        """Duplicate agent IDs → validation error."""
        index_path = tmp_path / "AGENTS.json"
        _make_index(index_path, [
            {"id": "dup-id", "name": "First", "category": "c",
             "description": "d", "path": "c/first.md"},
            {"id": "dup-id", "name": "Second", "category": "c",
             "description": "d", "path": "c/second.md"},
        ])

        _setup_repo_schema(monkeypatch, tmp_path)
        with patch.object(sys, "argv",
                          ["validate-index.py", "--path", str(index_path)]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1

    def test_main_orphan_and_missing(self, tmp_path, monkeypatch):
        """Orphan entries + missing files → exits with code 1."""
        index_path = tmp_path / "AGENTS.json"
        cat_dir = tmp_path / "test"
        cat_dir.mkdir()
        # Create a file NOT in AGENTS.json (missing) but DON'T create
        # the file referenced in AGENTS.json (orphan)
        (cat_dir / "extra-file.md").write_text("content", encoding="utf-8")

        _make_index(index_path, [{
            "id": "orphan-agent", "name": "Orphan",
            "category": "test", "description": "Orphaned agent",
            "path": "test/orphan-agent.md",  # this file does NOT exist
        }])

        _setup_repo_schema(monkeypatch, tmp_path)
        with patch.object(sys, "argv",
                          ["validate-index.py", "--path", str(index_path)]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1

    def test_main_total_agents_mismatch(self, tmp_path, monkeypatch):
        """total_agents field doesn't match array length → error."""
        index_path = tmp_path / "AGENTS.json"
        _make_index(index_path, [{
            "id": "test-agent", "name": "Test Agent",
            "category": "test", "description": "A test agent",
            "path": "test/test-agent.md",
        }], total_agents=999)

        _setup_repo_schema(monkeypatch, tmp_path)
        with patch.object(sys, "argv",
                          ["validate-index.py", "--path", str(index_path)]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1

    def test_main_schema_validation_errors(self, tmp_path, monkeypatch):
        """Schema validation finds errors → exits 1 if jsonschema installed."""
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            pytest.skip("jsonschema not installed")

        index_path = tmp_path / "AGENTS.json"
        # Create a schema that requires fields our data doesn't have
        schema_path = tmp_path / "schema.json"
        schema_path.write_text(json.dumps({
            "type": "object",
            "properties": {"agents": {"type": "array"}},
            "required": ["agents", "version"]
        }), encoding="utf-8")

        _make_index(index_path)  # no "version" field

        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "SCHEMA_FILE", schema_path)

        with patch.object(sys, "argv",
                          ["validate-index.py", "--path", str(index_path)]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1

    def test_main_schema_skip_jsonschema_not_installed(self, tmp_path, monkeypatch,
                                                        capsys):
        """Line 162: jsonschema not installed → WARN message printed."""
        index_path = tmp_path / "AGENTS.json"
        cat_dir = tmp_path / "test"
        cat_dir.mkdir()
        (cat_dir / "test-agent.md").write_text("content", encoding="utf-8")

        _make_index(index_path, [{
            "id": "test-agent", "name": "Test Agent",
            "category": "test", "description": "A test agent",
            "path": "test/test-agent.md",
        }])

        _setup_repo_schema(monkeypatch, tmp_path)
        # Simulate jsonschema not installed
        with patch.dict("sys.modules", {"jsonschema": None}):
            with patch.object(sys, "argv",
                              ["validate-index.py", "--path", str(index_path)]):
                with pytest.raises(SystemExit) as exc:
                    mod.main()
                assert exc.value.code == 0

        captured = capsys.readouterr()
        assert "WARN:" in captured.out

    def test_main_sync_only_skips_schema_load_error(self, tmp_path, monkeypatch):
        """--sync-only skips schema, so nonexistent schema won't cause error."""
        index_path = tmp_path / "AGENTS.json"
        cat_dir = tmp_path / "test"
        cat_dir.mkdir()
        (cat_dir / "test-agent.md").write_text("content", encoding="utf-8")

        _make_index(index_path, [{
            "id": "test-agent", "name": "Test Agent",
            "category": "test", "description": "A test agent",
            "path": "test/test-agent.md",
        }])

        monkeypatch.setattr(mod, "REPO", tmp_path)
        # Schema file doesn't matter — sync-only skips schema entirely
        monkeypatch.setattr(mod, "SCHEMA_FILE",
                            tmp_path / "nonexistent.json")

        with patch.object(sys, "argv",
                          ["validate-index.py", "--path", str(index_path),
                           "--sync-only"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 0
