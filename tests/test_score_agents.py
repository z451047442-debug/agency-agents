"""Tests for scripts/score-agents.py"""
import importlib.util
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
spec = importlib.util.spec_from_file_location(
    "score_agents", str(SCRIPTS_DIR / "score-agents.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

score_agent = mod.score_agent
get_frontmatter_text = mod.get_frontmatter_text
get_body = mod.get_body
get_field = mod.get_field

SAMPLE = """---
name: "Test Agent"
description: "Test agent for scoring"
emoji: "\\U0001f527"
color: blue
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
Test agent identity with background and expertise description.

## Mission
Test agent core mission statement here.

## Rules
1. Follow the rules strictly at all times.

## Deliverables
- Test deliverable format

## Workflow
1. Step one of the workflow.
"""


class TestScoreAgent:
    def test_returns_dict_with_score(self, tmp_path):
        f = tmp_path / "engineering" / "test.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(SAMPLE, encoding="utf-8")
        result = score_agent(f)
        assert isinstance(result, dict)
        assert "scores" in result
        assert 0 <= sum(result["scores"].values()) <= 10

    def test_has_required_detail_keys(self, tmp_path):
        f = tmp_path / "engineering" / "test2.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(SAMPLE, encoding="utf-8")
        result = score_agent(f)
        for key in ("content_depth", "structure", "frontmatter", "file_health"):
            assert key in result["scores"], f"Missing: {key}"


class TestHelpers:
    def test_frontmatter_ok(self):
        fm = get_frontmatter_text("---\nname: X\n---\nbody")
        assert "name: X" in fm

    def test_frontmatter_none(self):
        assert get_frontmatter_text("plain") == ""

    def test_body_ok(self):
        b = get_body("---\na: b\n---\n\nhello")
        assert "hello" in b

    def test_body_none(self):
        assert get_body("plain") == ""

    def test_get_field(self):
        assert get_field("name", "\nname: Z\ncolor: red\n") == "Z"

    def test_get_field_missing(self):
        assert get_field("x", "\nname: A\n") == ""
