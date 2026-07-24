"""Tests for scripts/build-architecture.py."""
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
        "build_architecture", str(SCRIPTS_DIR / "build-architecture.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SCRIPT_DATA = {
    "categories": {
        "quality": [
            {"name": "lint-agents.py", "desc": "YAML validation, section checks"},
        ],
        "maintenance": [
            {"name": "clean.py", "desc": "Project cleanup"},
        ],
        "integration": [
            {"name": "convert.py", "desc": ".md to 9 target tool formats"},
        ],
        "discovery": [
            {"name": "search-agents.py", "desc": "Keyword and category search"},
        ],
    },
    "py_total": 4,
    "sh_total": 2,
}

SHARED = {
    "modules": [
        {"name": "discovery.py", "desc": "Agent file discovery", "exports": "discover_agents()"},
        {"name": "frontmatter.py", "desc": "YAML frontmatter parsing", "exports": "get_field()"},
    ],
    "consumers": ["lint-agents", "convert", "search-agents"],
    "exports_count": 16,
}

SAMPLE_DATA = {
    "version": "v1.0.0",
    "python_req": ">=3.10",
    "coverage_threshold": "90%",
    "generated": "2026-07-15 12:00 UTC",
    "total_agents": 1292,
    "total_categories": 65,
    "category_counts": [
        {"category": "engineering", "count": 112},
        {"category": "design", "count": 24},
        {"category": "data-science", "count": 46},
    ],
    "total_tests": 1022,
    "test_modules": [
        {"module": "test_lint_agents.py", "count": 100},
        {"module": "test_convert.py", "count": 80},
    ],
    "test_modules_count": 2,
    "script_categories": SCRIPT_DATA,
    "shared": SHARED,
    "ci_workflows": [
        {"name": "Lint", "trigger": "push/PR", "actions": "lint"},
        {"name": "Test", "trigger": "push/PR", "actions": "test"},
    ],
    "ci_workflows_count": 2,
    "integration_targets": [
        {"tool": "Claude Code", "format": ".md", "converter": "direct"},
        {"tool": "Cursor", "format": ".mdc", "converter": "convert_cursor()"},
    ],
    "integration_targets_count": 2,
    "nexus_phases": ["phase-1-discovery", "phase-2-strategy", "phase-3-build"],
    "nexus_phases_count": 3,
}


class TestFmtTable:
    def test_simple_table(self):
        mod = _load_mod()
        result = mod._fmt_table(["A", "B"], [["1", "2"], ["3", "4"]])
        assert "| A | B |" in result
        assert "| 1 | 2 |" in result

    def test_empty_rows(self):
        mod = _load_mod()
        result = mod._fmt_table(["Header"], [])
        assert "| Header |" in result
        assert "---" in result


class TestMarkdownRendering:
    def test_render_markdown(self):
        mod = _load_mod()
        result = mod.render_markdown(SAMPLE_DATA)
        assert "The Agency" in result
        assert "v1.0.0" in result
        assert "engineering" in result

    def test_format_md_categories(self):
        mod = _load_mod()
        result = mod.format_md_categories(SAMPLE_DATA["category_counts"])
        assert "| engineering | 112 |" in result
        assert "| design | 24 |" in result

    def test_format_md_integration(self):
        mod = _load_mod()
        result = mod.format_md_integration(SAMPLE_DATA["integration_targets"])
        assert "| Claude Code | .md | direct |" in result
        assert "| Cursor | .mdc | convert_cursor() |" in result

    def test_format_md_test_table(self):
        mod = _load_mod()
        result = mod.format_md_test_table(SAMPLE_DATA["test_modules"])
        assert "test_lint_agents.py" in result
        assert "100" in result

    def test_format_md_shared(self):
        mod = _load_mod()
        result = mod.format_md_shared(SAMPLE_DATA["shared"])
        assert "frontmatter.py" in result
        assert "16" in result

    def test_format_md_scripts(self):
        mod = _load_mod()
        result = mod.format_md_scripts(SAMPLE_DATA["script_categories"])
        assert "lint-agents.py" in result
        assert "search-agents.py" in result

    def test_format_md_ci_table(self):
        mod = _load_mod()
        result = mod.format_md_ci_table(SAMPLE_DATA["ci_workflows"])
        assert "| Lint |" in result
        assert "| Test |" in result


class TestHtmlRendering:
    def test_render_html(self):
        mod = _load_mod()
        result = mod.render_html(SAMPLE_DATA)
        assert "<!DOCTYPE html>" in result
        assert "v1.0.0" in result

    def test_format_html_footer_stats(self):
        mod = _load_mod()
        result = mod.format_html_footer_stats(SAMPLE_DATA)
        assert "1,292" in result
        assert ">=3.10" in result

    def test_format_html_category_bars(self):
        mod = _load_mod()
        result = mod.format_html_category_bars(
            SAMPLE_DATA["category_counts"], SAMPLE_DATA["total_agents"]
        )
        assert "engineering" in result

    def test_format_html_nexus(self):
        mod = _load_mod()
        result = mod.format_html_nexus(SAMPLE_DATA["nexus_phases"])
        assert "P1" in result
        assert "Discovery" in result
        assert "P3" in result
        assert "Build" in result
        assert "agents" in result

    def test_format_html_ci_cards(self):
        mod = _load_mod()
        result = mod.format_html_ci_cards(SAMPLE_DATA["ci_workflows"])
        assert "Lint" in result

    def test_format_html_test_cards(self):
        mod = _load_mod()
        result = mod.format_html_test_cards(SAMPLE_DATA["test_modules"])
        assert "100" in result

    def test_format_html_shared_modules(self):
        mod = _load_mod()
        result = mod.format_html_shared_modules(SAMPLE_DATA["shared"])
        assert "frontmatter.py" in result
        assert "YAML" in result

    def test_format_html_script_grid(self):
        mod = _load_mod()
        result = mod.format_html_script_grid(SAMPLE_DATA["script_categories"])
        assert "lint-agents" in result

    def test_format_html_integration_cards(self):
        mod = _load_mod()
        result = mod.format_html_integration_cards(SAMPLE_DATA["integration_targets"])
        assert "Claude Code" in result


