"""Tests for scripts/scan-boilerplate.py — Methodology boilerplate detection."""

import importlib.util
import io
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "scan_boilerplate", str(SCRIPTS_DIR / "scan-boilerplate.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

extract_section = mod.extract_section
similarity = mod.similarity
REFERENCE = mod.REFERENCE


class TestExtractSection:
    def test_extracts_methodology_section(self):
        body = "## Decision Matrix: Test\ncontent here\n## Next Section"
        assert extract_section(body) == "content here"

    def test_extracts_decision_framework(self):
        body = "intro\n## Decision Framework: Choose\nsome text\n## After"
        assert extract_section(body) == "some text"

    def test_case_insensitive_header(self):
        body = "## METHODOLOGY SELECTION\npick me\n## done"
        assert extract_section(body) == "pick me"

    def test_no_matching_header_returns_none(self):
        body = "## Identity\nwho am i\n## Mission\nwhat i do"
        assert extract_section(body) is None

    def test_empty_section(self):
        body = "## Decision Matrix\n\n## Next"
        assert extract_section(body) == ""


class TestSimilarity:
    def test_identical_is_one(self):
        assert similarity(REFERENCE, REFERENCE) == 1.0

    def test_different_strings_low(self):
        assert similarity("hello world", "goodbye universe") < 0.5


class TestMain:
    def _setup_agent(self, tmp_path, name, content):
        cat = tmp_path / "engineering"
        cat.mkdir(parents=True, exist_ok=True)
        agent = cat / name
        agent.write_text(content, encoding="utf-8")
        return agent

    def test_json_output(self, tmp_path, monkeypatch):
        self._setup_agent(tmp_path, "test.md", "---\nname: T\n---\n## Next\n")
        monkeypatch.setattr("_shared.discovery.REPO", tmp_path)
        out = io.StringIO()
        with patch.object(sys, "argv", ["scan-boilerplate.py", "--json"]), \
             patch.object(sys, "stdout", out):
            mod.main()
        assert '"total"' in out.getvalue()

    def test_safe_to_delete_counted(self, tmp_path, monkeypatch):
        self._setup_agent(tmp_path, "eng.md",
                          "---\nname: T\n---\n"
                          "## Decision Matrix\n" + REFERENCE + "\n## Next\n")
        monkeypatch.setattr("_shared.discovery.REPO", tmp_path)
        out = io.StringIO()
        with patch.object(sys, "argv", ["scan-boilerplate.py"]), \
             patch.object(sys, "stdout", out):
            mod.main()
        assert "Safe to delete" in out.getvalue()

    def test_no_section_counted(self, tmp_path, monkeypatch):
        self._setup_agent(tmp_path, "no-method.md",
                          "---\nname: T\n---\n## Identity\nnone here\n")
        monkeypatch.setattr("_shared.discovery.REPO", tmp_path)
        out = io.StringIO()
        with patch.object(sys, "argv", ["scan-boilerplate.py"]), \
             patch.object(sys, "stdout", out):
            mod.main()
        assert "No Methodology section" in out.getvalue()

    def test_tier_filter(self, tmp_path, monkeypatch):
        self._setup_agent(tmp_path, "eng.md",
                          "---\nname: T\n---\n"
                          "## Decision Matrix\n" + REFERENCE + "\n## Next\n")
        monkeypatch.setattr("_shared.discovery.REPO", tmp_path)
        out = io.StringIO()
        with patch.object(sys, "argv", ["scan-boilerplate.py", "--tier", "safe"]), \
             patch.object(sys, "stdout", out):
            mod.main()
        assert "Tier: safe" in out.getvalue()

    def test_unicode_error_skipped(self, tmp_path, monkeypatch):
        self._setup_agent(tmp_path, "bad.md", "---\nname: T\n---\n## Next\n")
        # Write a file with invalid UTF-8
        bad_path = tmp_path / "engineering" / "bad-enc.md"
        bad_path.write_bytes(b"\xff\xfe\x00\x01")
        monkeypatch.setattr("_shared.discovery.REPO", tmp_path)
        out = io.StringIO()
        with patch.object(sys, "argv", ["scan-boilerplate.py"]), \
             patch.object(sys, "stdout", out):
            mod.main()
        assert "No Methodology section" in out.getvalue()
