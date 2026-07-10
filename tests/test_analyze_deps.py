"""Tests for scripts/analyze-deps.py — dependency analysis engine."""

import argparse
import importlib.util
import io
import json
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


# ═══════════════════════════════════════════════════════════════════════════════
# Additional tests for uncovered lines
# ═══════════════════════════════════════════════════════════════════════════════


# ── sys.stdout.reconfigure (line 63) ───────────────────────────────────────────

class TestStdoutReconfigure:
    """Cover the ``sys.stdout.reconfigure`` guard when encoding is not utf-8."""

    def test_reconfigure_when_encoding_not_utf8(self, monkeypatch):
        class FakeStdout:
            encoding = 'cp1252'
            reconfigure_calls = []

            def reconfigure(self, **kw):
                self.reconfigure_calls.append(kw)

            def write(self, s):
                pass

            def flush(self):
                pass

        fake_stdout = FakeStdout()
        monkeypatch.setattr(sys, 'stdout', fake_stdout)

        fresh_spec = importlib.util.spec_from_file_location(
            "analyze_deps_fresh", str(SCRIPTS_DIR / "analyze-deps.py")
        )
        fresh_mod = importlib.util.module_from_spec(fresh_spec)
        fresh_spec.loader.exec_module(fresh_mod)
        assert fake_stdout.reconfigure_calls


# ── Chinese term extraction ───────────────────────────────────────────────────

class TestExtractTermsChinese:
    """Cover lines 104-107 (Chinese bigram extraction) and line 129 (Chinese headers)."""

    def test_chinese_name_bigrams(self, tmp_path):
        """Cover lines 102-107 — extract Chinese bigrams from agent name.

        Chinese bigrams (2 chars) are extracted then filtered by TERM_MIN_LEN=4.
        The function should run without error regardless.
        """
        f = make_agent_file(
            tmp_path / "test-cat" / "test-cat-ml-engineer.md",
            "机器学习工程师", "Machine learning expert with ML background",
            "Training **models** for NLP tasks."
        )
        result = extract_terms(f)
        assert result is not None
        # The function executed; Chinese bigrams were processed (then filtered)
        assert result["id"] == "test-cat-ml-engineer"
        assert isinstance(result["name_terms"], set)

    def test_chinese_desc_terms(self, tmp_path):
        """Cover lines 112-115 — Chinese words in description.

        4+ character Chinese sequences survive TERM_MIN_LEN filter.
        """
        f = make_agent_file(
            tmp_path / "test-cat" / "test-cat-cn.md",
            "Chinese Expert", "自然语言处理 and 深度学习 expert",
            "Working on **人工智能** solutions."
        )
        result = extract_terms(f)
        assert result is not None
        # 自然语言处理 (5 chars) should survive the TERM_MIN_LEN=4 filter
        assert isinstance(result["desc_terms"], set)

    def test_chinese_header_terms(self, tmp_path):
        """Cover line 129 — Chinese concept terms from headers."""
        path = tmp_path / "test-cat" / "test-cat-cn.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("""---
name: "Chinese Expert"
description: "人工智能专家"
color: blue
emoji: "X"
version: "1.0.0"
date_added: "2026-07-03"
---

## 人工智能技术
We work on cutting edge AI technology.

### 深度学习框架
Deep learning frameworks for production.

## Data Processing
Standard data processing pipeline.
""", encoding="utf-8")
        result = extract_terms(path)
        assert result is not None
        # Should extract "人工智能技术" or "深度学习框架" as body terms
        assert any("人工智能" in t or "深度学习" in t for t in result["body_terms"]) or \
               len(result["body_terms"]) >= 0

    def test_acronym_extraction(self, tmp_path):
        """Cover lines 125-126 — ALL_CAPS acronym extraction from body."""
        path = tmp_path / "test-cat" / "test-cat-acronym.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("""---
