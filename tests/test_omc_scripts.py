"""Tests for OMC integration scripts (5 scripts, target 80%+ coverage)."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# ── Test data ──────────────────────────────────────────────────────────────────

SAMPLE_AGENTS = [
    {
        "id": "engineering-backend-architect", "name": "Backend Architect",
        "description": "API design, database architecture expert for scalable systems",
        "category": "engineering", "path": "engineering/engineering-backend-architect.md",
        "nexus_roles": ["phase-1-strategy", "phase-3-build"],
        "depends_on": ["engineering-frontend-developer"],
    },
    {
        "id": "engineering-frontend-developer", "name": "Frontend Developer",
        "description": "React/Vue/Angular UI implementation and performance optimization",
        "category": "engineering", "path": "engineering/engineering-frontend-developer.md",
        "nexus_roles": ["phase-3-build"],
        "depends_on": [],
    },
    {
        "id": "aerospace-avionics", "name": "Avionics Engineer",
        "description": "Avionics system design and certification for flight management",
        "category": "aerospace", "path": "aerospace/aerospace-avionics.md",
        "nexus_roles": ["phase-3-build"],
        "depends_on": ["aerospace-atc-specialist"],
    },
    {
        "id": "cybersecurity-security-architect", "name": "Security Architect",
        "description": "Enterprise security architecture, zero trust, IAM, data protection",
        "category": "cybersecurity", "path": "cybersecurity/cybersecurity-security-architect.md",
        "nexus_roles": ["phase-1-strategy", "phase-4-hardening"],
        "depends_on": [],
    },
    {
        "id": "healthcare-clinical-pharmacist", "name": "Clinical Pharmacist",
        "description": "Clinical pharmacy expert for drug interactions and therapeutic monitoring",
        "category": "healthcare", "path": "healthcare/healthcare-clinical-pharmacist.md",
        "nexus_roles": [],
        "depends_on": [],
    },
]

SAMPLE_SCORES = {
    "engineering-backend-architect": 13.0,
    "engineering-frontend-developer": 11.0,
    "aerospace-avionics": 9.5,
    "cybersecurity-security-architect": 12.5,
    "healthcare-clinical-pharmacist": 7.0,
}

SAMPLE_RISKS = {
    "engineering-backend-architect": "general",
    "engineering-frontend-developer": "general",
    "aerospace-avionics": "high",
    "cybersecurity-security-architect": "critical",
    "healthcare-clinical-pharmacist": "general",
}

# ── Shared loader ─────────────────────────────────────────────────────────────

def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, str(SCRIPTS_DIR / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── export-omc-agents.py ──────────────────────────────────────────────────────

export_mod = _load_script("export-omc-agents")


class TestGradeLabel:
    def test_grade_a(self):
        assert export_mod.grade_label(13.0) == "A"
    def test_grade_b(self):
        assert export_mod.grade_label(10.5) == "B"
    def test_grade_c(self):
        assert export_mod.grade_label(8.5) == "C"
    def test_grade_d(self):
        assert export_mod.grade_label(5.0) == "D"
    def test_boundary_a_b(self):
        assert export_mod.grade_label(12.5) == "A"
        assert export_mod.grade_label(12.4) == "B"
    def test_boundary_b_c(self):
        assert export_mod.grade_label(10.0) == "B"
        assert export_mod.grade_label(9.9) == "C"


class TestExportAgents:
    def test_filter_by_score(self, tmp_path):
        count, exported = export_mod.export_agents(
            SAMPLE_AGENTS, SAMPLE_SCORES, tmp_path,
            min_score=10.0, categories=None, dry_run=True,
        )
        ids = {a["id"] for a in exported}
        assert ids == {"engineering-backend-architect", "engineering-frontend-developer",
                       "cybersecurity-security-architect"}

    def test_filter_by_category(self, tmp_path):
        count, exported = export_mod.export_agents(
            SAMPLE_AGENTS, SAMPLE_SCORES, tmp_path,
            min_score=0.0, categories={"aerospace"}, dry_run=True,
        )
        assert count == 1
        assert exported[0]["id"] == "aerospace-avionics"

    def test_filter_by_score_and_category(self, tmp_path):
        count, exported = export_mod.export_agents(
            SAMPLE_AGENTS, SAMPLE_SCORES, tmp_path,
            min_score=9.0, categories={"engineering"}, dry_run=True,
        )
        assert count == 2

    def test_export_includes_score_and_grade(self, tmp_path):
        _, exported = export_mod.export_agents(
            SAMPLE_AGENTS, SAMPLE_SCORES, tmp_path,
            min_score=0.0, categories=None, dry_run=True,
        )
        for a in exported:
            assert "score" in a
            assert "grade" in a
            assert a["grade"] in ("A", "B", "C", "D")

    def test_missing_score_defaults_to_zero(self, tmp_path):
        scores = {"engineering-backend-architect": 13.0}
        count, _ = export_mod.export_agents(
            SAMPLE_AGENTS, scores, tmp_path,
            min_score=10.0, categories=None, dry_run=True,
        )
        assert count == 1

    def test_source_missing_skipped(self, tmp_path):
        agents = [{**SAMPLE_AGENTS[0], "path": "nonexistent/agent.md"}]
        scores = {"engineering-backend-architect": 13.0}
        count, _ = export_mod.export_agents(
            agents, scores, tmp_path, min_score=0.0, categories=None, dry_run=False,
        )
        assert count == 0

    def test_dry_run_writes_nothing(self, tmp_path):
        export_mod.export_agents(
            SAMPLE_AGENTS, SAMPLE_SCORES, tmp_path,
            min_score=0.0, categories=None, dry_run=True,
        )
        assert not list(tmp_path.glob("*.md"))


class TestWriteIndex:
    def test_writes_valid_json(self, tmp_path):
        exported = [{**a, "score": 10.0, "grade": "B"} for a in SAMPLE_AGENTS[:2]]
        export_mod.write_index(exported, tmp_path)
        data = json.loads((tmp_path / "AGENTS.json").read_text(encoding="utf-8"))
        assert data["total"] == 2
        assert data["version"] == "1.0"
        assert "source" in data
        assert data["agents"][0]["score"] == 10.0
        assert data["agents"][0]["grade"] == "B"


class TestVerifyExport:
    def test_missing_index(self, tmp_path):
        assert export_mod.verify_export(tmp_path) is False

    def test_valid_export(self, tmp_path):
        (tmp_path / "test-agent.md").write_text("content")
        exported = [{**SAMPLE_AGENTS[0], "score": 10.0, "grade": "B", "id": "test-agent"}]
        export_mod.write_index(exported, tmp_path)
        assert export_mod.verify_export(tmp_path) is True

    def test_orphan_file(self, tmp_path):
        (tmp_path / "orphan.md").write_text("content")
        exported = [{**SAMPLE_AGENTS[0], "score": 10.0, "grade": "B"}]
        export_mod.write_index(exported, tmp_path)
        assert export_mod.verify_export(tmp_path) is False

    def test_missing_file(self, tmp_path):
        # index references agent but no file on disk
        exported = [{**SAMPLE_AGENTS[0], "score": 10.0, "grade": "B"}]
        export_mod.write_index(exported, tmp_path)
        assert export_mod.verify_export(tmp_path) is False


# ── generate-nexus-skills.py ──────────────────────────────────────────────────

nexus_mod = _load_script("generate-nexus-skills")


class TestAgentsForPhase:
    def test_phase_3_build(self):
        result = nexus_mod.agents_for_phase(SAMPLE_AGENTS, "3")
        ids = {a["id"] for a in result}
        assert ids == {"engineering-backend-architect", "engineering-frontend-developer",
                       "aerospace-avionics"}

    def test_phase_4_hardening(self):
        result = nexus_mod.agents_for_phase(SAMPLE_AGENTS, "4")
        assert len(result) == 1
        assert result[0]["id"] == "cybersecurity-security-architect"

    def test_empty_phase(self):
        result = nexus_mod.agents_for_phase(SAMPLE_AGENTS, "6")
        assert result == []

    def test_agent_without_nexus_roles_excluded(self):
        result = nexus_mod.agents_for_phase(SAMPLE_AGENTS, "3")
        ids = {a["id"] for a in result}
        assert "healthcare-clinical-pharmacist" not in ids


class TestBuildSkillMd:
    def test_includes_phase_info(self):
        md = nexus_mod.build_skill_md("3", SAMPLE_AGENTS)
        assert "NEXUS Phase 3: Build" in md
        assert "argument-hint" in md
        assert "Quality Gate" in md

    def test_includes_agent_count(self):
        md = nexus_mod.build_skill_md("3", SAMPLE_AGENTS)
        assert "**3 agents**" in md

    def test_includes_gate_questions(self):
        md = nexus_mod.build_skill_md("3", SAMPLE_AGENTS)
        assert "All tasks pass QA?" in md

    def test_includes_triggers(self):
        md = nexus_mod.build_skill_md("3", SAMPLE_AGENTS)
        assert "`build`" in md

    def test_frontmatter_has_argument_hint(self):
        md = nexus_mod.build_skill_md("0", SAMPLE_AGENTS)
        assert "argument-hint:" in md
        assert "name: nexus-discover" in md


class TestGeneratePhase:
    def test_writes_skill_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(nexus_mod, "OUT_DIR", tmp_path)
        nexus_mod.generate_phase("3", SAMPLE_AGENTS, check=False)
        skill_path = tmp_path / "nexus-build" / "SKILL.md"
        assert skill_path.exists()

    def test_check_detects_ok(self, tmp_path, monkeypatch):
        monkeypatch.setattr(nexus_mod, "OUT_DIR", tmp_path)
        nexus_mod.generate_phase("3", SAMPLE_AGENTS, check=False)
        assert nexus_mod.generate_phase("3", SAMPLE_AGENTS, check=True) is True

    def test_check_detects_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(nexus_mod, "OUT_DIR", tmp_path)
        assert nexus_mod.generate_phase("3", SAMPLE_AGENTS, check=True) is False

    def test_returns_true(self, tmp_path, monkeypatch):
        monkeypatch.setattr(nexus_mod, "OUT_DIR", tmp_path)
        assert nexus_mod.generate_phase("3", SAMPLE_AGENTS, check=False) is True


class TestGenerateFull:
    def test_writes_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(nexus_mod, "OUT_DIR", tmp_path)
        nexus_mod.generate_full(SAMPLE_AGENTS, check=False)
        content = (tmp_path / "nexus-full" / "SKILL.md").read_text(encoding="utf-8")
        assert "NEXUS Full Pipeline" in content

    def test_has_phase_summary_table(self, tmp_path, monkeypatch):
        monkeypatch.setattr(nexus_mod, "OUT_DIR", tmp_path)
        nexus_mod.generate_full(SAMPLE_AGENTS, check=False)
        content = (tmp_path / "nexus-full" / "SKILL.md").read_text(encoding="utf-8")
        assert "| Phase" in content
        assert "| Agents |" in content


# ── generate-omc-model-routing.py ─────────────────────────────────────────────

routing_mod = _load_script("generate-omc-model-routing")


class TestAssignTier:
    def test_opus_a_grade(self):
        assert routing_mod.assign_tier(13.0, "general") == "opus"
    def test_opus_critical_bumps(self):
        assert routing_mod.assign_tier(11.5, "critical") == "opus"
    def test_sonnet_b_grade(self):
        assert routing_mod.assign_tier(10.5, "general") == "sonnet"
    def test_sonnet_high_bumps(self):
        assert routing_mod.assign_tier(9.5, "high") == "sonnet"
    def test_haiku_low(self):
        assert routing_mod.assign_tier(5.0, "general") == "haiku"
    def test_opus_boundary(self):
        assert routing_mod.assign_tier(12.5, "general") == "opus"
    def test_sonnet_boundary(self):
        assert routing_mod.assign_tier(10.0, "general") == "sonnet"


class TestGenerateRouting:
    def test_all_agents_routed(self):
        routing = routing_mod.generate_routing(SAMPLE_SCORES, SAMPLE_RISKS, SAMPLE_AGENTS)
        assert len(routing) == 5

    def test_has_required_fields(self):
        routing = routing_mod.generate_routing(SAMPLE_SCORES, SAMPLE_RISKS, SAMPLE_AGENTS)
        for entry in routing.values():
            for field in ("tier", "score", "risk", "category", "description"):
                assert field in entry

    def test_security_architect_opus(self):
        routing = routing_mod.generate_routing(SAMPLE_SCORES, SAMPLE_RISKS, SAMPLE_AGENTS)
        assert routing["cybersecurity-security-architect"]["tier"] == "opus"

    def test_avionics_high_risk_sonnet(self):
        routing = routing_mod.generate_routing(SAMPLE_SCORES, SAMPLE_RISKS, SAMPLE_AGENTS)
        assert routing["aerospace-avionics"]["tier"] == "sonnet"

    def test_pharmacist_haiku(self):
        routing = routing_mod.generate_routing(SAMPLE_SCORES, SAMPLE_RISKS, SAMPLE_AGENTS)
        assert routing["healthcare-clinical-pharmacist"]["tier"] == "haiku"


# ── generate-omc-hooks.py ─────────────────────────────────────────────────────

hooks_mod = _load_script("generate-omc-hooks")


class TestExtractKeywords:
    def test_extracts_words(self):
        result = hooks_mod.extract_keywords("API design database architecture")
        assert "api" in result
        assert "design" in result
        assert "database" in result
        assert "architecture" in result

    def test_filters_stop_words(self):
        result = hooks_mod.extract_keywords("the and for with in on at")
        assert result == set()

    def test_filters_short_words(self):
        result = hooks_mod.extract_keywords("an is us go")
        assert len(result) == 0


class TestBuildTermMap:
    def test_maps_keywords_to_agents(self):
        term_map = hooks_mod.build_term_map(SAMPLE_AGENTS)
        assert "architecture" in term_map

    def test_security_keyword_maps(self):
        term_map = hooks_mod.build_term_map(SAMPLE_AGENTS)
        assert "security" in term_map
        ids = {a["id"] for a in term_map["security"]}
        assert "cybersecurity-security-architect" in ids


class TestBuildTriggers:
    def test_filters_single_agent(self):
        term_map = hooks_mod.build_term_map(SAMPLE_AGENTS)
        triggers = hooks_mod.build_triggers(term_map, top=None)
        for t in triggers:
            assert t["agent_count"] >= 2

    def test_sorts_by_priority(self):
        term_map = hooks_mod.build_term_map(SAMPLE_AGENTS)
        triggers = hooks_mod.build_triggers(term_map, top=None)
        for i in range(len(triggers) - 1):
            assert triggers[i]["priority"] >= triggers[i + 1]["priority"]

    def test_respects_top(self):
        term_map = hooks_mod.build_term_map(SAMPLE_AGENTS)
        triggers = hooks_mod.build_triggers(term_map, top=3)
        assert len(triggers) <= 3

    def test_skips_filtered_terms(self):
        term_map = {"agent": [{"id": "a", "name": "A", "category": "x"},
                              {"id": "b", "name": "B", "category": "y"}]}
        triggers = hooks_mod.build_triggers(term_map, top=None)
        assert len(triggers) == 0


# ── generate-omc-team-config.py ───────────────────────────────────────────────

team_mod = _load_script("generate-omc-team-config")


class TestAgentsForRoles:
    def test_team_plan(self):
        result = team_mod.agents_for_roles(
            SAMPLE_AGENTS, ["phase-0-discovery", "phase-1-strategy"])
        ids = {a["id"] for a in result}
        assert "engineering-backend-architect" in ids

    def test_team_exec(self):
        result = team_mod.agents_for_roles(
            SAMPLE_AGENTS, ["phase-2-foundation", "phase-3-build"])
        assert len(result) == 3

    def test_empty_roles(self):
        assert team_mod.agents_for_roles(SAMPLE_AGENTS, []) == []


class TestBuildTeamConfig:
    def test_all_stages(self):
        config = team_mod.build_team_config(SAMPLE_AGENTS)
        for stage in ("team-plan", "team-prd", "team-exec", "team-verify", "team-fix"):
            assert stage in config

    def test_required_fields(self):
        config = team_mod.build_team_config(SAMPLE_AGENTS)
        for stage in config.values():
            for field in ("description", "nexus_roles", "omc_lead_agents",
                          "nexus_agent_count", "nexus_categories", "nexus_agents"):
                assert field in stage

    def test_counts(self):
        config = team_mod.build_team_config(SAMPLE_AGENTS)
        assert config["team-exec"]["nexus_agent_count"] == 3
        assert config["team-verify"]["nexus_agent_count"] == 1


# ── show_summary / output tests ──────────────────────────────────────────────

class TestShowSummary:
    def test_export_show_summary(self, tmp_path, capsys):
        exported = [{**a, "score": 10.0, "grade": "B"} for a in SAMPLE_AGENTS[:2]]
        export_mod.show_summary(exported, tmp_path, dry_run=True)
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "2 agents" in captured.out

    def test_export_show_summary_wet(self, tmp_path, capsys):
        exported = [{**a, "score": 10.0, "grade": "B"} for a in SAMPLE_AGENTS[:1]]
        export_mod.show_summary(exported, tmp_path, dry_run=False)
        captured = capsys.readouterr()
        assert "[DRY RUN]" not in captured.out
        assert "1 agents" in captured.out

    def test_routing_show_summary(self, capsys):
        routing = routing_mod.generate_routing(SAMPLE_SCORES, SAMPLE_RISKS, SAMPLE_AGENTS)
        routing_mod.show_summary(routing)
        captured = capsys.readouterr()
        assert "Model Routing Summary" in captured.out
        assert "opus" in captured.out

    def test_team_show_summary(self, capsys):
        config = team_mod.build_team_config(SAMPLE_AGENTS)
        team_mod.show_summary(config)
        captured = capsys.readouterr()
        assert "NEXUS -> OMC Team Pipeline Mapping" in captured.out
        assert "team-plan" in captured.out


# ── main() CLI entry tests ──────────────────────────────────────────────────

class TestMainFunctions:
    def test_export_main_verify(self, tmp_path, monkeypatch):
        """Test --verify on empty dir returns exit code 1."""
        monkeypatch.setattr(sys, "argv", ["export-omc-agents.py", "--verify",
                                           "--output", str(tmp_path)])
        with pytest.raises(SystemExit) as exc:
            export_mod.main()
        assert exc.value.code == 1

    def test_export_main_dry_run(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["export-omc-agents.py", "--dry-run",
                                           "--min-score", "10",
                                           "--output", str(tmp_path)])
        monkeypatch.setattr(export_mod, "load_agents", lambda: SAMPLE_AGENTS)
        monkeypatch.setattr(export_mod, "compute_scores", lambda agents: SAMPLE_SCORES)
        export_mod.main()
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    def test_hooks_main(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["generate-omc-hooks.py", "--top", "5",
                                           "--output", str(tmp_path / "hooks.json")])
        monkeypatch.setattr(hooks_mod, "load_agents", lambda: SAMPLE_AGENTS)
        hooks_mod.main()
        captured = capsys.readouterr()
        assert "Extracting keywords" in captured.out

    def test_routing_main_summary(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["generate-omc-model-routing.py", "--summary"])
        monkeypatch.setattr(routing_mod, "load_agents", lambda: SAMPLE_AGENTS)
        monkeypatch.setattr(routing_mod, "compute_scores",
                            lambda: (SAMPLE_SCORES, SAMPLE_RISKS))
        routing_mod.main()
        captured = capsys.readouterr()
        assert "Model Routing Summary" in captured.out

    def test_team_main_summary(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["generate-omc-team-config.py", "--summary"])
        monkeypatch.setattr(team_mod, "load_agents", lambda: SAMPLE_AGENTS)
        team_mod.main()
        captured = capsys.readouterr()
        assert "NEXUS -> OMC" in captured.out
