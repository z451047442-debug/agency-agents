"""Tests for scripts/nexus-orchestrator.py — multi-agent project orchestrator."""
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _load_mod():
    spec = importlib.util.spec_from_file_location(
        "nexus_orchestrator", str(SCRIPTS_DIR / "nexus-orchestrator.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_mod()


SAMPLE_AGENTS_JSON = json.dumps({
    "agents": [
        {"id": "eng-test", "name": "Test Engineer", "category": "engineering",
         "nexus_roles": ["phase-3-build"]},
        {"id": "eng-architect", "name": "Architect", "category": "engineering",
         "nexus_roles": ["phase-1-strategy", "phase-3-build"]},
        {"id": "sec-auditor", "name": "Security Auditor", "category": "security",
         "nexus_roles": ["phase-4-hardening"]},
        {"id": "ops-sre", "name": "SRE", "category": "operations",
         "nexus_roles": ["phase-6-operate"]},
    ]
})


class TestFilterByPhase:
    def test_filters_by_phase(self):
        agents = [
            {"id": "a", "nexus_roles": ["phase-3-build"]},
            {"id": "b", "nexus_roles": ["phase-1-strategy"]},
            {"id": "c", "nexus_roles": []},
        ]
        result = mod.filter_by_phase(agents, "3")
        assert len(result) == 1
        assert result[0]["id"] == "a"

    def test_agent_without_nexus_roles(self):
        agents = [{"id": "x"}]
        result = mod.filter_by_phase(agents, "3")
        assert result == []


class TestGetPhaseLabel:
    def test_default_label(self):
        assert mod.get_phase_label("software", "0") == "Discovery"

    def test_scenario_specific_label(self):
        assert mod.get_phase_label("research", "0") == "Scope & Question"

    def test_unknown_scenario_fallback(self):
        assert mod.get_phase_label("nonexistent", "3") == "Build"

    def test_unknown_phase_fallback(self):
        assert mod.get_phase_label("software", "99") == "Phase 99"


class TestGetFeedbackLoops:
    def test_software_has_default_loops(self):
        fb = mod.get_feedback_loops("software")
        assert "4" in fb
        assert fb["4"] == "3"

    def test_unknown_scenario_default(self):
        fb = mod.get_feedback_loops("nonexistent")
        assert "4" in fb


class TestCheckpointOps:
    def test_create_checkpoint(self):
        cp = mod.create_checkpoint("test-proj", "software")
        assert cp["project"] == "test-proj"
        assert cp["scenario"] == "software"
        assert cp["current_phase"] is None
        assert len(cp["phases"]) == 7

    def test_save_and_load(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        cp = mod.create_checkpoint("my-proj", "software")
        mod.save_checkpoint("my-proj", cp)
        loaded = mod.load_checkpoint("my-proj")
        assert loaded["project"] == "my-proj"

    def test_load_missing_exits(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        with pytest.raises(SystemExit):
            mod.load_checkpoint("nonexistent")


class TestInitProject:
    def test_init_creates_checkpoint(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("fresh", "software")
        assert (tmp_path / "fresh" / "checkpoint.json").exists()

    def test_init_existing_exits(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("dup", "software")
        with pytest.raises(SystemExit):
            mod.init_project("dup", "software")


class TestStartPhase:
    def test_shows_agents(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        index_path = tmp_path / "AGENTS.json"
        index_path.write_text(SAMPLE_AGENTS_JSON, encoding="utf-8")
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        mod.init_project("p1", "software")
        mod.start_phase("p1", "0")
        assert "Phase 0" in capsys.readouterr().out

    def test_requires_prev_completed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("p2", "software")
        with pytest.raises(SystemExit):
            mod.start_phase("p2", "3")


class TestCompletePhase:
    def test_requires_gate(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("p3", "software")
        mod.start_phase("p3", "0")
        with pytest.raises(SystemExit):
            mod.complete_phase("p3", "0")

    def test_marks_done_and_next(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("p4", "software")
        mod.start_phase("p4", "0")
        cp = mod.load_checkpoint("p4")
        cp["phases"]["0"]["gate"] = {"q": {"passed": True}}
        mod.save_checkpoint("p4", cp)
        mod.complete_phase("p4", "0")
        assert "COMPLETED" in capsys.readouterr().out

    def test_complete_final_phase(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("pf", "software")
        for p in ["0", "1", "2", "3", "4", "5"]:
            mod.start_phase("pf", p)
            cp = mod.load_checkpoint("pf")
            cp["phases"][p]["gate"] = {"q": {"passed": True}}
            mod.save_checkpoint("pf", cp)
            mod.complete_phase("pf", p)
        mod.start_phase("pf", "6")
        cp = mod.load_checkpoint("pf")
        cp["phases"]["6"]["gate"] = {"q": {"passed": True}}
        mod.save_checkpoint("pf", cp)
        mod.complete_phase("pf", "6")
        assert "finished" in capsys.readouterr().out


class TestRollbackPhase:
    def test_rollback_reopens_phases(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("p5", "software")
        for p in ["0", "1", "2", "3"]:
            mod.start_phase("p5", p)
            cp = mod.load_checkpoint("p5")
            cp["phases"][p]["gate"] = {"q": {"passed": True}}
            mod.save_checkpoint("p5", cp)
            mod.complete_phase("p5", p)
        mod.start_phase("p5", "4")
        mod.rollback_phase("p5", "4")
        assert "Rolled back" in capsys.readouterr().out

    def test_rollback_no_feedback_loop(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("p6", "software")
        mod.start_phase("p6", "0")
        cp = mod.load_checkpoint("p6")
        cp["phases"]["0"]["gate"] = {"q": {"passed": True}}
        mod.save_checkpoint("p6", cp)
        mod.complete_phase("p6", "0")
        with pytest.raises(SystemExit):
            mod.rollback_phase("p6", "0")


class TestShowStatus:
    def test_displays_phases(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("p8", "research")
        mod.show_status("p8")
        assert "Scope & Question" in capsys.readouterr().out

    def test_with_feedback_loops(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("pfb", "software")
        mod.show_status("pfb")
        assert "Feedback Loops" in capsys.readouterr().out


class TestGenerateReport:
    def test_report_with_summary(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("p9", "software")
        mod.start_phase("p9", "0")
        cp = mod.load_checkpoint("p9")
        cp["phases"]["0"]["gate"] = {"Q1": {"passed": True, "evidence": "ok", "timestamp": "2026-01-01T00:00:00"}}
        mod.save_checkpoint("p9", cp)
        mod.complete_phase("p9", "0")
        mod.generate_report("p9")
        assert "Phase Progress" in capsys.readouterr().out


class TestListProjects:
    def test_no_projects(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.list_projects()
        assert "No projects" in capsys.readouterr().out

    def test_with_project(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("my-app", "software")
        mod.list_projects()
        assert "my-app" in capsys.readouterr().out


class TestQueryPhase:
    def test_json_output(self, tmp_path, monkeypatch, capsys):
        index_path = tmp_path / "AGENTS.json"
        index_path.write_text(SAMPLE_AGENTS_JSON, encoding="utf-8")
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        mod.query_phase("3", "full", None, True)
        data = json.loads(capsys.readouterr().out)
        assert data["phase"] == "3"

    def test_category_filter(self, tmp_path, monkeypatch, capsys):
        index_path = tmp_path / "AGENTS.json"
        index_path.write_text(SAMPLE_AGENTS_JSON, encoding="utf-8")
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        mod.query_phase("3", "full", "engineering", False)
        assert "Test Engineer" in capsys.readouterr().out

    def test_micro_mode_truncates(self, tmp_path, monkeypatch, capsys):
        index_path = tmp_path / "AGENTS.json"
        big = json.dumps({"agents": [
            {"id": f"a{i}", "name": f"A{i}", "category": "eng",
             "nexus_roles": ["phase-3-build"]} for i in range(20)
        ]})
        index_path.write_text(big, encoding="utf-8")
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        mod.query_phase("3", "micro", None, False)
        assert "... +" in capsys.readouterr().out

    def test_no_agents_exits(self, tmp_path, monkeypatch):
        index_path = tmp_path / "AGENTS.json"
        index_path.write_text('{"agents":[]}', encoding="utf-8")
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        with pytest.raises(SystemExit):
            mod.query_phase("3", "full", None, False)

    def test_missing_index_exits(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "INDEX_PATH", tmp_path / "missing.json")
        with pytest.raises(SystemExit):
            mod.query_phase("0", "full", None, False)


class TestRunGate:
    def test_requires_in_progress(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("pg", "software")
        with pytest.raises(SystemExit):
            mod.run_gate("pg", "0")

    def test_all_pass(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("pg2", "software")
        mod.start_phase("pg2", "0")
        with patch("builtins.input", side_effect=["pass done"] * 5):
            mod.run_gate("pg2", "0")
        assert "All checks passed" in capsys.readouterr().out

    def test_some_fail(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("pg3", "software")
        mod.start_phase("pg3", "0")
        with patch("builtins.input", side_effect=["fail reason", "pass ok", "pass ok", "pass ok", "pass ok"]):
            mod.run_gate("pg3", "0")
        assert "failed" in capsys.readouterr().out

    def test_gate_passes_no_evidence(self, tmp_path, monkeypatch, capsys):
        """Line 312: gate check with pass but no evidence text."""
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("pg-noev", "software")
        mod.start_phase("pg-noev", "0")
        with patch("builtins.input", side_effect=["pass"] * 5):
            mod.run_gate("pg-noev", "0")
        assert "All checks passed" in capsys.readouterr().out

    def test_gate_already_pending(self, tmp_path, monkeypatch):
        """Line 381-382: complete_phase on non-in_progress phase."""
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("pg4", "software")
        with pytest.raises(SystemExit):
            mod.complete_phase("pg4", "0")

    def test_rollback_pending_phase(self, tmp_path, monkeypatch):
        """Lines 406-407: rollback phase not started."""
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("pg5", "software")
        with pytest.raises(SystemExit):
            mod.rollback_phase("pg5", "3")


class TestGenerateReportLegacy:
    def test_legacy_gate_format(self, tmp_path, monkeypatch, capsys):
        """Lines 358-364: legacy gate format with bool values."""
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("p-legacy", "software")
        mod.start_phase("p-legacy", "0")
        cp = mod.load_checkpoint("p-legacy")
        cp["phases"]["0"]["gate"] = {"Q1": True, "Q2": False}
        mod.save_checkpoint("p-legacy", cp)
        mod.generate_report("p-legacy")
        captured = capsys.readouterr()
        assert "Phase Progress" in captured.out


class TestListProjectsEdgeCases:
    def test_skips_non_dir(self, tmp_path, monkeypatch, capsys):
        """Line 439: skip non-directory entries during iteration."""
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        # Need a valid project so we get past the early return
        mod.init_project("valid-project", "software")
        (tmp_path / "not-a-dir.txt").write_text("x", encoding="utf-8")
        mod.list_projects()
        assert "valid-project" in capsys.readouterr().out

    def test_skips_no_checkpoint(self, tmp_path, monkeypatch, capsys):
        """Line 442: skip dirs without checkpoint.json during iteration."""
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        # Need a valid project so we iterate past early return
        mod.init_project("valid-project", "software")
        (tmp_path / "empty-dir").mkdir(parents=True)
        mod.list_projects()
        assert "valid-project" in capsys.readouterr().out


class TestMain:
    def test_help_output(self, capsys):
        with patch.object(sys, "argv", ["nexus-orchestrator.py"]):
            mod.main()
        out = capsys.readouterr().out
        assert "NEXUS" in out or "usage" in out.lower()

    def test_init(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        with patch.object(sys, "argv", ["nexus-orchestrator.py", "--init", "proj", "--scenario", "consulting"]):
            mod.main()
        assert "proj" in capsys.readouterr().out

    def test_list_projects(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        with patch.object(sys, "argv", ["nexus-orchestrator.py", "--list-projects"]):
            mod.main()
        assert "No projects" in capsys.readouterr().out

    def test_status(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("ps", "software")
        with patch.object(sys, "argv", ["nexus-orchestrator.py", "--project", "ps", "--status"]):
            mod.main()
        assert "Phase Status" in capsys.readouterr().out

    def test_project_defaults_to_status(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("pd", "software")
        with patch.object(sys, "argv", ["nexus-orchestrator.py", "--project", "pd"]):
            mod.main()
        assert "Phase Status" in capsys.readouterr().out

    def test_start_via_main(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        index_path = tmp_path / "AGENTS.json"
        index_path.write_text(SAMPLE_AGENTS_JSON, encoding="utf-8")
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        mod.init_project("ps2", "software")
        with patch.object(sys, "argv", ["nexus-orchestrator.py", "--project", "ps2", "--start", "0"]):
            mod.main()
        assert "Phase 0" in capsys.readouterr().out

    def test_report_via_main(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("pr", "software")
        with patch.object(sys, "argv", ["nexus-orchestrator.py", "--project", "pr", "--report"]):
            mod.main()
        assert "GATE REPORT" in capsys.readouterr().out

    def test_query_phase_via_main(self, tmp_path, monkeypatch, capsys):
        index_path = tmp_path / "AGENTS.json"
        index_path.write_text(SAMPLE_AGENTS_JSON, encoding="utf-8")
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        with patch.object(sys, "argv", ["nexus-orchestrator.py", "--phase", "3"]):
            mod.main()
        assert "Phase 3" in capsys.readouterr().out

    def test_gate_via_main(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("p-g", "software")
        mod.start_phase("p-g", "0")
        with patch.object(sys, "argv", ["nexus-orchestrator.py", "--project", "p-g", "--gate", "0"]):
            with patch("builtins.input", side_effect=["pass ok"] * 5):
                mod.main()
        assert "All checks passed" in capsys.readouterr().out

    def test_complete_via_main(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("p-c", "software")
        mod.start_phase("p-c", "0")
        cp = mod.load_checkpoint("p-c")
        cp["phases"]["0"]["gate"] = {"q": {"passed": True}}
        mod.save_checkpoint("p-c", cp)
        with patch.object(sys, "argv", ["nexus-orchestrator.py", "--project", "p-c", "--complete", "0"]):
            mod.main()
        assert "COMPLETED" in capsys.readouterr().out

    def test_show_status_with_active_phase(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("p-act", "software")
        mod.start_phase("p-act", "0")
        with patch.object(sys, "argv", ["nexus-orchestrator.py", "--project", "p-act", "--status"]):
            mod.main()
        captured = capsys.readouterr()
        assert "Active" in captured.out

    def test_show_status_with_completed_phase(self, tmp_path, monkeypatch, capsys):
        """Line 234: show_status with completed phase dates."""
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("p-done", "software")
        mod.start_phase("p-done", "0")
        cp = mod.load_checkpoint("p-done")
        cp["phases"]["0"]["gate"] = {"q": {"passed": True}}
        mod.save_checkpoint("p-done", cp)
        mod.complete_phase("p-done", "0")
        mod.show_status("p-done")
        assert "completed" in capsys.readouterr().out

    def test_report_phase_without_gate(self, tmp_path, monkeypatch, capsys):
        """Line 364: report on phase that was started but gate not run."""
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("p-nogate", "software")
        mod.start_phase("p-nogate", "0")
        mod.generate_report("p-nogate")
        assert "gate not yet run" in capsys.readouterr().out

    def test_rollback_via_main(self, tmp_path, monkeypatch, capsys):
        """Line 530: main() calling rollback_phase."""
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("p-rb2", "software")
        for p in ["0", "1", "2", "3"]:
            mod.start_phase("p-rb2", p)
            cp = mod.load_checkpoint("p-rb2")
            cp["phases"][p]["gate"] = {"q": {"passed": True}}
            mod.save_checkpoint("p-rb2", cp)
            mod.complete_phase("p-rb2", p)
        mod.start_phase("p-rb2", "4")
        with patch.object(sys, "argv", ["nexus-orchestrator.py", "--project", "p-rb2", "--rollback", "4"]):
            mod.main()
        assert "Rolled back" in capsys.readouterr().out


class TestNewScenarios:
    def test_enterprise_feature_init(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("ent-feat", "enterprise-feature")
        cp = mod.load_checkpoint("ent-feat")
        assert cp["scenario"] == "enterprise-feature"
        assert len(cp["phases"]) == 5

    def test_incident_response_init(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("inc-resp", "incident-response")
        cp = mod.load_checkpoint("inc-resp")
        assert cp["scenario"] == "incident-response"
        assert len(cp["phases"]) == 4

    def test_marketing_campaign_feedback(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        mod.init_project("mkt-camp", "marketing-campaign")
        fb = mod.get_feedback_loops("marketing-campaign")
        assert fb == {"2": "0"}


class TestGetGateQuestions:
    def test_default_questions(self):
        qs = mod.get_gate_questions("software", "0")
        assert len(qs) == 5

    def test_incident_custom_questions(self):
        qs = mod.get_gate_questions("incident-response", "0")
        assert any("Severity" in q[0] for q in qs)

    def test_marketing_custom_questions(self):
        qs = mod.get_gate_questions("marketing-campaign", "0")
        assert any("Campaign" in q[0] for q in qs)

    def test_unknown_scenario_fallback(self):
        qs = mod.get_gate_questions("nonexistent", "3")
        assert len(qs) == 6  # Phase 3 has 6 default questions

    def test_unknown_phase_empty(self):
        qs = mod.get_gate_questions("software", "99")
        assert qs == []


class TestDiscoverScenario:
    def test_software_discovery(self, capsys):
        mod.discover_scenario("build a mobile app")
        assert "software" in capsys.readouterr().out

    def test_incident_discovery(self, capsys):
        mod.discover_scenario("production outage emergency alert")
        assert "incident-response" in capsys.readouterr().out

    def test_marketing_discovery(self, capsys):
        mod.discover_scenario("social media brand campaign launch")
        assert "marketing-campaign" in capsys.readouterr().out

    def test_no_match_shows_all(self, capsys):
        mod.discover_scenario("xyzzy12345")
        assert "No direct matches" in capsys.readouterr().out

    def test_discover_via_main(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "PROJECTS_DIR", tmp_path)
        with patch.object(sys, "argv", ["nexus-orchestrator.py", "--discover", "launch mvp"]):
            mod.main()
        assert "software" in capsys.readouterr().out


class TestNewPhaseLabels:
    def test_enterprise_labels(self):
        assert mod.get_phase_label("enterprise-feature", "0") == "Requirements & Architecture"
        assert mod.get_phase_label("enterprise-feature", "4") == "Rollout"

    def test_incident_labels(self):
        assert mod.get_phase_label("incident-response", "0") == "Detection & Triage"
        assert mod.get_phase_label("incident-response", "3") == "Post-Mortem"

    def test_marketing_labels(self):
        assert mod.get_phase_label("marketing-campaign", "0") == "Strategy & Content"
        assert mod.get_phase_label("marketing-campaign", "2") == "Optimize & Sustain"
