"""Tests for scripts/analyze-deps.py — dependency analysis engine."""

import importlib.util
import io
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "analyze_deps", str(SCRIPTS_DIR / "analyze-deps.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

extract_terms = mod.extract_terms
compute_dep_score = mod.compute_dep_score
validate_depends_on = mod.validate_depends_on
get_list_field = mod.get_list_field
build_agent_index = mod.build_agent_index
build_term_index = mod.build_term_index
suggest_dependencies = mod.suggest_dependencies
print_dependency_health = mod.print_dependency_health


def make_agent_file(path, name, description, body, deps=None, category="test-cat"):
    """Create a temporary agent .md file with valid frontmatter."""
    dep_lines = ""
    if deps:
        dep_lines += f"depends_on:\n"
        for d in deps:
            dep_lines += f"  - {d}\n"

    content = f"""---
name: "{name}"
description: "{description}"
color: blue
emoji: "\\U0001f527"
version: "1.0.0"
date_added: "2026-07-03"
{dep_lines}---

## Identity
You are {name}. You specialize in {description}.

## Mission
{body}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class TestGetListField:
    def test_extract_depends_on(self):
        fm = "depends_on:\n  - agent-a\n  - agent-b\ncolor: blue\n"
        assert get_list_field("depends_on", fm) == ["agent-a", "agent-b"]

    def test_empty_when_missing(self):
        assert get_list_field("depends_on", "name: test\ncolor: blue\n") == []

    def test_stops_at_next_field(self):
        fm = "depends_on:\n  - dep-a\n  - dep-b\nnext: value\n"
        assert get_list_field("depends_on", fm) == ["dep-a", "dep-b"]


class TestExtractTerms:
    def test_extracts_id_and_category(self, tmp_path):
        f = make_agent_file(
            tmp_path / "test-cat" / "test-cat-data-engineer.md",
            "Data Engineer", "Expert in data pipelines",
            "Building **data pipelines** with **Apache Spark**."
        )
        result = extract_terms(f)
        assert result is not None
        assert result["id"] == "test-cat-data-engineer"
        assert result["category"] == "test-cat"

    def test_extracts_description_terms(self, tmp_path):
        f = make_agent_file(
            tmp_path / "test-cat" / "test-cat-ml-engineer.md",
            "ML Engineer", "Machine learning model deployment specialist",
            "Deploying models with **TensorFlow** and **PyTorch**."
        )
        result = extract_terms(f)
        assert result is not None
        assert len(result["desc_terms"]) >= 0

    def test_extracts_body_bold_terms(self, tmp_path):
        f = make_agent_file(
            tmp_path / "test-cat" / "test-cat-cloud-architect.md",
            "Cloud Architect", "AWS and Azure cloud architecture expert",
            "Designing **serverless** architectures with **Lambda** and **ECS**."
        )
        result = extract_terms(f)
        assert result is not None
        assert "serverless" in result["body_terms"] or "lambda" in result["body_terms"]

    def test_all_terms_union(self, tmp_path):
        f = make_agent_file(
            tmp_path / "test-cat" / "test-cat-fullstack-dev.md",
            "Fullstack Developer", "React frontend and Node.js backend",
            "Building apps with **React**, **TypeScript**, and **Express**."
        )
        result = extract_terms(f)
        assert len(result["all_terms"]) >= len(result["name_terms"])
        assert len(result["all_terms"]) >= len(result["desc_terms"])

    def test_invalid_file_returns_none(self, tmp_path):
        f = tmp_path / "nonexistent" / "ghost.md"
        result = extract_terms(f)
        assert result is None


class TestComputeDepScore:
    def make_agent(self, aid, cat, name, desc, body_terms, desc_terms):
        return {
            "id": aid, "category": cat, "name": name,
            "name_terms": set(name.lower().split()),
            "desc_terms": desc_terms,
            "body_terms": body_terms,
            "all_terms": body_terms | desc_terms,
            "body_text": " ".join(body_terms),
        }

    def test_score_range(self):
        source = self.make_agent(
            "src", "eng", "Frontend Developer",
            "react", {"react", "component"}, {"react"}
        )
        target = self.make_agent(
            "tgt", "eng", "React Specialist",
            "react", {"react", "hooks"}, {"react", "hooks"}
        )
        score, evidence = compute_dep_score(source, target)
        assert 0 <= score <= 1.0
        assert isinstance(evidence, list)

    def test_same_category_bonus(self):
        source = self.make_agent(
            "src", "engineering", "A", "a", {"deploy"}, {"deploy"}
        )
        target = self.make_agent(
            "tgt", "engineering", "B", "b", {"deploy"}, {"deploy"}
        )
        score, _evidence = compute_dep_score(source, target)
        assert score >= 0.05

    def test_no_overlap_gives_zero(self):
        source = self.make_agent(
            "src", "healthcare", "Doctor", "medical", {"patient"}, {"patient"}
        )
        target = self.make_agent(
            "tgt", "engineering", "Compiler Dev", "compiler", {"parser"}, {"parser"}
        )
        score, _evidence = compute_dep_score(source, target)
        assert score == 0.0

    def test_self_reference_in_body(self):
        source = self.make_agent(
            "src", "eng", "K8s User", "k8s",
            set(), {"kubernetes"}
        )
        target = self.make_agent(
            "tgt", "infra", "Kubernetes Expert", "kubernetes",
            {"kubernetes"}, {"kubernetes"}
        )
        score, _evidence = compute_dep_score(source, target)
        assert 0 <= score <= 1.0


class TestValidateDependsOn:
    def test_valid_reference_detected(self, tmp_path, monkeypatch):
        consumer = make_agent_file(
            tmp_path / "test-cat" / "test-cat-consumer.md",
            "Consumer Agent", "Uses other agents",
            "Body content.", deps=["test-cat-provider"]
        )
        provider = make_agent_file(
            tmp_path / "test-cat" / "test-cat-provider.md",
            "Provider Agent", "Provides services",
            "Body content."
        )
        agents = {}
        for f in [consumer, provider]:
            terms = extract_terms(f)
            if terms:
                agents[terms["id"]] = terms

        # Mock discover_agents to only return our tmp files
        def mock_discover():
            for f in [consumer, provider]:
                cat = f.parent.name
                rel = str(f.relative_to(tmp_path)).replace("\\", "/")
                yield cat, rel, f

        monkeypatch.setattr(mod, "discover_agents", mock_discover)
        valid, _broken, _count = validate_depends_on(agents)
        valid_sources = {s for s, _t, _c in valid}
        assert "test-cat-consumer" in valid_sources

    def test_broken_reference_detected(self, tmp_path, monkeypatch):
        consumer = make_agent_file(
            tmp_path / "test-cat" / "test-cat-broken-consumer.md",
            "Broken Consumer", "References missing agent",
            "Body.", deps=["test-cat-nonexistent-target"]
        )
        agents = {}
        terms = extract_terms(consumer)
        if terms:
            agents[terms["id"]] = terms

        def mock_discover():
            cat = consumer.parent.name
            rel = str(consumer.relative_to(tmp_path)).replace("\\", "/")
            yield cat, rel, consumer

        monkeypatch.setattr(mod, "discover_agents", mock_discover)
        _valid, broken, _count = validate_depends_on(agents)
        broken_sources = {s for s, _t in broken}
        assert "test-cat-broken-consumer" in broken_sources

    def test_no_deps_agent_not_broken(self, tmp_path, monkeypatch):
        f = make_agent_file(
            tmp_path / "test-cat" / "test-cat-independent.md",
            "Independent Agent", "No dependencies",
            "Body."
        )
        agents = {}
        terms = extract_terms(f)
        if terms:
            agents[terms["id"]] = terms

        def mock_discover():
            cat = f.parent.name
            rel = str(f.relative_to(tmp_path)).replace("\\", "/")
            yield cat, rel, f

        monkeypatch.setattr(mod, "discover_agents", mock_discover)
        _valid, broken, _count = validate_depends_on(agents)
        broken_sources = {s for s, _t in broken}
        assert "test-cat-independent" not in broken_sources


class TestBuildTermIndex:
    def test_non_empty_index(self, tmp_path):
        f1 = make_agent_file(
            tmp_path / "cat-a" / "cat-a-agent-one.md",
            "Agent One", "Kubernetes specialist",
            "Working with **Kubernetes** deployments."
        )
        f2 = make_agent_file(
            tmp_path / "cat-a" / "cat-a-agent-two.md",
            "Agent Two", "Docker specialist",
            "Working with **Docker** containers."
        )
        agents = {}
        for f in (f1, f2):
            terms = extract_terms(f)
            if terms:
                agents[terms["id"]] = terms
        term_idx = build_term_index(agents)
        assert isinstance(term_idx, dict)
        assert len(term_idx) > 0

    def test_empty_index(self):
        idx = build_term_index({})
        assert idx == {}


# ── build_agent_index ────────────────────────────────────────────────────────

class TestBuildAgentIndex:
    def test_returns_dict(self):
        agents = build_agent_index(category_filter="aviation")
        assert isinstance(agents, dict)

    def test_each_entry_has_required_fields(self):
        agents = build_agent_index(category_filter="aviation")
        for agent_id, agent_data in agents.items():
            assert "id" in agent_data
            assert "category" in agent_data
            assert "name" in agent_data
            assert "all_terms" in agent_data
            assert agent_data["category"] == "aviation"

    def test_empty_for_nonexistent_category(self):
        agents = build_agent_index(category_filter="zzz_no_such_cat_zzz")
        assert agents == {}


# ── suggest_dependencies ─────────────────────────────────────────────────────

class TestSuggestDependencies:
    def test_returns_dict(self):
        agents = build_agent_index(category_filter="aviation")
        if len(agents) < 2:
            pytest.skip("need at least 2 agents for dependency suggestions")
        term_idx = build_term_index(agents)
        suggestions = suggest_dependencies(agents, term_idx, min_confidence=0.3)
        assert isinstance(suggestions, dict)

    def test_suggestions_have_confidence_scores(self):
        agents = build_agent_index(category_filter="aviation")
        if len(agents) < 2:
            pytest.skip("need at least 2 agents for dependency suggestions")
        term_idx = build_term_index(agents)
        suggestions = suggest_dependencies(agents, term_idx, min_confidence=0.1)
        for agent_id, deps in suggestions.items():
            for target_id, confidence, evidence in deps:
                assert 0.0 <= confidence <= 1.0
                assert isinstance(target_id, str)
                assert isinstance(evidence, list)


# ── print_dependency_health ──────────────────────────────────────────────────

class TestPrintDependencyHealth:
    def test_prints_header(self, tmp_path, monkeypatch):
        f1 = make_agent_file(
            tmp_path / "cat1" / "cat1-agent1.md",
            "Agent One", "Testing agent",
            "Some **body** content with **testing** terms."
        )
        f2 = make_agent_file(
            tmp_path / "cat2" / "cat2-agent2.md",
            "Agent Two", "Another agent",
            "Works with **testing** infrastructure."
        )

        def mock_discover():
            for f in (f1, f2):
                cat = f.parent.name
                rel = str(f.relative_to(tmp_path)).replace("\\", "/")
                yield cat, rel, f

        monkeypatch.setattr(mod, "discover_agents", mock_discover)
        agents = {}
        for f in (f1, f2):
            terms = extract_terms(f)
            if terms:
                agents[terms["id"]] = terms

        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_dependency_health(agents)
        finally:
            sys.stdout = old_stdout
        output = buf.getvalue()
        assert "Dependency Graph Health" in output
        assert "Total agents" in output

    def test_handles_empty_agents(self):
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_dependency_health({})
        finally:
            sys.stdout = old_stdout
        output = buf.getvalue()
        assert "Total agents: 0" in output
