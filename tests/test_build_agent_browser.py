"""Tests for scripts/build-agent-browser.py — standalone HTML builder."""
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
        "build_agent_browser", str(SCRIPTS_DIR / "build-agent-browser.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SAMPLE_INDEX = {
    "version": "1.0",
    "generated": "2026-07-13",
    "total_categories": 2,
    "total_agents": 2,
    "agents": [
        {
            "id": "test-agent-1",
            "name": "Test Agent 1",
            "description": "First test agent",
            "emoji": "🧪",
            "category": "engineering",
            "subcategory": "",
            "path": "engineering/test-agent-1.md",
            "depends_on": ["test-dep"],
            "nexus_roles": ["phase-3-build"],
        },
        {
            "id": "test-agent-2",
            "name": "Test Agent 2",
            "description": "Second test agent",
            "emoji": "🔬",
            "category": "design",
            "subcategory": "",
            "path": "design/test-agent-2.md",
        },
    ],
}


class TestBuildAgentBrowser:
    def test_builds_html_with_agents(self, tmp_path):
        mod = _load_mod()
        index_path = tmp_path / "AGENTS.json"
        index_path.write_text(json.dumps(SAMPLE_INDEX), encoding="utf-8")
        out_path = tmp_path / "agent-browser.html"

        import _shared
        original_repo = mod.REPO
        orig_shared = _shared.REPO
        try:
            mod.REPO = tmp_path
            _shared.REPO = tmp_path
            with patch.object(sys, "argv", ["build-agent-browser.py", "--out", str(out_path)]):
                mod.main()
            assert out_path.exists()
            html = out_path.read_text(encoding="utf-8")
            assert "Test Agent 1" in html
            assert "Test Agent 2" in html
            assert "🧪" in html
            assert "engineering" in html
        finally:
            mod.REPO = original_repo
            _shared.REPO = orig_shared

    def test_missing_index_exits(self, tmp_path):
        mod = _load_mod()
        original_repo = mod.REPO
        try:
            mod.REPO = tmp_path
            with patch.object(sys, "argv", ["build-agent-browser.py"]):
                with pytest.raises(SystemExit) as exc:
                    mod.main()
                assert exc.value.code == 1
        finally:
            mod.REPO = original_repo

    def test_default_output_path(self, tmp_path):
        mod = _load_mod()
        index_path = tmp_path / "AGENTS.json"
        index_path.write_text(json.dumps(SAMPLE_INDEX), encoding="utf-8")

        import _shared
        original_repo = mod.REPO
        orig_shared = _shared.REPO
        try:
            mod.REPO = tmp_path
            _shared.REPO = tmp_path
            with patch.object(sys, "argv", ["build-agent-browser.py"]):
                mod.main()
            assert (tmp_path / "agent-browser.html").exists()
        finally:
            mod.REPO = original_repo
            _shared.REPO = orig_shared
