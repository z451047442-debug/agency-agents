"""Tests for scripts/analyze-deps-auto.py dependency detection logic."""
import importlib.util
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
spec = importlib.util.spec_from_file_location(
    "analyze_deps_auto", str(SCRIPTS_DIR / "analyze-deps-auto.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

extract_keywords = mod.extract_keywords
find_agent_file = mod.find_agent_file
load_agents = mod.load_agents


class TestExtractKeywords:
    def test_extracts_english_tokens(self):
        result = extract_keywords("Big Query Pipeline Engineer", "")
        assert "big" in result
        assert "query" in result
        assert "pipeline" in result
        assert "engineer" in result

    def test_extracts_chinese_tokens(self):
        result = extract_keywords("数据工程师", "")
        # Chinese tokens extracted
        assert len(result) > 0

    def test_filters_stop_words(self):
        result = extract_keywords("the and for with", "")
        assert "the" not in result
        assert "and" not in result
        assert "for" not in result

    def test_filters_short_tokens(self):
        result = extract_keywords("a b c ab cd", "")
        assert "a" not in result
        assert "ab" not in result  # 2 chars, < minimum 3
        assert "cd" not in result  # 2 chars

    def test_handles_empty_input(self):
        assert extract_keywords("", "") == set()

    def test_name_and_description_combined(self):
        result = extract_keywords("Jenkins Expert", "CI/CD pipeline automation")
        assert "jenkins" in result
        assert "pipeline" in result

    def test_generic_stopwords_removed(self):
        result = extract_keywords("Manager Platform", "support system data service management")
        assert "manager" not in result
        assert "platform" not in result
        assert "management" not in result


class TestFindAgentFile:
    def test_nonexistent_returns_none(self):
        assert find_agent_file("definitely-non-existent-agent-id-999999") is None

    def test_real_agent_exists(self):
        path = find_agent_file("engineering-frontend-developer")
        assert path is not None
        assert path.name == "engineering-frontend-developer.md"


class TestLoadAgents:
    def test_returns_list(self):
        agents = load_agents()
        assert isinstance(agents, list)
        assert len(agents) > 0

    def test_each_agent_has_required_fields(self):
        agents = load_agents()
        for a in agents[:5]:
            assert "id" in a
            assert "name" in a
            assert "category" in a
            assert "description" in a


class TestMainFunction:
    def test_main_runs_without_error(self):
        # Should not raise
        mod.main()