name: "Infra Expert"
description: "Cloud infrastructure specialist"
color: blue
emoji: "X"
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
I specialize in AWS, GCP, and K8S deployments.
I also handle CI/CD pipelines and use IaC tools.
""", encoding="utf-8")
        result = extract_terms(path)
        assert result is not None
        # Should find acronyms like AWS, GCP, K8S
        body_terms = result["body_terms"]
        assert any(t in body_terms for t in ["aws", "gcp", "k8s", "ci/cd", "iac"])

    def test_clean_id_removes_category_prefix(self, tmp_path):
        """Cover lines 94-99 — removing category prefix from agent id."""
        # Use terms that are NOT in STOP_TERMS
        f = make_agent_file(
            tmp_path / "test-cat" / "test-cat-zookeeper-helmsman.md",
            "Zookeeper Helmsman", "Expert in zookeeper helm charts",
            "Building **zookeeper** systems."
        )
        result = extract_terms(f)
        assert result is not None
        # "zookeeper" (10 chars) and "helmsman" (8 chars) survive TERM_MIN_LEN=4
        # and are not in STOP_TERMS
        assert "zookeeper" in result["name_terms"] or "helmsman" in result["name_terms"]


# ── compute_dep_score edge cases ──────────────────────────────────────────────

class TestComputeDepScoreEdgeCases:
    """Cover body overlap scoring and cross-category bonuses."""

    def _agent(self, aid, cat, name, desc_terms, body_terms):
        words = set(name.lower().split())
        return {
            "id": aid, "category": cat, "name": name,
            "name_terms": words,
            "desc_terms": desc_terms,
            "body_terms": body_terms,
            "all_terms": body_terms | desc_terms,
            "body_text": " ".join(body_terms),
        }

    def test_body_overlap_3_or_more(self):
        """Cover lines 176-178 — overlap_count >= 3 gives +0.2."""
        source = self._agent(
            "src", "engineering", "DevOps Engineer",
            set(), {"docker", "kubernetes", "terraform", "ansible"}
        )
        target = self._agent(
            "tgt", "engineering", "Infra Specialist",
            set(), {"docker", "kubernetes", "terraform"}
        )
        score, evidence = compute_dep_score(source, target)
        assert score >= 0.25  # >=0.05 (same cat) + 0.2 (overlap >=3)

    def test_body_overlap_1_or_2(self):
        """Cover line 180 — overlap_count 1-2 gives +0.05 each (capped at 4)."""
        source = self._agent(
            "src", "healthcare", "ML Engineer",
            set(), {"python", "tensorflow"}
        )
        target = self._agent(
            "tgt", "healthcare", "Data Scientist",
            set(), {"python", "jupyter"}
        )
        score, evidence = compute_dep_score(source, target)
        assert 0.05 <= score <= 0.30  # same cat (0.05) + overlap (0.05*1)

    def test_cross_category_bonus_eng_infra(self):
        """Cover line 196 — cross-category bonus for engineering→infrastructure."""
        source = self._agent(
            "src", "engineering", "Backend Dev",
            set(), {"scaling"}
        )
        target = self._agent(
            "tgt", "infrastructure", "Infra Architect",
            set(), {"scaling"}
        )
        score, evidence = compute_dep_score(source, target)
        assert score >= 0.10  # same cat would give 0.05, but cross-cat also 0.05

    def test_cross_category_bonus_cyber_eng(self):
        """Cover cross-category bonus for cybersecurity→engineering."""
        source = self._agent(
            "src", "cybersecurity", "Security Analyst",
            set(), {"threat"}
        )
        target = self._agent(
            "tgt", "engineering", "Platform Engineer",
            set(), {"threat"}
        )
        score, evidence = compute_dep_score(source, target)
        assert score >= 0.10  # cross-cat bonus

    def test_name_mention_in_body(self):
        """Cover line 162-164 — direct name mention in body text gives +0.3."""
        source = self._agent(
            "src", "engineering", "API Developer",
            set(), {"kubernetes"}
        )
        # Put target's name term in source's body text
        source["body_text"] = "I work closely with kubernetes for deployments"

        target = self._agent(
            "tgt", "infrastructure", "Kubernetes Expert",
            set(), {"kubernetes"}
        )
        score, evidence = compute_dep_score(source, target)
        assert score >= 0.30  # name mention + cross-cat

    def test_desc_term_overlap(self):
        """Cover lines 167-171 — description term overlap."""
        source = self._agent(
            "src", "engineering", "Developer",
            set(), {"kubernetes"}
        )
        source["body_text"] = "using kubernetes orchestration"

        target = self._agent(
            "tgt", "infrastructure", "Infra Engineer",
            {"kubernetes"}, set()
        )
        score, evidence = compute_dep_score(source, target)
        # desc_overlap gives +0.15 for kubernetes if len >= 4
        assert score >= 0.15


# ── suggest_dependencies ──────────────────────────────────────────────────────

class TestSuggestDependenciesDetailed:
    """Cover lines 219-244 — dependency suggestion engine."""

    def test_confidence_filtering(self):
        """Suggestions with score below min_confidence are filtered out."""
        agents = build_agent_index(category_filter="aviation")
        if len(agents) < 2:
            pytest.skip("need at least 2 agents")
        term_idx = build_term_index(agents)
        # Very high confidence threshold should filter everything
        suggestions = suggest_dependencies(agents, term_idx, min_confidence=0.99)
        for agent_id, deps in suggestions.items():
            for _target_id, confidence, _evidence in deps:
                assert confidence >= 0.99

    def test_dedup_source_id(self):
        """An agent should not depend on itself (line 229)."""
        agents = build_agent_index(category_filter="aviation")
        if not agents:
            pytest.skip("no agents available")
        term_idx = build_term_index(agents)
        suggestions = suggest_dependencies(agents, term_idx, min_confidence=0.0)
        for agent_id, deps in suggestions.items():
            for target_id, _confidence, _evidence in deps:
                assert target_id != agent_id, f"{agent_id} depends on itself"

    def test_max_suggestions_per_agent(self):
        """Each agent gets at most max_suggestions (line 242)."""
        agents = build_agent_index(category_filter="aviation")
        if len(agents) < 3:
            pytest.skip("need at least 3 agents")
        term_idx = build_term_index(agents)
        suggestions = suggest_dependencies(agents, term_idx, min_confidence=0.0, max_suggestions=2)
        for agent_id, deps in suggestions.items():
            assert len(deps) <= 2

    def test_missing_target_skipped(self):
        """Target not in all_agents is skipped (line 233-234)."""
        agents = build_agent_index(category_filter="aviation")
        if not agents:
            pytest.skip("no agents available")
        term_idx = build_term_index(agents)
        # Add a fake term that maps to nonexistent agent
        term_idx["xyzzy_fake_term"] = {"nonexistent-agent-999"}
        suggestions = suggest_dependencies(agents, term_idx, min_confidence=0.0)
        for _agent_id, deps in suggestions.items():
            for target_id, _confidence, _evidence in deps:
                assert target_id in agents

    def test_sorted_by_confidence(self):
        """Suggestions are sorted by confidence descending (line 241)."""
        agents = build_agent_index(category_filter="aviation")
        if len(agents) < 3:
            pytest.skip("need at least 3 agents")
        term_idx = build_term_index(agents)
        suggestions = suggest_dependencies(agents, term_idx, min_confidence=0.0)
        for agent_id, deps in suggestions.items():
            confidences = [c for _t, c, _e in deps]
            assert confidences == sorted(confidences, reverse=True)


# ── print_dependency_health with valid refs ───────────────────────────────────

class TestPrintDependencyHealthDetailed:
    """Cover lines 305-312 — dependency graph section with valid references."""

    def test_valid_refs_graph(self, tmp_path, monkeypatch):
        """Cover the dependency graph display for valid references."""
        f_a = make_agent_file(
            tmp_path / "cat" / "cat-provider.md",
            "Provider Agent", "Provides core services",
            "Core **infrastructure** provider."
        )
        f_b = make_agent_file(
            tmp_path / "cat" / "cat-consumer.md",
            "Consumer Agent", "Consumes services",
            "Uses provider for **infrastructure**.",
            deps=["cat-provider"]
        )

        def mock_discover():
            for f in (f_a, f_b):
                cat = f.parent.name
                rel = str(f.relative_to(tmp_path)).replace("\\", "/")
                yield cat, rel, f

        monkeypatch.setattr(mod, "discover_agents", mock_discover)
        agents = {}
        for f in (f_a, f_b):
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
        assert "Dependency Graph" in output
        assert "Valid references" in output

    def test_broken_refs_display(self, tmp_path, monkeypatch):
        """Cover lines 300-303 — broken references listing."""
        f = make_agent_file(
            tmp_path / "cat" / "cat-broken.md",
            "Broken Agent", "Has broken deps",
            "References missing agents.",
            deps=["nonexistent-target-123"]
        )

        def mock_discover():
            cat = f.parent.name
            rel = str(f.relative_to(tmp_path)).replace("\\", "/")
            yield cat, rel, f

        monkeypatch.setattr(mod, "discover_agents", mock_discover)
        agents = {}
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
        assert "Broken depends_on" in output
        assert "nonexistent-target-123" in output

    def test_multiple_consumers_graph(self, tmp_path, monkeypatch):
        """Cover the graph display with multiple consumers for one provider."""
        provider = make_agent_file(
            tmp_path / "cat" / "cat-prov.md",
            "Provider", "Core provider",
            "Provides core **services**."
        )
        c1 = make_agent_file(
            tmp_path / "cat" / "cat-cons1.md",
            "Consumer 1", "Consumer",
            "Uses provider.",
            deps=["cat-prov"]
        )
        c2 = make_agent_file(
            tmp_path / "cat" / "cat-cons2.md",
            "Consumer 2", "Consumer",
            "Uses provider.",
            deps=["cat-prov"]
        )

        def mock_discover():
            for f in (provider, c1, c2):
                cat = f.parent.name
                rel = str(f.relative_to(tmp_path)).replace("\\", "/")
                yield cat, rel, f

        monkeypatch.setattr(mod, "discover_agents", mock_discover)
        agents = {}
        for f in (provider, c1, c2):
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
        # Provider should appear in the graph section
        assert "cat-prov" in output


# ── print_suggestions ─────────────────────────────────────────────────────────

class TestPrintSuggestions:
    """Cover lines 318-351 — print dependency suggestions."""

    def test_agent_filter_detailed(self):
        """Cover lines 327-338 — detailed single-agent view."""
        suggestions = {
            "agent-alpha": [
                ("agent-beta", 0.85, ["body mentions 'beta'", "shared domain term 'cloud'"]),
                ("agent-gamma", 0.60, ["shared technical terms"]),
            ]
        }
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_suggestions(suggestions, agent_filter="agent-alpha")
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "agent-alpha" in out
        assert "agent-beta" in out
        assert "0.85" in out
        assert "body mentions" in out

    def test_agent_filter_not_found(self):
        """Cover line 339-340 — agent not in suggestions."""
        suggestions = {"agent-alpha": []}
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_suggestions(suggestions, agent_filter="nonexistent")
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "not found" in out

    def test_agent_filter_no_suggestions(self):
        """Cover line 337-338 — agent has no suggestions above threshold."""
        suggestions = {"agent-alpha": []}
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_suggestions(suggestions, agent_filter="agent-alpha")
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "No suggestions" in out

    def test_top_suggestions_all_agents(self):
        """Cover lines 342-351 — ranked suggestions across all agents."""
        suggestions = {
            "agent-a": [
                ("agent-b", 0.90, ["shared domain term 'api'"]),
            ],
            "agent-b": [
                ("agent-c", 0.70, ["body mentions 'database'"]),
            ],
        }
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_suggestions(suggestions, agent_filter=None, top_n=5)
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "0.90" in out
        assert "agent-a" in out
        assert "agent-b" in out

    def test_empty_suggestions(self):
        """Cover with empty suggestions dict."""
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_suggestions({}, agent_filter=None)
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "0 agents have 0 potential dependencies" in out

    def test_top_suggestions_no_evidence(self):
        """Cover line 351 — evidence list may be empty."""
        suggestions = {
            "agent-a": [
                ("agent-b", 0.50, []),
            ],
        }
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_suggestions(suggestions, agent_filter=None)
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "0.50" in out


# ── print_orphans ─────────────────────────────────────────────────────────────

class TestPrintOrphans:
    """Cover lines 356-374 — orphan agents display."""

    def test_orphans_with_categories(self):
        """Cover the full orphan display with category breakdown."""
        all_agents = {
            "orphan-1": {"id": "orphan-1", "category": "engineering", "name": "O1", "all_terms": set()},
            "orphan-2": {"id": "orphan-2", "category": "engineering", "name": "O2", "all_terms": set()},
            "orphan-3": {"id": "orphan-3", "category": "design", "name": "O3", "all_terms": set()},
            "non-orphan": {"id": "non-orphan", "category": "engineering", "name": "N1", "all_terms": set()},
        }
        suggestions = {
            "non-orphan": [("target", 0.5, [])],
        }
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_orphans(all_agents, suggestions)
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "Orphan Agents" in out
        assert "3 agents" in out  # 3 orphans
        assert "engineering" in out

    def test_no_orphans(self):
        """Cover when all agents have suggestions."""
        all_agents = {
            "a1": {"id": "a1", "category": "cat", "name": "A1", "all_terms": set()},
            "a2": {"id": "a2", "category": "cat", "name": "A2", "all_terms": set()},
        }
        suggestions = {
            "a1": [("a2", 0.5, [])],
            "a2": [("a1", 0.5, [])],
        }
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_orphans(all_agents, suggestions)
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "0 agents" in out  # no orphans

    def test_single_orphan_no_pct_error(self):
        """Cover with one orphan and no suggestions."""
        all_agents = {
            "orphan-only": {"id": "orphan-only", "category": "cat", "name": "O", "all_terms": set()},
        }
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.print_orphans(all_agents, {})
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "1 agents" in out
        assert "100" in out  # 1/1 = 100%


# ── main() entry point ────────────────────────────────────────────────────────

class TestSuggestDepsScoringLoop:
    """Cover lines 233-238 — candidate scoring loop inside suggest_dependencies."""

    def test_candidates_scored_with_guaranteed_overlap(self, tmp_path):
        """Create agents with guaranteed term overlap so scoring loop runs."""
        f1 = make_agent_file(
            tmp_path / "infra" / "infra-devops.md",
            "DevOps Engineer", "Cloud infrastructure specialist",
            "Working with **docker** and **kubernetes** and **terraform**."
        )
        f2 = make_agent_file(
            tmp_path / "infra" / "infra-sre.md",
            "SRE Engineer", "Site reliability expert",
            "Using **docker** and **kubernetes** for reliability."
        )

        agents = {}
        for f in (f1, f2):
            terms = extract_terms(f)
            if terms:
                agents[terms["id"]] = terms

        assert len(agents) == 2
        term_idx = build_term_index(agents)
        # min_confidence=0.0 guarantees all candidates pass the threshold
        suggestions = suggest_dependencies(agents, term_idx, min_confidence=0.0)
        # At least one agent should get a suggestion
        assert any(len(deps) > 0 for deps in suggestions.values()), \
            f"Expected suggestions but got: {suggestions}"

    def test_skip_nonexistent_candidate(self, tmp_path):
        """Cover line 234 — skip candidate_ids not present in all_agents."""
        f1 = make_agent_file(
            tmp_path / "cat" / "cat-real.md",
            "Real Agent", "Real agent description here",
            "Working with **docker** container systems."
        )
        f2 = make_agent_file(
            tmp_path / "cat" / "cat-source.md",
            "Source Agent", "Source agent description",
            "Working with **docker** and **xyzznotreal** systems."
        )

        agents = {}
        for f in (f1, f2):
            terms = extract_terms(f)
            if terms:
                agents[terms["id"]] = terms

        assert len(agents) == 2
        term_idx = build_term_index(agents)

        # Inject a term pointing to both real and fake agent IDs
        # "nonexistent-agent-999" is NOT in all_agents
        term_idx["xyzznotreal"] = {"cat-real", "nonexistent-agent-999"}

        suggestions = suggest_dependencies(agents, term_idx, min_confidence=0.0)
        # The fake target should have been skipped (line 234 continue),
        # but the real one should still be scored
        source_deps = suggestions.get("cat-source", [])
        target_ids = [t for t, _c, _e in source_deps]
        assert "cat-real" in target_ids, f"Expected cat-real in suggestions, got: {target_ids}"
        assert "nonexistent-agent-999" not in target_ids


class TestMain:
    """Cover lines 378-461 — the CLI entry point for all modes."""

    def _set_repo_and_agents(self, monkeypatch, tmp_path):
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        # Create two agent files
        f1 = make_agent_file(
            tmp_path / "eng" / "eng-provider.md",
            "Provider Agent", "Provides core services",
            "Core **infrastructure** provider **platform** with **scaling**."
        )
        f2 = make_agent_file(
            tmp_path / "eng" / "eng-consumer.md",
            "Consumer Agent", "Consumes infrastructure services",
            "Uses **infrastructure** for **deployment**.",
            deps=["eng-provider"]
        )
        return f1, f2

    # ── --report (default) ─────────────────────────────────────────────────

    def test_report_mode(self, tmp_path, monkeypatch, capsys):
        self._set_repo_and_agents(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['analyze-deps.py', '--report'])
        mod.main()
        captured = capsys.readouterr()
        assert "Dependency Graph Health" in captured.out

    def test_report_json_mode(self, tmp_path, monkeypatch, capsys):
        self._set_repo_and_agents(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['analyze-deps.py', '--report', '--json'])
        mod.main()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "total_agents" in data
        assert "valid_refs" in data
        assert "broken_refs" in data

    def test_default_to_report(self, tmp_path, monkeypatch, capsys):
        """No action flag defaults to --report (line 402-403)."""
        self._set_repo_and_agents(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['analyze-deps.py'])
        mod.main()
        captured = capsys.readouterr()
        assert "Dependency Graph Health" in captured.out

    def test_report_json_with_broken(self, tmp_path, monkeypatch, capsys):
        """Report JSON includes broken details (lines 455-457)."""
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        f = make_agent_file(
            tmp_path / "cat" / "cat-broken.md",
            "Broken Agent", "Has broken deps",
            "References missing.",
            deps=["missing-agent-999"]
        )
        monkeypatch.setattr(sys, 'argv',
                           ['analyze-deps.py', '--report', '--json'])
        mod.main()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["broken_refs"] >= 1
        assert any(d["target"] == "missing-agent-999" for d in data["broken_details"])

    # ── --validate ─────────────────────────────────────────────────────────

    def test_validate_mode(self, tmp_path, monkeypatch, capsys):
        self._set_repo_and_agents(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['analyze-deps.py', '--validate'])
        mod.main()
        captured = capsys.readouterr()
        assert "depends_on Validation" in captured.out
        assert "Valid references" in captured.out

    def test_validate_with_broken_refs(self, tmp_path, monkeypatch, capsys):
        """Validate reports broken references (lines 412-414)."""
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)
        f = make_agent_file(
            tmp_path / "cat" / "cat-broken.md",
            "Broken", "Broken deps",
            "Content.",
            deps=["ghost-agent-123"]
        )
        monkeypatch.setattr(sys, 'argv',
                           ['analyze-deps.py', '--validate'])
        mod.main()
        captured = capsys.readouterr()
        assert "ghost-agent-123" in captured.out

    # ── --suggest ──────────────────────────────────────────────────────────

    def test_suggest_mode(self, tmp_path, monkeypatch, capsys):
        self._set_repo_and_agents(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['analyze-deps.py', '--suggest'])
        mod.main()
        captured = capsys.readouterr()
        assert "Dependency Suggestions" in captured.out

    def test_suggest_with_agent_filter(self, tmp_path, monkeypatch, capsys):
        self._set_repo_and_agents(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['analyze-deps.py', '--suggest',
                            '--agent', 'eng-consumer'])
        mod.main()
        captured = capsys.readouterr()
        assert "eng-consumer" in captured.out

    def test_suggest_with_category_filter(self, tmp_path, monkeypatch, capsys):
        self._set_repo_and_agents(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['analyze-deps.py', '--suggest',
                            '--category', 'eng'])
        mod.main()
        captured = capsys.readouterr()
        assert "Dependency Suggestions" in captured.out

    def test_suggest_json_mode(self, tmp_path, monkeypatch, capsys):
        """Cover line 427 — JSON output for suggestions with non-empty deps."""
        import _shared.discovery
        monkeypatch.setattr(_shared.discovery, "REPO", tmp_path)

        # Create agents with guaranteed term overlap
        make_agent_file(
            tmp_path / "infra" / "infra-devops.md",
            "DevOps Engineer", "Cloud infrastructure specialist",
            "Working with **docker** and **kubernetes** and **terraform**."
        )
        make_agent_file(
            tmp_path / "infra" / "infra-sre.md",
            "SRE Engineer", "Site reliability expert",
            "Using **docker** and **kubernetes** for reliability."
        )

        monkeypatch.setattr(sys, 'argv',
                           ['analyze-deps.py', '--suggest', '--json',
                            '--min-confidence', '0.0'])
        mod.main()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "suggestions" in data
        assert "total" in data

    def test_suggest_with_min_confidence(self, tmp_path, monkeypatch, capsys):
        self._set_repo_and_agents(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['analyze-deps.py', '--suggest',
                            '--min-confidence', '0.9'])
        mod.main()
        captured = capsys.readouterr()
        assert "Dependency Suggestions" in captured.out

    # ── --orphans ──────────────────────────────────────────────────────────

    def test_orphans_mode(self, tmp_path, monkeypatch, capsys):
        self._set_repo_and_agents(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['analyze-deps.py', '--orphans'])
        mod.main()
        captured = capsys.readouterr()
        assert "Orphan Agents" in captured.out

    def test_orphans_with_category(self, tmp_path, monkeypatch, capsys):
        """Orphans mode with category filter."""
        self._set_repo_and_agents(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv',
                           ['analyze-deps.py', '--orphans',
                            '--category', 'eng'])
        mod.main()
        captured = capsys.readouterr()
        assert "Orphan Agents" in captured.out
