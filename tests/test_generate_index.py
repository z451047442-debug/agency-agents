"""Tests for scripts/generate-index.py — AGENTS.json index generator."""
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _load_mod():
    spec = importlib.util.spec_from_file_location(
        "generate_index", str(SCRIPTS_DIR / "generate-index.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_mod()
build_index = mod.build_index
format_json = mod.format_json


AGENT_CONTENT = """---
name: "Test Agent"
description: "Test description"
emoji: "\U0001f9ea"
color: teal
version: "1.0.0"
date_added: "2026-07-03"
depends_on:
  - dep-one
  - dep-two
nexus_roles:
  - phase-3-build
---

## Identity
You are a test agent.

## Mission
Test things.

## Rules
1. Test everything.
"""


class TestBuildIndex:
    def test_builds_index_from_agents(self, tmp_path, monkeypatch):
        from _shared import discovery
        original_repo = discovery.REPO
        try:
            discovery.REPO = tmp_path
            cat_dir = tmp_path / "engineering"
            cat_dir.mkdir(parents=True)
            (cat_dir / "engineering-test-agent.md").write_text(AGENT_CONTENT, encoding="utf-8")
            index = build_index()
            assert index["version"] == "1.0"
            assert index["total_agents"] == 1
            assert len(index["agents"]) == 1
            agent = index["agents"][0]
            assert agent["id"] == "engineering-test-agent"
            assert agent["depends_on"] == ["dep-one", "dep-two"]
            assert agent["nexus_roles"] == ["phase-3-build"]
        finally:
            discovery.REPO = original_repo

    def test_skips_invalid_frontmatter(self, tmp_path):
        from _shared import discovery
        original_repo = discovery.REPO
        try:
            discovery.REPO = tmp_path
            cat_dir = tmp_path / "eng"
            cat_dir.mkdir(parents=True)
            (cat_dir / "eng-bad.md").write_text("No frontmatter", encoding="utf-8")
            (cat_dir / "eng-good.md").write_text(AGENT_CONTENT, encoding="utf-8")
            index = build_index()
            assert index["total_agents"] == 1
        finally:
            discovery.REPO = original_repo

    def test_skips_agent_without_name(self, tmp_path):
        from _shared import discovery
        original_repo = discovery.REPO
        try:
            discovery.REPO = tmp_path
            cat_dir = tmp_path / "eng"
            cat_dir.mkdir(parents=True)
            content = """---
description: "No name field"
emoji: "X"
color: red
---

## Identity
Test.
## Mission
Test.
## Rules
Test.
"""
            (cat_dir / "eng-no-name.md").write_text(content, encoding="utf-8")
            index = build_index()
            assert index["total_agents"] == 0
        finally:
            discovery.REPO = original_repo

    def test_agent_without_deps_and_nexus(self, tmp_path):
        from _shared import discovery
        original_repo = discovery.REPO
        try:
            discovery.REPO = tmp_path
            cat_dir = tmp_path / "design"
            cat_dir.mkdir(parents=True)
            content = """---
name: "Minimal"
description: "Minimal agent"
emoji: "X"
color: red
---

## Identity
Minimal agent.

## Mission
Test.

## Rules
None.
"""
            (cat_dir / "design-minimal.md").write_text(content, encoding="utf-8")
            index = build_index()
            agent = index["agents"][0]
            assert "depends_on" not in agent
            assert "nexus_roles" not in agent
        finally:
            discovery.REPO = original_repo


class TestFormatJson:
    def test_formats_agents_as_json_lines(self):
        data = {
            "version": "1.0", "generated": "2026-07-13",
            "agents": [{"id": "a", "name": "A", "description": "D", "emoji": "E",
                        "category": "c", "subcategory": "", "path": "c/a.md"}],
            "total_categories": 1, "total_agents": 1,
        }
        result = format_json(data)
        assert '"version":"1.0"' in result
        assert '"id":"a"' in result
        assert '"total_agents":1' in result

    def test_multiple_agents_separated_by_comma(self):
        data = {
            "version": "1.0", "generated": "2026-07-13",
            "agents": [
                {"id": "a", "name": "A", "description": "D", "emoji": "E",
                 "category": "c", "subcategory": "", "path": "c/a.md"},
                {"id": "b", "name": "B", "description": "D", "emoji": "E",
                 "category": "c", "subcategory": "", "path": "c/b.md"},
            ],
            "total_categories": 1, "total_agents": 2,
        }
        result = format_json(data)
        assert result.count('"id"') == 2


class TestMain:
    def test_generate_writes_file(self, tmp_path):
        from _shared import discovery
        original_repo = discovery.REPO
        try:
            discovery.REPO = tmp_path
            (tmp_path / "engineering").mkdir(parents=True)
            (tmp_path / "engineering/engineering-test.md").write_text(AGENT_CONTENT, encoding="utf-8")
            out = tmp_path / "AGENTS.json"
            with patch.object(sys, "argv", ["generate-index.py", "--out", str(out)]):
                mod.main()
            assert out.exists()
            data = json.loads(out.read_text(encoding="utf-8"))
            assert data["total_agents"] == 1
        finally:
            discovery.REPO = original_repo

    def test_check_up_to_date(self, tmp_path):
        from _shared import discovery
        original_repo = discovery.REPO
        try:
            discovery.REPO = tmp_path
            (tmp_path / "eng").mkdir(parents=True)
            (tmp_path / "eng/eng-test.md").write_text(AGENT_CONTENT, encoding="utf-8")
            out = tmp_path / "AGENTS.json"
            with patch.object(sys, "argv", ["generate-index.py", "--out", str(out)]):
                mod.main()
            with patch.object(sys, "argv", ["generate-index.py", "--check", "--out", str(out)]):
                with pytest.raises(SystemExit) as exc:
                    mod.main()
                assert exc.value.code == 0
        finally:
            discovery.REPO = original_repo

    def test_check_stale(self, tmp_path):
        from _shared import discovery
        original_repo = discovery.REPO
        try:
            discovery.REPO = tmp_path
            (tmp_path / "eng").mkdir(parents=True)
            (tmp_path / "eng/eng-test.md").write_text(AGENT_CONTENT, encoding="utf-8")
            out = tmp_path / "AGENTS.json"
            out.write_text('{"version":"1.0","agents":[],"total_agents":0,"total_categories":0}', encoding="utf-8")
            with patch.object(sys, "argv", ["generate-index.py", "--check", "--out", str(out)]):
                with pytest.raises(SystemExit) as exc:
                    mod.main()
                assert exc.value.code == 1
        finally:
            discovery.REPO = original_repo

    def test_check_missing_file(self, tmp_path):
        out = tmp_path / "nonexistent.json"
        with patch.object(sys, "argv", ["generate-index.py", "--check", "--out", str(out)]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1

    def test_check_invalid_json(self, tmp_path):
        from _shared import discovery
        original_repo = discovery.REPO
        try:
            discovery.REPO = tmp_path
            (tmp_path / "eng").mkdir(parents=True)
            (tmp_path / "eng/eng-test.md").write_text(AGENT_CONTENT, encoding="utf-8")
            out = tmp_path / "AGENTS.json"
            out.write_text("not json", encoding="utf-8")
            with patch.object(sys, "argv", ["generate-index.py", "--check", "--out", str(out)]):
                with pytest.raises(SystemExit) as exc:
                    mod.main()
                assert exc.value.code == 1
        finally:
            discovery.REPO = original_repo
