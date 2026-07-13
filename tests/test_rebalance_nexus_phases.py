"""Tests for scripts/rebalance-nexus-phases.py — NEXUS phase rebalancer."""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _load_mod():
    spec = importlib.util.spec_from_file_location(
        "rebalance_nexus_phases", str(SCRIPTS_DIR / "rebalance-nexus-phases.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_mod()
matches = mod.matches
rebalance = mod.rebalance


class TestMatches:
    def test_matches_pattern(self):
        assert matches("engineering-test-automation", [r"test"])

    def test_no_match(self):
        assert not matches("engineering-frontend", [r"test", r"qa"])

    def test_case_insensitive(self):
        assert matches("engineering-QA-engineer", [r"qa"])

    def test_multiple_patterns_first_wins(self):
        assert matches("engineering-security-auditor", [r"test", r"security"])


AGENT_WITH_P4 = """---
name: "Test Builder"
description: "Builds things"
emoji: "X"
color: blue
version: "1.0.0"
date_added: "2026-07-13"
nexus_roles:
  - phase-3-build
  - phase-4-hardening
---

## Identity
Test agent.

## Mission
Test.

## Rules
Test.
"""

AGENT_WITHOUT_P4 = """---
name: "Test Researcher"
description: "Researches things"
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

AGENT_INFRA = """---
name: "Test Platform Engineer"
description: "Platform"
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


class TestRebalance:
    def test_dry_run_removes_p4(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir(parents=True)
        (tmp_path / "engineering/engineering-test-builder.md").write_text(
            AGENT_WITH_P4, encoding="utf-8")
        rebalance(dry_run=True)

    def test_dry_run_adds_p0_to_researcher(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        (tmp_path / "data-science").mkdir(parents=True)
        (tmp_path / "data-science/data-science-researcher.md").write_text(
            AGENT_WITHOUT_P4, encoding="utf-8")
        rebalance(dry_run=True)

    def test_dry_run_adds_p2_to_infra(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        (tmp_path / "infrastructure").mkdir(parents=True)
        (tmp_path / "infrastructure/infrastructure-platform-engineer.md").write_text(
            AGENT_INFRA, encoding="utf-8")
        rebalance(dry_run=True)

    def test_dry_run_skips_no_roles(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir(parents=True)
        content = """---
name: "No Roles"
description: "No nexus_roles"
emoji: "X"
color: blue
---

## Identity
Test.
## Mission
Test.
## Rules
Test.
"""
        (tmp_path / "engineering/engineering-no-roles.md").write_text(content, encoding="utf-8")
        rebalance(dry_run=True)

    def test_apply_removes_p4_from_non_keeper(self, tmp_path, monkeypatch):
        """Apply mode: remove P4 from agent NOT matching KEEP_P4."""
        monkeypatch.setattr(mod, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir(parents=True)
        # "builder" doesn't match KEEP_P4, so P4 should be removed
        agent_content = """---
name: "Widget Builder"
description: "Builds widgets"
emoji: "X"
color: blue
version: "1.0.0"
date_added: "2026-07-13"
nexus_roles:
  - phase-3-build
  - phase-4-hardening
---

## Identity
Test.
## Mission
Test.
## Rules
Test.
"""
        agent_path = tmp_path / "engineering/engineering-widget-builder.md"
        agent_path.write_text(agent_content, encoding="utf-8")
        rebalance(dry_run=False)
        content = agent_path.read_text(encoding="utf-8")
        assert "phase-4-hardening" not in content
        assert "phase-3-build" in content

    def test_apply_adds_p0_and_p2(self, tmp_path, monkeypatch):
        """Apply mode: add P0 to researcher and P2 to platform."""
        monkeypatch.setattr(mod, "REPO", tmp_path)
        (tmp_path / "data-science").mkdir(parents=True)
        (tmp_path / "infrastructure").mkdir(parents=True)

        ds_agent = """---
name: "Data Researcher"
description: "Researches data"
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
        (tmp_path / "data-science/data-science-researcher.md").write_text(ds_agent, encoding="utf-8")

        infra_agent = """---
name: "Platform Engineer"
description: "Platform"
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
        (tmp_path / "infrastructure/infrastructure-platform-engineer.md").write_text(infra_agent, encoding="utf-8")
        rebalance(dry_run=False)
        ds_content = (tmp_path / "data-science/data-science-researcher.md").read_text("utf-8")
        infra_content = (tmp_path / "infrastructure/infrastructure-platform-engineer.md").read_text("utf-8")
        assert "phase-0-discovery" in ds_content
        assert "phase-2-foundation" in infra_content

    def test_apply_writes_changes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir(parents=True)
        agent_path = tmp_path / "engineering/engineering-test-builder.md"
        agent_path.write_text(AGENT_WITH_P4, encoding="utf-8")
        rebalance(dry_run=False)
        content = agent_path.read_text(encoding="utf-8")


class TestMain:
    def test_main_dry_run_default(self, capsys):
        with patch.object(sys, "argv", ["rebalance-nexus-phases.py"]):
            mod.main()
        assert "DRY RUN" in capsys.readouterr().out

    def test_main_apply_flag(self, capsys):
        with patch.object(sys, "argv", ["rebalance-nexus-phases.py", "--apply"]):
            mod.main()
        assert "DRY RUN" not in capsys.readouterr().out
