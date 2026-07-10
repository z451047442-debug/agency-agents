"""Tests for scripts/add-comm-section.py — communication section insertion."""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "add_comm_section", str(SCRIPTS_DIR / "add-comm-section.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

has_comm_section = mod.has_comm_section
generate_comm_section = mod.generate_comm_section
get_traits_for_agent = mod.get_traits_for_agent
insert_comm_section = mod.insert_comm_section


class TestHasCommSection:
    def test_detects_english_style_header(self):
        assert has_comm_section("## Communication Style\n\nSome content here.")

    def test_detects_emoji_header(self):
        assert has_comm_section("## 💬 Your Communication Style\n\nTrait content.")

    def test_case_insensitive(self):
        assert has_comm_section("## communication style\n\nContent.")

    def test_no_section_returns_false(self):
        assert not has_comm_section("## Identity\n\nSome identity content.")

    def test_empty_body(self):
        assert not has_comm_section("")

    def test_mid_body_detection(self):
        body = "## Identity\nContent.\n\n## 💬 Communication\n\nStyle here.\n\n## Deliverables\nList."
        assert has_comm_section(body)


class TestGenerateCommSection:
    def test_returns_section_with_header(self):
        result = generate_comm_section(
            "test-agent", "engineering",
            "Frontend development expert", "Frontend Developer", "Precise"
        )
        assert "## 💬 Your Communication Style" in result
        assert "**" in result  # has bold trait names

    def test_includes_traits(self):
        result = generate_comm_section(
            "test-agent", "data-science",
            "Machine learning expert", "ML Engineer", "Analytical"
        )
        assert len(result) > 50

    def test_unknown_category_uses_default(self):
        result = generate_comm_section(
            "test-agent", "zzz-unknown-cat",
            "Something", "Someone", ""
        )
        assert "## 💬 Your Communication Style" in result


class TestGetTraitsForAgent:
    def test_returns_list_of_tuples(self):
        traits = get_traits_for_agent(
            "engineering", "frontend developer", "Frontend Dev", ""
        )
        assert isinstance(traits, list)
        assert len(traits) > 0
        assert len(traits) <= 4
        for t in traits:
            assert isinstance(t, tuple)
            assert len(t) == 2

    def test_default_traits_for_unknown_category(self):
        traits = get_traits_for_agent(
            "nonexistent-category", "something", "Name", ""
        )
        assert len(traits) > 0
        assert len(traits) <= 4


class TestInsertCommSection:
    def test_dry_run_does_not_modify(self, tmp_path):
        path = tmp_path / "test-cat" / "test-agent.md"
        path.parent.mkdir(parents=True)
        content = """---
name: "Test"
description: "Test agent"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## 🧠 Identity
You are a test agent.

## 🚨 Critical Rules
1. Always test.

## 📦 Deliverables
- Test report
"""
        path.write_text(content, encoding="utf-8")
        original = path.read_text(encoding="utf-8")
        ok, msg = insert_comm_section(path, dry_run=True)
        assert ok
        assert path.read_text(encoding="utf-8") == original

    def test_skips_if_already_has_section(self, tmp_path):
        path = tmp_path / "test-cat" / "test-agent.md"
        path.parent.mkdir(parents=True)
        content = """---
name: "Test"
description: "Test"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
Test.

## 💬 Communication Style
Already has one.
"""
        path.write_text(content, encoding="utf-8")
        ok, msg = insert_comm_section(path, dry_run=False)
        assert not ok
        assert "already has" in msg.lower()

    def test_inserts_section_in_place(self, tmp_path):
        path = tmp_path / "test-cat" / "test-agent.md"
        path.parent.mkdir(parents=True)
        content = """---
name: "Test"
description: "Test agent"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## 🧠 Identity
You are a test agent.

## 🚨 Critical Rules
1. Always test.
2. Verify results.

## 📦 Deliverables
- Test report
"""
        path.write_text(content, encoding="utf-8")
        ok, msg = insert_comm_section(path, dry_run=False)
        assert ok
        modified = path.read_text(encoding="utf-8")
        assert "## 💬 Your Communication Style" in modified
