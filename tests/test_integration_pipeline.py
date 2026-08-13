"""Integration tests for the full quality pipeline with fixture agents.

Creates a small dataset of 10 fixture agents and verifies cross-script
consistency across scoring, linting, dependency validation, and lifecycle.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _load_script(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, str(SCRIPTS_DIR / filename)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_agent(dirpath, name, category, body_words=150, sections=None):
    """Create a fixture agent .md file with configurable content depth."""
    if sections is None:
        sections = {
            "Identity": "You are a helpful expert in this domain.",
            "Core Mission": "Your mission is to assist users effectively.",
            "Critical Rules": "1. Always verify facts.\n2. Stay in scope.",
            "Deliverables": "Reports and recommendations.",
            "Workflow": "Step by step analysis.",
        }

    desc = f"An expert agent for {name} in {category}"
    fm = (
        f'---\nname: "{name}"\ndescription: "{desc}"\n'
        f'emoji: "💡"\ncolor: blue\nversion: "1.0.0"\n'
        f'date_added: "2026-07-16"\n---\n\n'
    )

    body_parts = []
    for sec_title, sec_content in sections.items():
        body_parts.append(f"## {sec_title}\n{sec_content}\n")

    current_words = sum(len(b.split()) for b in body_parts)
    if current_words < body_words:
        needed = body_words - current_words
        body_parts.append("\n" + " ".join(["context"] * needed) + "\n")

    content = fm + "\n".join(body_parts)
    filepath = dirpath / f"{category}-{name.lower().replace(' ', '-')}.md"
    content = content.replace("\r\n", "\n")
    filepath.write_text(content, encoding="utf-8", newline="\n")
    return filepath


@pytest.fixture
def fixture_agents(tmp_path, monkeypatch):
    """Create a fixture dataset of 10 agents across 3 categories."""
    import _shared.discovery as discovery

    monkeypatch.setattr(discovery, "REPO", tmp_path)

    for cat in ("engineering", "design", "data-science"):
        (tmp_path / cat).mkdir()

    eng = tmp_path / "engineering"
    design = tmp_path / "design"
    data = tmp_path / "data-science"

    _make_agent(eng, "Expert Developer", "engineering", body_words=300,
                sections={
                    "Identity": "You are a senior Python developer with 10 years "
                    "of experience in building scalable web applications.",
                    "Core Mission": "Write clean, well-tested Python code.",
                    "Critical Rules": "1. Always write tests first.\n2. Use type hints.",
                    "Deliverables": "Production-ready Python modules.",
                    "Workflow": "1. Understand.\n2. Test.\n3. Implement.\n4. Review.",
                    "Success Metrics": "Coverage above 90%, zero lint errors.",
                })
    _make_agent(eng, "Basic Coder", "engineering", body_words=50,
                sections={"Identity": "You write code.", "Core Mission": "Code."})
    _make_agent(eng, "DevOps Engineer", "engineering", body_words=200,
                sections={
                    "Identity": "You are a DevOps engineer for CI/CD.",
                    "Core Mission": "Automate deployment.",
                    "Critical Rules": "1. IaC.\n2. Monitor everything.",
                    "Deliverables": "CI/CD pipelines.",
                })
    _make_agent(eng, "Frontend Developer", "engineering", body_words=180,
                sections={
                    "Identity": "React developer with UX focus.",
                    "Core Mission": "Build accessible UIs.",
                    "Critical Rules": "1. Mobile-first.\n2. WCAG compliant.",
                    "Deliverables": "React components.",
                })

    _make_agent(design, "UX Researcher", "design", body_words=250,
                sections={
                    "Identity": "UX researcher focused on qualitative methods.",
                    "Core Mission": "Understand user needs.",
                    "Critical Rules": "1. Evidence over opinion.\n2. Inclusive.",
                    "Deliverables": "Research reports, personas.",
                    "Workflow": "Plan, recruit, analyze, report.",
                })
    _make_agent(design, "UI Designer", "design", body_words=200,
                sections={
                    "Identity": "UI designer for design systems.",
                    "Core Mission": "Create consistent interfaces.",
                    "Critical Rules": "1. Follow design system.\n2. Usability first.",
                })
    _make_agent(design, "Brand Strategist", "design", body_words=220)

    _make_agent(data, "ML Engineer", "data-science", body_words=280,
                sections={
                    "Identity": "ML engineer deploying at scale.",
                    "Core Mission": "Productionize ML models.",
                    "Critical Rules": "1. Monitor drift.\n2. Version datasets.",
                    "Deliverables": "ML pipelines, model cards.",
                    "Workflow": "Prep, train, eval, deploy, monitor.",
                })
    _make_agent(data, "Data Analyst", "data-science", body_words=160)
    _make_agent(data, "AI Researcher", "data-science", body_words=350,
                sections={
                    "Identity": "AI researcher advancing LLM capabilities.",
                    "Core Mission": "Advance AI through rigorous research.",
                    "Critical Rules": "1. Reproducible.\n2. Ethical.\n3. Open science.",
                    "Deliverables": "Papers, benchmarks, models.",
                    "Workflow": "Hypothesize, experiment, analyze, publish.",
                    "Success Metrics": "Paper acceptance, benchmark improvements.",
                    "Communication": "Clear technical writing.",
                })

    return tmp_path


class TestPipelineIntegration:
    """Integration tests verifying cross-script consistency."""

    def test_score_agent_on_fixture(self, fixture_agents, monkeypatch):
        import _shared.discovery as discovery

        monkeypatch.setattr(discovery, "REPO", fixture_agents)

        score_agents = _load_script("score_agents", "score-agents.py")
        score_agent = score_agents.score_agent

        results = {}
        for _cat, _rel, filepath in discovery.discover_agents():
            r = score_agent(filepath, check_freshness=False)
            results[filepath.stem] = r

        assert len(results) == 10
        assert results["engineering-expert-developer"]["total"] > results["engineering-basic-coder"]["total"]
        for r in results.values():
            assert r["grade"] in ("A", "B", "C", "D")
            assert 0 <= r["total"] <= 10

    def test_lint_on_fixture(self, fixture_agents, monkeypatch):
        import _shared.discovery as discovery

        monkeypatch.setattr(discovery, "REPO", fixture_agents)

        lint_agents = _load_script("lint_agents", "lint-agents.py")
        lint_file = lint_agents.lint_file

        errors, warnings, infos = [], [], []
        for _cat, _rel, filepath in discovery.discover_agents():
            lint_file(filepath, errors, warnings, infos, freshness=False)

        crlf_errors = [e for e in errors if "CRLF" in e]
        real_errors = [e for e in errors if "CRLF" not in e]
        assert not real_errors, f"Unexpected lint errors: {real_errors}"

    def test_score_lint_consistency(self, fixture_agents, monkeypatch):
        import _shared.discovery as discovery

        monkeypatch.setattr(discovery, "REPO", fixture_agents)

        score_agents = _load_script("score_agents", "score-agents.py")
        lint_agents = _load_script("lint_agents", "lint-agents.py")
        score_agent = score_agents.score_agent
        lint_file = lint_agents.lint_file

        for _cat, _rel, filepath in discovery.discover_agents():
            r = score_agent(filepath, check_freshness=False)
            e, w, i = [], [], []
            lint_file(filepath, e, w, i, freshness=False)
            if r["total"] >= 7:
                assert not e, f"High-scoring agent {filepath.stem} has errors: {e}"

    def test_analyze_deps_on_fixture(self, fixture_agents, monkeypatch):
        import _shared.discovery as discovery

        monkeypatch.setattr(discovery, "REPO", fixture_agents)

        analyze_deps = _load_script("analyze_deps", "analyze-deps.py")
        # validate_depends_on expects a dict keyed by agent ID
        agent_index = analyze_deps.build_agent_index()
        findings = analyze_deps.validate_depends_on(agent_index)
        assert len(findings) == 3  # (valid_refs, broken_refs, agents_with_deps)
        # Fixture agents declare no depends_on, so nothing is valid or broken
        assert findings[0] == []
        assert findings[1] == []
        assert findings[2] == 0

    def test_validate_depends_on_broken_ref(self, fixture_agents, monkeypatch):
        """depends_on pointing to a nonexistent agent must be reported as broken."""
        import _shared.discovery as discovery

        monkeypatch.setattr(discovery, "REPO", fixture_agents)

        analyze_deps = _load_script("analyze_deps", "analyze-deps.py")
        agent_index = analyze_deps.build_agent_index()

        # An agent whose depends_on targets an agent absent from the index
        broken_path = fixture_agents / "engineering" / "engineering-broken-ref.md"
        broken_path.write_text(
            "---\nname: Broken Ref\ndescription: Has a broken dependency\n"
            "emoji: X\ncolor: blue\nversion: '1.0.0'\ndate_added: '2026-07-16'\n"
            "depends_on:\n  - engineering-no-such-agent\n---\n\n"
            "## Identity\nYou are a test agent.\n\n"
            "## Core Mission\nTest.\n\n"
            "## Critical Rules\n1. Test.\n",
            encoding="utf-8",
        )

        valid, broken, agents_with_deps = analyze_deps.validate_depends_on(agent_index)
        assert ("engineering-broken-ref", "engineering-no-such-agent") in broken
        assert agents_with_deps == 1
        assert valid == []

    def test_agent_lifecycle_on_fixture(self, fixture_agents, monkeypatch):
        import _shared.discovery as discovery

        monkeypatch.setattr(discovery, "REPO", fixture_agents)

        agent_lifecycle = _load_script("agent_lifecycle", "agent-lifecycle.py")
        flags = agent_lifecycle.auto_flag_agents(category_filter=None)

        assert len(flags) >= 1
        scores = [f[4] for f in flags]
        assert scores == sorted(scores)

    def test_pipeline_end_to_end(self, fixture_agents, monkeypatch):
        """Full pipeline: score + lint + deps on all fixture agents."""
        import _shared.discovery as discovery

        monkeypatch.setattr(discovery, "REPO", fixture_agents)

        score_agents = _load_script("score_agents", "score-agents.py")
        lint_agents = _load_script("lint_agents", "lint-agents.py")
        analyze_deps = _load_script("analyze_deps", "analyze-deps.py")

        score_agent = score_agents.score_agent
        lint_file = lint_agents.lint_file

        agents = list(discovery.discover_agents())
        assert len(agents) == 10

        total = 0
        for _cat, _rel, filepath in agents:
            r = score_agent(filepath, check_freshness=False)
            total += r["total"]
            e, w, i = [], [], []
            lint_file(filepath, e, w, i, freshness=False)

        avg = total / len(agents)
        # Accept broader range — fixture agents are intentionally minimal
        assert 2 <= avg <= 9

        # validate_depends_on expects a dict keyed by agent ID, not the
        # (category, relpath, filepath) tuples from discover_agents()
        agent_index = analyze_deps.build_agent_index()
        findings = analyze_deps.validate_depends_on(agent_index)
        assert len(findings) == 3  # (valid_refs, broken_refs, agents_with_deps)
        # Fixture agents declare no depends_on, so nothing is valid or broken
        assert findings[0] == []
        assert findings[1] == []
        assert findings[2] == 0