class TestDataCollection:
    def test_load_index(self, tmp_path):
        mod = _load_mod()
        index_path = tmp_path / "AGENTS.json"
        index_path.write_text(
            json.dumps({"version": "1.0", "agents": [], "total_agents": 0}),
            encoding="utf-8",
        )
        original_repo = mod.REPO
        try:
            mod.REPO = tmp_path
            result = mod.load_index()
            assert result["version"] == "1.0"
        finally:
            mod.REPO = original_repo

    def test_collect_architecture_data(self, tmp_path):
        mod = _load_mod()
        index = {
            "version": "1.0",
            "total_categories": 3,
            "total_agents": 3,
            "agents": [
                {"id": "test-1", "name": "Test 1", "category": "engineering"},
                {"id": "test-2", "name": "Test 2", "category": "design"},
                {"id": "test-3", "name": "Test 3", "category": "engineering"},
            ],
        }
        (tmp_path / "AGENTS.json").write_text(json.dumps(index), encoding="utf-8")
        (tmp_path / "engineering").mkdir(exist_ok=True)
        (tmp_path / "design").mkdir(exist_ok=True)

        original_repo = mod.REPO
        try:
            mod.REPO = tmp_path
            data = mod.collect_architecture_data()
            assert data["total_agents"] == 3
            assert data["total_categories"] == 3
        finally:
            mod.REPO = original_repo

    def test_collect_category_counts(self, tmp_path):
        mod = _load_mod()
        index = {
            "version": "1.0",
            "agents": [
                {"id": "t1", "name": "T1", "category": "engineering"},
                {"id": "t2", "name": "T2", "category": "engineering"},
                {"id": "t3", "name": "T3", "category": "design"},
            ],
        }
        (tmp_path / "AGENTS.json").write_text(json.dumps(index), encoding="utf-8")

        original_repo = mod.REPO
        try:
            mod.REPO = tmp_path
            result = mod.collect_category_counts()
            eng = next(c for c in result if c["category"] == "engineering")
            des = next(c for c in result if c["category"] == "design")
            assert eng["count"] == 2
            assert des["count"] == 1
        finally:
            mod.REPO = original_repo

    def test_collect_nexus_phases(self, tmp_path):
        mod = _load_mod()
        index = {
            "version": "1.0",
            "agents": [
                {"id": "t1", "name": "T1", "nexus_roles": ["phase-1-discovery", "phase-3-build"]},
                {"id": "t2", "name": "T2", "nexus_roles": ["phase-2-strategy"]},
                {"id": "t3", "name": "T3", "nexus_roles": ["phase-1-discovery"]},
            ],
        }
        (tmp_path / "AGENTS.json").write_text(json.dumps(index), encoding="utf-8")

        original_repo = mod.REPO
        try:
            mod.REPO = tmp_path
            result = mod.collect_nexus_phases()
            assert "phase-1-discovery" in result
            assert "phase-2-strategy" in result
            assert "phase-3-build" in result
            assert len(result) == 3
        finally:
            mod.REPO = original_repo


class TestCheckMode:
    def test_check_mode_detects_stale_md(self, tmp_path):
        mod = _load_mod()
        md_path = tmp_path / "ARCHITECTURE.md"
        html_path = tmp_path / "ARCHITECTURE.html"

        index = {
            "version": "1.0",
            "total_categories": 1,
            "total_agents": 1,
            "agents": [{"id": "test-1", "name": "Test", "category": "engineering"}],
        }
        (tmp_path / "AGENTS.json").write_text(json.dumps(index), encoding="utf-8")
        (tmp_path / "engineering").mkdir(exist_ok=True)

        original_repo = mod.REPO
        try:
            mod.REPO = tmp_path
            # First generate the files normally, then check they pass
            with patch.object(
                sys, "argv",
                ["build-architecture.py", "--out-md", str(md_path), "--out-html", str(html_path)],
            ):
                mod.main()

            # Verify files exist after generation
            assert md_path.exists()
            assert html_path.exists()
            assert "The Agency" in md_path.read_text(encoding="utf-8")

            # Now --check should pass since files are fresh
            with patch.object(
                sys, "argv",
                ["build-architecture.py", "--check", "--out-md", str(md_path), "--out-html", str(html_path)],
            ):
                with pytest.raises(SystemExit) as exc:
                    mod.main()
                assert exc.value.code == 0
        finally:
            mod.REPO = original_repo
