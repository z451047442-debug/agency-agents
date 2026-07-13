"""Tests for missing coverage in batch-nexus-roles.py main() — lines 240-255, 277, 338, 346."""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _load_mod():
    spec = importlib.util.spec_from_file_location(
        "batch_nexus_roles2", str(SCRIPTS_DIR / "batch-nexus-roles.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod2 = _load_mod()
replace_nexus_roles = mod2.replace_nexus_roles


class TestReplaceNexusRoles:
    """Covers replace_nexus_roles (line 238-255)."""

    def test_strips_existing_nexus_block(self):
        fm = """name: "Test"
date_added: "2026-07-13"
nexus_roles:
  - phase-3-build
  - phase-4-hardening
color: blue"""
        result = replace_nexus_roles(fm, ["phase-0-discovery"])
        assert "nexus_roles:" in result
        assert "phase-0-discovery" in result
        assert "phase-3-build" not in result
        assert "phase-4-hardening" not in result
        assert "color: blue" in result


class TestMainCoverage:
    """Covers uncovered main() paths."""

    AGENT_BODY = """---
name: "Force Test Agent"
description: "Testing force mode"
emoji: "X"
color: blue
version: "1.0.0"
date_added: "2026-07-13"
nexus_roles:
  - phase-3-build
---

## Identity
Test.

## Mission
Test.

## Rules
Test.
"""

    AGENT_NO_ROLES = """---
name: "No Roles Agent"
description: "Agent without nexus_roles"
emoji: "X"
color: blue
version: "1.0.0"
date_added: "2026-07-13"
---

## Identity
Test.

## Mission
Test.

## Rules
Test.
"""

    def test_force_mode_overwrites(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod2, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir(parents=True)
        (tmp_path / "engineering/engineering-force-test.md").write_text(
            self.AGENT_BODY, encoding="utf-8")
        with patch.object(sys, "argv", [
            "batch-nexus-roles.py", "--force", "--category", "engineering"
        ]):
            mod2.main()
        content = (tmp_path / "engineering/engineering-force-test.md").read_text("utf-8")
        assert "nexus_roles:" in content

    def test_dry_run_verbose(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod2, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir(parents=True)
        (tmp_path / "engineering/engineering-no-roles.md").write_text(
            self.AGENT_NO_ROLES, encoding="utf-8")
        with patch.object(sys, "argv", [
            "batch-nexus-roles.py", "--dry-run", "--verbose"
        ]):
            mod2.main()
        assert "Assigned:" in capsys.readouterr().out

    def test_live_write_mode(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod2, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir(parents=True)
        agent_path = tmp_path / "engineering/engineering-no-roles.md"
        agent_path.write_text(self.AGENT_NO_ROLES, encoding="utf-8")
        with patch.object(sys, "argv", ["batch-nexus-roles.py"]):
            mod2.main()
        assert "nexus_roles:" in agent_path.read_text("utf-8")

    def test_unknown_category_returns_none(self):
        """Line 277: category not in ROLE_RULES or DEFAULT_BY_CATEGORY returns None."""
        result = mod2.assign_roles("some-unknown-agent", "nonexistent-category")
        assert result is None

    def test_for_else_no_pattern_matches(self, monkeypatch):
        """Line 277: for/else when no keyword matches and no None catch-all."""
        monkeypatch.setattr(mod2, "ROLE_RULES", {
            "test-cat": [(r"specific-only", ["phase-3-build"])],
        })
        result = mod2.assign_roles("no-match-agent", "test-cat")
        assert result == []

    def test_category_filter(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod2, "REPO", tmp_path)
        (tmp_path / "design").mkdir(parents=True)
        (tmp_path / "engineering").mkdir(parents=True)
        (tmp_path / "design/design-test.md").write_text(self.AGENT_NO_ROLES, encoding="utf-8")
        (tmp_path / "engineering/engineering-test.md").write_text(self.AGENT_NO_ROLES, encoding="utf-8")
        with patch.object(sys, "argv", ["batch-nexus-roles.py", "--category", "design"]):
            mod2.main()
        assert "nexus_roles:" in (tmp_path / "design/design-test.md").read_text("utf-8")
        assert "nexus_roles:" not in (tmp_path / "engineering/engineering-test.md").read_text("utf-8")
