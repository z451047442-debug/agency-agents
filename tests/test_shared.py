"""Tests for scripts/_shared/ — terminal, frontmatter, discovery modules."""

import sys
from pathlib import Path
from unittest import mock

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from _shared import (  # noqa: E402
    BOLD,
    CYAN,
    GREEN,
    RED,
    RESET,
    YELLOW,
    discover_agents,
    get_body,
    get_field,
    get_frontmatter_text,
    get_list_field,
    supports_color,
)

SAMPLE_YAML = """---
name: "Test Agent"
description: "A test agent"
version: "1.0.0"
depends_on:
  - dep-one
  - dep-two
nexus_roles:
  - phase-1-discovery
  - phase-2-strategy
color: blue
---"""


class TestTerminal:
    def test_supports_color_true(self):
        with mock.patch.object(sys.stdout, "isatty", return_value=True), \
             mock.patch.dict("os.environ", {"TERM": "xterm-256color"}, clear=True):
            assert supports_color() is True

    def test_supports_color_false_no_tty(self):
        with mock.patch.object(sys.stdout, "isatty", return_value=False), \
             mock.patch.dict("os.environ", {}, clear=True):
            assert supports_color() is False

    def test_supports_color_false_dumb_term(self):
        with mock.patch.object(sys.stdout, "isatty", return_value=True), \
             mock.patch.dict("os.environ", {"TERM": "dumb"}, clear=True):
            assert supports_color() is False

    def test_supports_color_false_no_color_env(self):
        with mock.patch.object(sys.stdout, "isatty", return_value=True), \
             mock.patch.dict("os.environ", {"NO_COLOR": "1", "TERM": "xterm"}, clear=True):
            assert supports_color() is False

    def test_ansi_constants_are_strings(self):
        for const in (GREEN, RED, YELLOW, BOLD, CYAN, RESET):
            assert isinstance(const, str)

    def test_constants_empty_when_no_color(self, monkeypatch):
        """Module-level constants are empty strings when supports_color() is False."""
        import importlib
        from _shared import terminal

        monkeypatch.setenv("NO_COLOR", "1")
        with mock.patch.object(sys.stdout, "isatty", return_value=True):
            importlib.reload(terminal)
            assert terminal.GREEN == ""
            assert terminal.RESET == ""
            assert terminal.RED == ""


class TestFrontmatter:
    def test_get_frontmatter_text(self):
        fm = get_frontmatter_text(SAMPLE_YAML)
        assert "Test Agent" in fm

    def test_get_frontmatter_text_empty(self):
        assert get_frontmatter_text("no frontmatter") == ""

    def test_get_body(self):
        body = get_body(SAMPLE_YAML)
        assert isinstance(body, str)

    def test_get_body_empty(self):
        assert get_body("no frontmatter") == "no frontmatter"

    def test_get_field_name(self):
        fm = get_frontmatter_text(SAMPLE_YAML)
        assert "Test Agent" in get_field("name", fm)

    def test_get_field_description(self):
        fm = get_frontmatter_text(SAMPLE_YAML)
        assert "A test agent" in get_field("description", fm)

    def test_get_field_missing(self):
        fm = get_frontmatter_text(SAMPLE_YAML)
        assert get_field("nonexistent", fm) == ""

    def test_get_field_quoted_value(self):
        fm = get_frontmatter_text(SAMPLE_YAML)
        val = get_field("version", fm)
        assert "1.0.0" in val

    def test_get_list_field_depends_on(self):
        fm = get_frontmatter_text(SAMPLE_YAML)
        deps = get_list_field("depends_on", fm)
        assert deps == ["dep-one", "dep-two"]

    def test_get_list_field_nexus_roles(self):
        fm = get_frontmatter_text(SAMPLE_YAML)
        roles = get_list_field("nexus_roles", fm)
        assert roles == ["phase-1-discovery", "phase-2-strategy"]

    def test_get_list_field_missing(self):
        fm = get_frontmatter_text(SAMPLE_YAML)
        assert get_list_field("nonexistent", fm) == []

    def test_get_list_field_stops_at_next_top_level(self):
        content = "---\ndepends_on:\n  - dep-a\n  - dep-b\nnext_field: value\n---\n"
        deps = get_list_field("depends_on", content)
        assert deps == ["dep-a", "dep-b"]


class TestDiscovery:
    def test_discover_agents_returns_generator(self):
        result = discover_agents()
        assert hasattr(result, "__iter__")

    def test_discover_agents_each_item_is_tuple(self):
        for item in discover_agents():
            assert isinstance(item, tuple)
            assert len(item) == 3
            cat, rel, path = item
            assert isinstance(cat, str)
            assert isinstance(rel, str)
            assert isinstance(path, Path)
            break

    def test_discover_agents_excludes_scripts(self):
        for _cat, _rel, path in discover_agents():
            assert "scripts/" not in str(path).replace("\\", "/")

    def test_discover_agents_category_filter(self):
        found = list(discover_agents("engineering"))
        assert len(found) > 0
        for cat, _rel, _path in found:
            assert cat == "engineering"

    def test_discover_agents_nonexistent_category(self):
        found = list(discover_agents("zzz-nonexistent-category"))
        assert found == []
