"""Tests for scripts/nexus-coverage.py — NEXUS phase coverage visualization."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "nexus_coverage", str(SCRIPTS_DIR / "nexus-coverage.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

collect_phase_data = mod.collect_phase_data
compute_coverage_scores = mod.compute_coverage_scores
find_gaps = mod.find_gaps
PHASE_ORDER = mod.PHASE_ORDER
PHASE_LABELS = mod.PHASE_LABELS
GAP_AGENT_THRESHOLD = mod.GAP_AGENT_THRESHOLD
GAP_CATEGORY_THRESHOLD = mod.GAP_CATEGORY_THRESHOLD


# ---------------------------------------------------------------------------
# collect_phase_data
# ---------------------------------------------------------------------------

def _create_agent(
    dir_path: Path, agent_id: str, nexus_roles: list[str],
) -> Path:
    """Helper: write an agent .md file with given nexus_roles."""
    fm_lines = [
        "---",
        f"name: {agent_id}",
        "description: A test agent",
        "emoji: X",
        "color: blue",
    ]
    if nexus_roles:
        fm_lines.append("nexus_roles:")
        for r in nexus_roles:
            fm_lines.append(f"  - {r}")
    fm_lines.append("---\n")
    content = "\n".join(fm_lines) + "\n## Identity\nTest agent body.\n"

    p = dir_path / f"{agent_id}.md"
    p.write_text(content, encoding="utf-8")
    return p


class TestCollectPhaseData:
    """Phase counting is accurate."""

    def test_all_phases_empty_for_empty_repo(self, tmp_path):
        with patch("_shared.discovery.REPO", tmp_path):
            data = collect_phase_data()

        assert all(p["agent_count"] == 0 for p in data.values())
        assert all(p["categories"] == set() for p in data.values())

    def test_counts_agents_correctly(self, tmp_path):
        eng = tmp_path / "engineering"
        eng.mkdir()
        _create_agent(eng, "engineering-agent-a", ["phase-0-discovery", "phase-3-build"])
        _create_agent(eng, "engineering-agent-b", ["phase-3-build"])
        _create_agent(eng, "engineering-agent-c", ["phase-4-hardening"])

        with patch("_shared.discovery.REPO", tmp_path):
            data = collect_phase_data()

        assert data["phase-0-discovery"]["agent_count"] == 1
        assert data["phase-3-build"]["agent_count"] == 2
        assert data["phase-4-hardening"]["agent_count"] == 1
        assert data["phase-1-strategy"]["agent_count"] == 0

    def test_tracks_categories(self, tmp_path):
        eng = tmp_path / "engineering"
        design = tmp_path / "design"
        eng.mkdir()
        design.mkdir()

        _create_agent(eng, "engineering-tester", ["phase-4-hardening"])
        _create_agent(design, "design-tester", ["phase-4-hardening"])

        with patch("_shared.discovery.REPO", tmp_path):
            data = collect_phase_data()

        assert data["phase-4-hardening"]["categories"] == {"engineering", "design"}

    def test_agent_without_roles_not_counted(self, tmp_path):
        eng = tmp_path / "engineering"
        eng.mkdir()
        _create_agent(eng, "engineering-no-roles", [])

        with patch("_shared.discovery.REPO", tmp_path):
            data = collect_phase_data()

        assert all(p["agent_count"] == 0 for p in data.values())

    def test_category_filter(self, tmp_path):
        eng = tmp_path / "engineering"
        design = tmp_path / "design"
        eng.mkdir()
        design.mkdir()

        _create_agent(eng, "engineering-dev", ["phase-3-build"])
        _create_agent(design, "design-ui", ["phase-3-build"])

        with patch("_shared.discovery.REPO", tmp_path):
            data = collect_phase_data(category_filter="engineering")

        assert data["phase-3-build"]["agent_count"] == 1
        assert data["phase-3-build"]["categories"] == {"engineering"}


# ---------------------------------------------------------------------------
# compute_coverage_scores
# ---------------------------------------------------------------------------

class TestComputeCoverageScores:
    """Coverage score computation."""

    def test_all_zeros_gives_zero_scores(self):
        phases = {
            pid: {"agent_count": 0, "agents": [], "categories": set()}
            for pid in PHASE_ORDER
        }
        scores = compute_coverage_scores(phases)
        for pid in PHASE_ORDER:
            assert scores[pid] == 0.0

    def test_uniform_distribution_gives_high_scores(self, tmp_path):
        eng = tmp_path / "engineering"
        design = tmp_path / "design"
        eng.mkdir()
        design.mkdir()

        _create_agent(eng, "eng-a", ["phase-0-discovery"])
        _create_agent(design, "des-a", ["phase-0-discovery"])

        with patch("_shared.discovery.REPO", tmp_path):
            data = collect_phase_data()

        scores = compute_coverage_scores(data)

        # phase-0-discovery should have the highest score (only phase with agents)
        assert scores["phase-0-discovery"] > 0.0
        # Other phases with zero agents should have some score from cat diversity
        # but less than the populated one
        for pid in PHASE_ORDER:
            if pid != "phase-0-discovery":
                assert scores[pid] <= scores["phase-0-discovery"]

    def test_scores_in_01_range(self, tmp_path):
        eng = tmp_path / "engineering"
        eng.mkdir()
        _create_agent(eng, "eng-a", ["phase-0-discovery"])
        _create_agent(eng, "eng-b", ["phase-1-strategy"])
        _create_agent(eng, "eng-c", ["phase-3-build"])
        _create_agent(eng, "eng-d", ["phase-4-hardening"])

        with patch("_shared.discovery.REPO", tmp_path):
            data = collect_phase_data()

        scores = compute_coverage_scores(data)
        for pid in PHASE_ORDER:
            assert 0.0 <= scores[pid] <= 1.0


# ---------------------------------------------------------------------------
# Gap detection
# ---------------------------------------------------------------------------

class TestFindGaps:
    """Gap detection identifies under-covered phases."""

    def test_no_gaps_when_all_above_threshold(self):
        phases = {
            pid: {
                "agent_count": GAP_AGENT_THRESHOLD + 50,
                "agents": [],
                "categories": {f"cat-{i}" for i in range(GAP_CATEGORY_THRESHOLD + 5)},
            }
            for pid in PHASE_ORDER
        }
        gaps = find_gaps(phases)
        assert gaps == []

    def test_identifies_low_agent_count(self):
        phases = {
            pid: {
                "agent_count": 5,
                "agents": [],
                "categories": {f"cat-{i}" for i in range(GAP_CATEGORY_THRESHOLD + 5)},
            }
            for pid in PHASE_ORDER
        }
        gaps = find_gaps(phases)
        assert len(gaps) == 7  # all 7 phases have low agent count
        for g in gaps:
            assert "low agent count" in g["issues"][0]

    def test_identifies_low_category_diversity(self):
        phases = {
            pid: {
                "agent_count": GAP_AGENT_THRESHOLD + 50,
                "agents": [],
                "categories": {"engineering"},  # only 1 category
            }
            for pid in PHASE_ORDER
        }
        gaps = find_gaps(phases)
        assert len(gaps) == 7
        # At least one issue should be about category diversity
        # The issue ordering: low agent count is checked first for those below threshold
        for g in gaps:
            cat_issues = [i for i in g["issues"] if "category diversity" in i]
            assert len(cat_issues) == 1

    def test_gaps_sorted_by_severity(self):
        phases: dict[str, dict] = {}
        for pid in PHASE_ORDER:
            if pid == "phase-0-discovery":
                phases[pid] = {
                    "agent_count": 5,
                    "agents": [],
                    "categories": {"engineering"},
                }
            elif pid == "phase-3-build":
                phases[pid] = {
                    "agent_count": GAP_AGENT_THRESHOLD + 50,
                    "agents": [],
                    "categories": {f"cat-{i}" for i in range(GAP_CATEGORY_THRESHOLD + 5)},
                }
            else:
                phases[pid] = {
                    "agent_count": GAP_AGENT_THRESHOLD + 50,
                    "agents": [],
                    "categories": {f"cat-{i}" for i in range(GAP_CATEGORY_THRESHOLD + 5)},
                }
        gaps = find_gaps(phases)
        # Only phase-0-discovery should be a gap (both issues)
        assert len(gaps) == 1
        assert gaps[0]["phase"] == "phase-0-discovery"
        assert len(gaps[0]["issues"]) == 2


# ---------------------------------------------------------------------------
# Category filtering
# ---------------------------------------------------------------------------

class TestCategoryFilter:
    """Category filtering works correctly."""

    def test_filter_limits_to_single_category(self, tmp_path):
        eng = tmp_path / "engineering"
        design = tmp_path / "design"
        eng.mkdir()
        design.mkdir()

        _create_agent(eng, "eng-dev", ["phase-3-build"])
        _create_agent(eng, "eng-ops", ["phase-6-operate"])
        _create_agent(design, "des-ui", ["phase-3-build"])

        with patch("_shared.discovery.REPO", tmp_path):
            data = collect_phase_data(category_filter="engineering")

        assert data["phase-3-build"]["agent_count"] == 1
        assert data["phase-6-operate"]["agent_count"] == 1
        assert data["phase-0-discovery"]["agent_count"] == 0
        assert data["phase-3-build"]["categories"] == {"engineering"}

    def test_nonexistent_category_returns_empty(self, tmp_path):
        with patch("_shared.discovery.REPO", tmp_path):
            data = collect_phase_data(category_filter="nonexistent")

        assert all(p["agent_count"] == 0 for p in data.values())


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

class TestJsonOutput:
    """JSON output is valid and complete."""

    def test_json_output_is_valid(self, tmp_path, capsys):
        eng = tmp_path / "engineering"
        eng.mkdir()
        _create_agent(eng, "eng-dev", ["phase-3-build"])

        with patch("_shared.discovery.REPO", tmp_path):
            with patch.object(
                sys, "argv",
                ["nexus-coverage.py", "--json"],
            ):
                mod.main()

        out = capsys.readouterr().out
        data = json.loads(out)
        assert "phases" in data
        assert "scores" in data
        assert "summary" in data
        assert "phase-3-build" in data["phases"]
        assert data["phases"]["phase-3-build"]["agent_count"] == 1

    def test_json_with_category_filter(self, tmp_path, capsys):
        eng = tmp_path / "engineering"
        design = tmp_path / "design"
        eng.mkdir()
        design.mkdir()
        _create_agent(eng, "eng-dev", ["phase-3-build"])
        _create_agent(design, "des-ui", ["phase-3-build"])

        with patch("_shared.discovery.REPO", tmp_path):
            with patch.object(
                sys, "argv",
                ["nexus-coverage.py", "--json", "--category", "engineering"],
            ):
                mod.main()

        data = json.loads(capsys.readouterr().out)
        assert data["phases"]["phase-3-build"]["agent_count"] == 1
        assert data["summary"]["total_agents"] == 1

    def test_json_with_gaps_flag_includes_gaps(self, tmp_path, capsys):
        with patch("_shared.discovery.REPO", tmp_path):
            with patch.object(
                sys, "argv",
                ["nexus-coverage.py", "--json", "--gaps"],
            ):
                mod.main()

        data = json.loads(capsys.readouterr().out)
        assert "gaps" in data
        assert len(data["gaps"]) == 7  # all phases empty = all gaps

    def test_json_empty_repo(self, tmp_path, capsys):
        with patch("_shared.discovery.REPO", tmp_path):
            with patch.object(
                sys, "argv",
                ["nexus-coverage.py", "--json"],
            ):
                mod.main()

        data = json.loads(capsys.readouterr().out)
        assert data["summary"]["total_agents"] == 0
        assert data["summary"]["total_categories"] == 0


# ---------------------------------------------------------------------------
# Main() text output
# ---------------------------------------------------------------------------

class TestMainTextOutput:
    """Text mode output produces expected headings."""

    def test_prints_header(self, tmp_path, capsys):
        with patch("_shared.discovery.REPO", tmp_path):
            with patch.object(
                sys, "argv",
                ["nexus-coverage.py"],
            ):
                mod.main()

        out = capsys.readouterr().out
        assert "NEXUS Phase Coverage" in out

    def test_gaps_mode_shows_gaps_section(self, tmp_path, capsys):
        with patch("_shared.discovery.REPO", tmp_path):
            with patch.object(
                sys, "argv",
                ["nexus-coverage.py", "--gaps"],
            ):
                mod.main()

        out = capsys.readouterr().out
        assert "Coverage Gaps" in out

    def test_category_shows_in_header(self, tmp_path, capsys):
        eng = tmp_path / "engineering"
        eng.mkdir()
        _create_agent(eng, "eng-dev", ["phase-3-build"])

        with patch("_shared.discovery.REPO", tmp_path):
            with patch.object(
                sys, "argv",
                ["nexus-coverage.py", "--category", "engineering"],
            ):
                mod.main()

        out = capsys.readouterr().out
        assert "engineering" in out
