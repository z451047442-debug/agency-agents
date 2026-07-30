"""Tests for scripts/match-nexus-agents.py — NEXUS agent matching."""
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
    "match_nexus_agents", str(SCRIPTS_DIR / "match-nexus-agents.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

tokenize = mod.tokenize
score_agent = mod.score_agent
build_roster = mod.build_roster
PHASE_LABELS = mod.PHASE_LABELS


# ---------------------------------------------------------------------------
# tokenize
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_removes_stopwords(self):
        tokens = tokenize("a project for the web application")
        assert "a" not in tokens
        assert "the" not in tokens
        assert "for" not in tokens
        assert "project" in tokens
        assert "web" in tokens
        assert "application" in tokens

    def test_filters_short_words(self):
        tokens = tokenize("we go to the web")
        assert "we" not in tokens
        assert "go" not in tokens
        assert "to" not in tokens
        assert "web" in tokens

    def test_empty_input(self):
        assert tokenize("") == []

    def test_stopwords_only(self):
        assert tokenize("the and for with") == []

    def test_keeps_meaningful_keywords(self):
        tokens = tokenize("build secure web application with kubernetes")
        assert "build" in tokens
        assert "secure" in tokens
        assert "web" in tokens
        assert "application" in tokens
        assert "kubernetes" in tokens
        assert "with" not in tokens


# ---------------------------------------------------------------------------
# score_agent
# ---------------------------------------------------------------------------

class TestScoreAgent:
    def test_matches_body(self, tmp_path):
        f = tmp_path / "agent.md"
        f.write_text(
            "---\nname: Tester\ndescription: Something\n---\n"
            "I perform security audits and code reviews for web applications.",
            encoding="utf-8",
        )
        score = score_agent(f, ["security", "web"])
        assert score == 2

    def test_matches_description(self, tmp_path):
        f = tmp_path / "agent.md"
        f.write_text(
            "---\nname: Tester\n"
            "description: This agent handles security and web development\n---\n"
            "Body content here.",
            encoding="utf-8",
        )
        score = score_agent(f, ["security", "web"])
        assert score == 2

    def test_no_frontmatter_returns_zero(self, tmp_path):
        f = tmp_path / "agent.md"
        f.write_text("plain text no frontmatter", encoding="utf-8")
        assert score_agent(f, ["security"]) == 0

    def test_no_matches_returns_zero(self, tmp_path):
        f = tmp_path / "agent.md"
        f.write_text(
            "---\nname: Tester\ndescription: Something completely unrelated\n---\n"
            "This has nothing to do with the keywords.",
            encoding="utf-8",
        )
        assert score_agent(f, ["security", "testing"]) == 0

    def test_missing_file_returns_zero(self, tmp_path):
        assert score_agent(tmp_path / "nonexistent.md", ["security"]) == 0


# ---------------------------------------------------------------------------
# build_roster
# ---------------------------------------------------------------------------

def _create_agent(dir_path: Path, agent_id: str, description: str,
                  body: str, nexus_roles: list[str]) -> Path:
    """Helper: write an agent .md file under dir_path."""
    roles_yaml = "\n".join(f"  - {r}" for r in nexus_roles)
    content = (
        f"---\nname: {agent_id}\n"
        f"description: {description}\n"
        f"nexus_roles:\n{roles_yaml}\n---\n{body}"
    )
    p = dir_path / f"{agent_id}.md"
    p.write_text(content, encoding="utf-8")
    return p


class TestBuildRoster:
    def test_empty_description_returns_empty_dict(self):
        roster = build_roster("")
        assert roster == {}

    def test_stopwords_only_returns_empty_dict(self):
        roster = build_roster("the and for with")
        assert roster == {}

    def test_keyword_matching_produces_results(self, tmp_path):
        eng = tmp_path / "engineering"
        eng.mkdir()
        _create_agent(
            eng, "engineering-security-tester",
            "Handles security testing and code reviews",
            "I perform security audits and code reviews for web applications.",
            ["phase-4-hardening"],
        )

        with patch("_shared.discovery.REPO", tmp_path):
            roster = build_roster("secure web application with authentication")

        assert roster, "Expected non-empty roster for matching keywords"
        # phase-4-hardening should contain our agent
        hardening = roster.get("phase-4-hardening", [])
        agent_ids = [e["agent_id"] for e in hardening]
        assert "engineering-security-tester" in agent_ids

    def test_multi_phase_agent_appears_in_multiple_phases(self, tmp_path):
        eng = tmp_path / "engineering"
        eng.mkdir()
        _create_agent(
            eng, "engineering-fullstack-dev",
            "Builds secure web apps",
            "I build web applications with security in mind.",
            ["phase-3-build", "phase-4-hardening"],
        )

        with patch("_shared.discovery.REPO", tmp_path):
            roster = build_roster("build web application secure")

        assert "phase-3-build" in roster
        assert "phase-4-hardening" in roster
        build_ids = [e["agent_id"] for e in roster["phase-3-build"]]
        harden_ids = [e["agent_id"] for e in roster["phase-4-hardening"]]
        assert "engineering-fullstack-dev" in build_ids
        assert "engineering-fullstack-dev" in harden_ids

    def test_respects_top5_limit(self, tmp_path):
        eng = tmp_path / "engineering"
        eng.mkdir()
        for i in range(10):
            _create_agent(
                eng, f"engineering-agent-{i:03d}",
                f"Security tester number {i}",
                f"Handles security testing and code reviews for project number {i}.",
                ["phase-4-hardening"],
            )

        with patch("_shared.discovery.REPO", tmp_path):
            roster = build_roster("security testing code review")

        hardening = roster.get("phase-4-hardening", [])
        assert len(hardening) <= 5, "Should return at most 5 agents per phase"

    def test_no_match_returns_empty_lists(self, tmp_path):
        eng = tmp_path / "engineering"
        eng.mkdir()
        _create_agent(
            eng, "engineering-astronomer",
            "Studies stars and galaxies",
            "I focus on astrophysics and celestial observations.",
            ["phase-0-discovery"],
        )

        with patch("_shared.discovery.REPO", tmp_path):
            roster = build_roster("secure web application")

        # All phases should be present as keys
        assert "phase-0-discovery" in roster
        # But the astronomer should not appear
        disco_ids = [e["agent_id"] for e in roster["phase-0-discovery"]]
        assert "engineering-astronomer" not in disco_ids


# ---------------------------------------------------------------------------
# Phase filtering
# ---------------------------------------------------------------------------

class TestPhaseFilter:
    def test_filter_to_single_phase(self, tmp_path):
        eng = tmp_path / "engineering"
        eng.mkdir()
        _create_agent(
            eng, "engineering-tester",
            "Testing agent",
            "I do security testing and code reviews.",
            ["phase-4-hardening", "phase-3-build"],
        )

        with patch("_shared.discovery.REPO", tmp_path):
            roster = build_roster("security testing", phase_filter="phase-4-hardening")

        assert "phase-4-hardening" in roster
        assert "phase-3-build" not in roster

    def test_phase_filter_returns_empty_when_no_match(self, tmp_path):
        eng = tmp_path / "engineering"
        eng.mkdir()
        _create_agent(
            eng, "engineering-dev",
            "Builds web applications",
            "I build web applications.",
            ["phase-3-build"],
        )

        with patch("_shared.discovery.REPO", tmp_path):
            roster = build_roster("secure web", phase_filter="phase-0-discovery")

        assert "phase-0-discovery" in roster
        assert roster["phase-0-discovery"] == []


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

class TestJsonOutput:
    def test_json_output_is_valid(self, tmp_path, capsys):
        eng = tmp_path / "engineering"
        eng.mkdir()
        _create_agent(
            eng, "engineering-dev",
            "Web application developer",
            "I build web applications with modern tools.",
            ["phase-3-build"],
        )

        with patch("_shared.discovery.REPO", tmp_path):
            with patch.object(
                sys, "argv",
                ["match-nexus-agents.py", "--project", "web application", "--json"],
            ):
                mod.main()

        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, dict)
        assert "phase-3-build" in data
        assert len(data["phase-3-build"]) > 0

    def test_json_with_phase_filter(self, tmp_path, capsys):
        eng = tmp_path / "engineering"
        eng.mkdir()
        _create_agent(
            eng, "engineering-tester",
            "Security tester",
            "I do security testing and code reviews.",
            ["phase-4-hardening", "phase-3-build"],
        )

        with patch("_shared.discovery.REPO", tmp_path):
            with patch.object(
                sys, "argv",
                [
                    "match-nexus-agents.py", "--project", "security testing",
                    "--json", "--phase", "phase-4-hardening",
                ],
            ):
                mod.main()

        data = json.loads(capsys.readouterr().out)
        assert "phase-4-hardening" in data
        assert "phase-3-build" not in data

    def test_json_empty_roster(self, tmp_path, capsys):
        with patch("_shared.discovery.REPO", tmp_path):
            with patch.object(
                sys, "argv",
                ["match-nexus-agents.py", "--project", "", "--json"],
            ):
                mod.main()

        data = json.loads(capsys.readouterr().out)
        assert data == {}


# ---------------------------------------------------------------------------
# main() — text output
# ---------------------------------------------------------------------------

class TestMain:
    def test_empty_project_shows_no_match_message(self, tmp_path, capsys):
        with patch("_shared.discovery.REPO", tmp_path):
            with patch.object(
                sys, "argv",
                ["match-nexus-agents.py", "--project", "xyzzynotfoundkeyword"],
            ):
                mod.main()

        out = capsys.readouterr().out
        assert "No matching agents found" in out
