"""Tests for scripts/rebalance-nexus-phases.py - NEXUS phase rebalancer."""
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


AGENT_WITH_P4 = chr(34)*3 + """---
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
""" + chr(34)*3


AGENT_WITHOUT_P4 = chr(34)*3 + """---
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
""" + chr(34)*3


AGENT_INFRA = chr(34)*3 + """---
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
""" + chr(34)*3


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
        monkeypatch.setattr(mod, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir(parents=True)
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


_TEST_AGENT_BUILDER = """---
name: "Builder"
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
Test.
## Mission
Test.
## Rules
Test.
"""


_TEST_AGENT_RESEARCHER = """---
name: "Researcher"
description: "Researches things"
emoji: "X"
color: blue
version: "1.0.0"
date_added: "2026-07-13"
nexus_roles:
  - phase-0-discovery
  - phase-1-strategy
---

## Identity
Test.
## Mission
Test.
## Rules
Test.
"""


_ALL_PHASES = {
    "phase-0-discovery": {"count": 0, "agents": [], "scores": []},
    "phase-1-strategy": {"count": 0, "agents": [], "scores": []},
    "phase-2-foundation": {"count": 0, "agents": [], "scores": []},
    "phase-3-build": {"count": 0, "agents": [], "scores": []},
    "phase-4-hardening": {"count": 0, "agents": [], "scores": []},
    "phase-5-launch": {"count": 0, "agents": [], "scores": []},
    "phase-6-operate": {"count": 0, "agents": [], "scores": []},
}


import _shared


class TestPhaseDistribution:
    def test_counts_phases_from_agent_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir()
        f = tmp_path / "engineering/engineering-builder.md"
        f.write_text(_TEST_AGENT_BUILDER, encoding="utf-8")
        monkeypatch.setattr(
            _shared, "discover_agents",
            lambda **kw: iter([("engineering", "engineering/engineering-builder.md", f)])
        )
        monkeypatch.setattr(_shared, "get_score_agent",
                            lambda: lambda fp, **kw: {"total": 7.5})
        result = mod.phase_distribution()
        assert result["phase-3-build"]["count"] == 1
        assert result["phase-4-hardening"]["count"] == 1
        assert result["phase-0-discovery"]["count"] == 0

    def test_multiple_agents_across_phases(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir()
        (tmp_path / "data-science").mkdir()
        f1 = tmp_path / "engineering/engineering-builder.md"
        f1.write_text(_TEST_AGENT_BUILDER, encoding="utf-8")
        f2 = tmp_path / "data-science/data-science-researcher.md"
        f2.write_text(_TEST_AGENT_RESEARCHER, encoding="utf-8")
        monkeypatch.setattr(
            _shared, "discover_agents",
            lambda **kw: iter([
                ("engineering", "engineering/engineering-builder.md", f1),
                ("data-science", "data-science/data-science-researcher.md", f2),
            ])
        )
        monkeypatch.setattr(_shared, "get_score_agent",
                            lambda: lambda fp, **kw: {"total": 8.0})
        result = mod.phase_distribution()
        assert result["phase-3-build"]["count"] == 1
        assert result["phase-4-hardening"]["count"] == 1
        assert result["phase-0-discovery"]["count"] == 1
        assert result["phase-1-strategy"]["count"] == 1

    def test_collects_scores_per_phase(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "REPO", tmp_path)
        (tmp_path / "engineering").mkdir()
        f = tmp_path / "engineering/engineering-builder.md"
        f.write_text(_TEST_AGENT_BUILDER, encoding="utf-8")
        monkeypatch.setattr(
            _shared, "discover_agents",
            lambda **kw: iter([("engineering", "engineering/engineering-builder.md", f)])
        )
        monkeypatch.setattr(_shared, "get_score_agent",
                            lambda: lambda fp, **kw: {"total": 9.2})
        result = mod.phase_distribution()
        assert result["phase-3-build"]["scores"] == [9.2]
        assert result["phase-4-hardening"]["scores"] == [9.2]

    def test_skips_agents_without_nexus_roles(self, tmp_path, monkeypatch):
        no_role = """---
name: "No Role"
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
        monkeypatch.setattr(mod, "REPO", tmp_path)
        (tmp_path / "general").mkdir()
        f = tmp_path / "general/general-no-role.md"
        f.write_text(no_role, encoding="utf-8")
        monkeypatch.setattr(
            _shared, "discover_agents",
            lambda **kw: iter([("general", "general/general-no-role.md", f)])
        )
        monkeypatch.setattr(_shared, "get_score_agent",
                            lambda: lambda fp, **kw: {"total": 5.0})
        result = mod.phase_distribution()
        for phase, data in result.items():
            assert data["count"] == 0


class TestPrintPhaseReport:
    def test_prints_report_header_and_phases(self, capsys):
        phases = dict(_ALL_PHASES)
        phases["phase-3-build"] = {"count": 40, "agents": [], "scores": [7.0] * 40}
        phases["phase-4-hardening"] = {"count": 20, "agents": [], "scores": [6.5] * 20}
        mod.print_phase_report(phases)
        out = capsys.readouterr().out
        assert "NEXUS Phase Balance Report" in out
        assert "Build" in out
        assert "Hardening" in out
        assert "Build→Hardening ratio" in out

    def test_bottleneck_flag_when_ratio_gt_3(self, capsys):
        phases = dict(_ALL_PHASES)
        phases["phase-3-build"] = {"count": 100, "agents": [], "scores": [7.0]}
        phases["phase-4-hardening"] = {"count": 10, "agents": [], "scores": [6.5]}
        mod.print_phase_report(phases)
        assert "BOTTLENECK" in capsys.readouterr().out

    def test_no_bottleneck_when_ratio_ok(self, capsys):
        phases = dict(_ALL_PHASES)
        phases["phase-3-build"] = {"count": 30, "agents": [], "scores": [7.0]}
        phases["phase-4-hardening"] = {"count": 20, "agents": [], "scores": [6.5]}
        mod.print_phase_report(phases)
        assert "BOTTLENECK" not in capsys.readouterr().out

    def test_empty_all_phases(self, capsys):
        mod.print_phase_report(_ALL_PHASES)
        out = capsys.readouterr().out
        assert "NEXUS Phase Balance Report" in out
        assert "Build→Hardening" not in out

    def test_high_pct_shows_double_exclamation(self, capsys):
        phases = dict(_ALL_PHASES)
        phases["phase-3-build"] = {"count": 80, "agents": [], "scores": [7.0]}
        mod.print_phase_report(phases)
        assert "!!" in capsys.readouterr().out

    def test_low_pct_shows_dash(self, capsys):
        phases = dict(_ALL_PHASES)
        phases["phase-0-discovery"] = {"count": 2, "agents": [], "scores": [7.0]}
        phases["phase-3-build"] = {"count": 98, "agents": [], "scores": [7.0]}
        mod.print_phase_report(phases)
        assert " -" in capsys.readouterr().out

    def test_average_score_displayed(self, capsys):
        phases = dict(_ALL_PHASES)
        phases["phase-3-build"] = {"count": 10, "agents": [], "scores": [8.0, 9.0, 7.0]}
        mod.print_phase_report(phases)
        assert "avg score 8.0" in capsys.readouterr().out


class TestMain:
    def test_main_dry_run_default(self, capsys):
        with patch.object(sys, "argv", ["rebalance-nexus-phases.py"]):
            mod.main()
        assert "DRY RUN" in capsys.readouterr().out

    def test_main_apply_flag(self, capsys):
        with patch.object(sys, "argv", ["rebalance-nexus-phases.py", "--apply"]):
            mod.main()
        assert "DRY RUN" not in capsys.readouterr().out

    def test_main_report_flag(self, monkeypatch, capsys):
        monkeypatch.setattr(mod, "phase_distribution", lambda: dict(_ALL_PHASES))
        with patch.object(sys, "argv", ["rebalance-nexus-phases.py", "--report"]):
            mod.main()
        out = capsys.readouterr().out
        assert "NEXUS Phase Balance Report" in out
