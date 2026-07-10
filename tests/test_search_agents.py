"""Tests for scripts/search-agents.py — agent search engine."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "search_agents", str(SCRIPTS_DIR / "search-agents.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

search_agents = mod.search_agents
print_stats = mod.print_stats
print_categories = mod.print_categories
print_results = mod.print_results
print_json_results = mod.print_json_results

MOCK_DATA = {
    "agents": [
        {"id": "engineering-frontend-dev", "name": "Frontend Developer",
         "description": "React and Vue.js expert", "category": "engineering"},
        {"id": "engineering-backend-dev", "name": "Backend Developer",
         "description": "Python and Go backend specialist", "category": "engineering"},
        {"id": "data-science-ml-engineer", "name": "ML Engineer",
         "description": "Machine learning and deep learning expert", "category": "data-science"},
        {"id": "cybersecurity-analyst", "name": "Security Analyst",
         "description": "Threat detection and incident response", "category": "cybersecurity"},
    ]
}


class TestSearchAgents:
    def test_keyword_search(self):
        results = search_agents(MOCK_DATA, query="react")
        assert len(results) == 1
        assert results[0]["id"] == "engineering-frontend-dev"

    def test_case_insensitive(self):
        results = search_agents(MOCK_DATA, query="REACT")
        assert len(results) == 1

    def test_and_search(self):
        results = search_agents(MOCK_DATA, query="machine learning")
        assert len(results) == 1
        assert results[0]["id"] == "data-science-ml-engineer"

    def test_category_filter(self):
        results = search_agents(MOCK_DATA, category="engineering")
        assert len(results) == 2
        for r in results:
            assert r["category"] == "engineering"

    def test_category_and_keyword(self):
        results = search_agents(MOCK_DATA, query="react", category="engineering")
        assert len(results) == 1

    def test_field_specific(self):
        results = search_agents(MOCK_DATA, query="ML", field="name")
        assert len(results) == 1

    def test_regex_search(self):
        results = search_agents(MOCK_DATA, query=r"frontend|backend", regex=True)
        assert len(results) == 2

    def test_no_query_returns_all(self):
        results = search_agents(MOCK_DATA)
        assert len(results) == 4

    def test_no_matches(self):
        results = search_agents(MOCK_DATA, query="nonexistent_xyz")
        assert len(results) == 0

    def test_search_in_description(self):
        results = search_agents(MOCK_DATA, query="threat detection")
        assert len(results) == 1

    def test_search_in_id(self):
        results = search_agents(MOCK_DATA, query="backend-dev")
        assert len(results) == 1


# ── print_stats ──────────────────────────────────────────────────────────────

class TestPrintStats:
    def test_shows_total_agents(self, capsys):
        data = {
            "total_agents": 4,
            "total_categories": 3,
            "generated": "2026-01-01",
            "agents": MOCK_DATA["agents"],
        }
        print_stats(data)
        captured = capsys.readouterr()
        assert "4" in captured.out

    def test_shows_categories_count(self, capsys):
        data = {
            "total_agents": 4,
            "total_categories": 3,
            "generated": "2026-01-01",
            "agents": MOCK_DATA["agents"],
        }
        print_stats(data)
        captured = capsys.readouterr()
        assert "3" in captured.out

    def test_shows_generated_date(self, capsys):
        data = {
            "total_agents": 4,
            "total_categories": 3,
            "generated": "2026-01-01",
            "agents": MOCK_DATA["agents"],
        }
        print_stats(data)
        captured = capsys.readouterr()
        assert "2026-01-01" in captured.out

    def test_shows_top_categories(self, capsys):
        data = {
            "total_agents": 4,
            "total_categories": 3,
            "generated": "2026-01-01",
            "agents": MOCK_DATA["agents"],
        }
        print_stats(data)
        captured = capsys.readouterr()
        assert "engineering" in captured.out.lower()
        assert "data-science" in captured.out

    def test_shows_emoji_section(self, capsys):
        data = {
            "total_agents": 2,
            "generated": "2026-01-01",
            "agents": [
                {"id": "a", "name": "A", "category": "eng", "emoji": "X"},
                {"id": "b", "name": "B", "category": "eng", "emoji": "Y"},
            ],
        }
        print_stats(data)
        captured = capsys.readouterr()
        assert "X" in captured.out
        assert "Y" in captured.out

    def test_nexus_roles_stat(self, capsys):
        data = {
            "total_agents": 2,
            "generated": "2026-01-01",
            "agents": [
                {"id": "a", "name": "A", "category": "eng", "nexus_roles": ["p1"]},
                {"id": "b", "name": "B", "category": "eng"},
            ],
        }
        print_stats(data)
        captured = capsys.readouterr()
        assert "With nexus_roles" in captured.out
        assert "50%" in captured.out


# ── print_categories ─────────────────────────────────────────────────────────

class TestPrintCategories:
    def test_shows_all_categories(self, capsys):
        data = {"total_agents": 4, "agents": MOCK_DATA["agents"]}
        print_categories(data)
        captured = capsys.readouterr()
        assert "engineering" in captured.out
        assert "data-science" in captured.out
        assert "cybersecurity" in captured.out

    def test_shows_agent_counts(self, capsys):
        data = {"total_agents": 4, "agents": MOCK_DATA["agents"]}
        print_categories(data)
        captured = capsys.readouterr()
        # engineering has 2 agents
        assert "2" in captured.out


# ── print_results ────────────────────────────────────────────────────────────

class TestPrintResults:
    def test_empty_results(self, capsys):
        print_results([])
        captured = capsys.readouterr()
        assert "No agents found" in captured.out

    def test_single_result(self, capsys):
        results = [MOCK_DATA["agents"][0]]
        print_results(results)
        captured = capsys.readouterr()
        assert "1 agent" in captured.out

    def test_shows_agent_name(self, capsys):
        results = [MOCK_DATA["agents"][0]]
        print_results(results)
        captured = capsys.readouterr()
        assert "Frontend Developer" in captured.out

    def test_pagination_single_page(self, capsys):
        results = MOCK_DATA["agents"]  # 4 items, 25 per page
        print_results(results, page=1, per_page=25)
        captured = capsys.readouterr()
        assert "4 agent" in captured.out

    def test_pagination_multi_page(self, capsys):
        # Create 30 results — should paginate at 10 per page
        results = [MOCK_DATA["agents"][0]] * 30
        print_results(results, page=1, per_page=10)
        captured = capsys.readouterr()
        assert "Page 1/3" in captured.out
        assert "Next: --page 2" in captured.out

    def test_page_out_of_bounds_clamped(self, capsys):
        results = [MOCK_DATA["agents"][0]] * 5
        print_results(results, page=99, per_page=3)
        captured = capsys.readouterr()
        # Clamped to last page (page 2 of 2)
        assert "Page 2/2" in captured.out
        assert "Next:" not in captured.out


# ── print_json_results ───────────────────────────────────────────────────────

class TestPrintJsonResults:
    def test_outputs_valid_json(self, capsys):
        results = MOCK_DATA["agents"][:2]
        print_json_results(results)
        captured = capsys.readouterr()
        import json
        parsed = json.loads(captured.out)
        assert parsed["total"] == 2
        assert len(parsed["results"]) == 2

    def test_empty_results(self, capsys):
        print_json_results([])
        captured = capsys.readouterr()
        import json
        parsed = json.loads(captured.out)
        assert parsed["total"] == 0


# ── load_index ─────────────────────────────────────────────────────────────

class TestLoadIndex:
    def test_file_not_found_exits(self, monkeypatch):
        """load_index exits when AGENTS.json is missing (lines 35-39)."""
        monkeypatch.setattr(mod, "INDEX_PATH", Path("/nonexistent/AGENTS.json"))
        with pytest.raises(SystemExit) as exc:
            mod.load_index()
        assert exc.value.code == 1


# ── search_agents edge cases ───────────────────────────────────────────────

class TestSearchAgentsEdge:
    def test_regex_field_search(self):
        """Field-specific regex search (line 60-61)."""
        results = mod.search_agents(
            MOCK_DATA, query=r"^React", field="description", regex=True,
        )
        assert len(results) == 1
        assert results[0]["id"] == "engineering-frontend-dev"

    def test_regex_field_search_no_match(self):
        """Field-specific regex with no match."""
        results = mod.search_agents(
            MOCK_DATA, query=r"^xyz", field="name", regex=True,
        )
        assert len(results) == 0

    def test_field_search_non_regex(self):
        """Field-specific non-regex search (already covered but tests both branches)."""
        results = mod.search_agents(
            MOCK_DATA, query="ML", field="name", regex=False,
        )
        assert len(results) == 1


# ── stdout encoding ────────────────────────────────────────────────────────

class TestStdoutEncoding:
    def test_reconfigure_on_non_utf8(self, monkeypatch):
        """Cover line 29: sys.stdout.reconfigure when encoding != utf-8."""
        import io

        class MockStdout(io.StringIO):
            encoding = "ascii"
            def reconfigure(self, **kwargs):
                pass

        fake_stdout = MockStdout()
        monkeypatch.setattr(sys, "stdout", fake_stdout)
        # Re-execute the module code to trigger the encoding check
        import importlib.util
        spec2 = importlib.util.spec_from_file_location(
            "search_agents_enc", str(SCRIPTS_DIR / "search-agents.py")
        )
        mod2 = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(mod2)


# ── main ───────────────────────────────────────────────────────────────────

class TestMain:
    def _setup_index(self, tmp_path, monkeypatch, agents=None):
        index_path = tmp_path / "AGENTS.json"
        if agents is None:
            agents = MOCK_DATA["agents"]
        data = {
            "total_agents": len(agents),
            "total_categories": 3,
            "generated": "2026-01-01",
            "agents": agents,
        }
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        return index_path

    def test_stats_mode(self, tmp_path, monkeypatch, capsys):
        self._setup_index(tmp_path, monkeypatch)
        monkeypatch.setattr("sys.argv", ["search-agents.py", "--stats"])
        mod.main()
        captured = capsys.readouterr()
        assert "Total agents" in captured.out

    def test_list_categories_mode(self, tmp_path, monkeypatch, capsys):
        self._setup_index(tmp_path, monkeypatch)
        monkeypatch.setattr("sys.argv", ["search-agents.py", "--list-categories"])
        mod.main()
        captured = capsys.readouterr()
        assert "categories" in captured.out

    def test_search_with_query(self, tmp_path, monkeypatch, capsys):
        self._setup_index(tmp_path, monkeypatch)
        monkeypatch.setattr("sys.argv", ["search-agents.py", "react"])
        mod.main()
        captured = capsys.readouterr()
        assert "1 agent" in captured.out

    def test_search_with_category_only(self, tmp_path, monkeypatch, capsys):
        self._setup_index(tmp_path, monkeypatch)
        monkeypatch.setattr(
            "sys.argv", ["search-agents.py", "--category", "engineering"]
        )
        mod.main()
        captured = capsys.readouterr()
        assert "engineering" in captured.out

    def test_search_with_query_and_category(self, tmp_path, monkeypatch, capsys):
        """Query + category prints combined context (line 221-222)."""
        self._setup_index(tmp_path, monkeypatch)
        monkeypatch.setattr(
            "sys.argv", ["search-agents.py", "react", "--category", "engineering"]
        )
        mod.main()
        captured = capsys.readouterr()
        assert "react" in captured.out

    def test_invalid_field_exits(self, tmp_path, monkeypatch):
        self._setup_index(tmp_path, monkeypatch)
        monkeypatch.setattr(
            "sys.argv",
            ["search-agents.py", "--field", "invalid_field", "query"],
        )
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 1

    def test_json_output_mode(self, tmp_path, monkeypatch, capsys):
        self._setup_index(tmp_path, monkeypatch)
        monkeypatch.setattr(
            "sys.argv", ["search-agents.py", "--json", "react"]
        )
        mod.main()
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["total"] == 1

    def test_pagination_next_hint(self, tmp_path, monkeypatch, capsys):
        """Pagination shows 'Next: --page N' hint (line 150-151)."""
        agents = [MOCK_DATA["agents"][0]] * 30
        self._setup_index(tmp_path, monkeypatch, agents=agents)
        monkeypatch.setattr(
            "sys.argv",
            ["search-agents.py", "frontend", "--per-page", "10"],
        )
        mod.main()
        captured = capsys.readouterr()
        assert "Next:" in captured.out

    def test_no_results_message(self, tmp_path, monkeypatch, capsys):
        self._setup_index(tmp_path, monkeypatch)
        monkeypatch.setattr(
            "sys.argv", ["search-agents.py", "nonexistent_xyz123"]
        )
        mod.main()
        captured = capsys.readouterr()
        assert "No agents found" in captured.out

    def test_page_clamped(self, tmp_path, monkeypatch, capsys):
        """Page out of bounds is clamped (line 128)."""
        agents = [MOCK_DATA["agents"][0]] * 5
        self._setup_index(tmp_path, monkeypatch, agents=agents)
        monkeypatch.setattr(
            "sys.argv",
            ["search-agents.py", "frontend", "--page", "99", "--per-page", "3"],
        )
        mod.main()
        captured = capsys.readouterr()
        assert "Page 2/2" in captured.out
