"""Tests for scripts/check-dupes.py — near-duplicate agent detection."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "check_dupes", str(SCRIPTS_DIR / "check-dupes.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

find_duplicates = mod.find_duplicates

MOCK_AGENTS = [
    {"id": "a1", "name": "Frontend Developer", "description": "React expert",
     "category": "engineering"},
    {"id": "a2", "name": "Frontend Developer", "description": "React expert",
     "category": "engineering"},
    {"id": "a3", "name": "Front-End Developer", "description": "React and Vue.js specialist",
     "category": "engineering"},
    {"id": "a4", "name": "Security Analyst", "description": "Threat detection expert",
     "category": "cybersecurity"},
    {"id": "a5", "name": "ML Engineer", "description": "Machine learning deep learning",
     "category": "data-science"},
]


class TestFindDuplicates:
    def test_identical_agents_flagged(self):
        pairs = find_duplicates(MOCK_AGENTS, threshold=0.85)
        assert len(pairs) >= 1
        ids = {p[3]["id"] for p in pairs} | {p[4]["id"] for p in pairs}
        assert "a1" in ids and "a2" in ids

    def test_threshold_filters_out_low_similarity(self):
        # At 0.98 threshold, only near-identical pairs should match.
        # a1-a2 has composite=1.0, a1-a3 composite should be < 0.98
        pairs = find_duplicates(MOCK_AGENTS, threshold=0.98)
        assert len(pairs) == 1
        matched = {pairs[0][3]["id"], pairs[0][4]["id"]}
        assert matched == {"a1", "a2"}

    def test_no_matches_at_max_threshold(self):
        agents = [
            {"id": "x1", "name": "Similar A", "description": "d1",
             "category": "test"},
            {"id": "x2", "name": "Similar B", "description": "d2",
             "category": "test"},
        ]
        pairs = find_duplicates(agents, threshold=0.99)
        assert len(pairs) == 0

    def test_high_threshold_still_catches_exact_dupes(self):
        agents = [
            {"id": "x1", "name": "Exact Match", "description": "Same desc",
             "category": "test"},
            {"id": "x2", "name": "Exact Match", "description": "Same desc",
             "category": "test"},
        ]
        pairs = find_duplicates(agents, threshold=1.0)
        assert len(pairs) == 1
        assert pairs[0][0] == 1.0

    def test_category_filter(self):
        pairs = find_duplicates(MOCK_AGENTS, threshold=0.85, category_filter="cybersecurity")
        assert len(pairs) == 0

    def test_empty_agents(self):
        pairs = find_duplicates([], threshold=0.85)
        assert pairs == []

    def test_single_agent(self):
        pairs = find_duplicates(MOCK_AGENTS[:1], threshold=0.85)
        assert pairs == []

    def test_composite_weighting(self):
        """Name similarity (0.6) should dominate desc similarity (0.4)."""
        agents = [
            {"id": "y1", "name": "Identical Name", "description": "Totally different A",
             "category": "test"},
            {"id": "y2", "name": "Identical Name", "description": "Totally different B",
             "category": "test"},
        ]
        pairs = find_duplicates(agents, threshold=0.50)
        assert len(pairs) == 1
        assert pairs[0][1] == 1.0  # name_ratio = 1.0

    def test_result_sort_order(self):
        pairs = find_duplicates(MOCK_AGENTS, threshold=0.50)
        for i in range(len(pairs) - 1):
            assert pairs[i][0] >= pairs[i + 1][0]


class TestMainFunction:
    """Tests for the main() CLI entry point."""

    def _make_index(self, tmp_path, agents=None):
        index_path = tmp_path / "AGENTS.json"
        index_path.write_text(json.dumps({"agents": agents or []}), encoding="utf-8")
        return index_path

    def test_no_duplicates(self, tmp_path, monkeypatch, capsys):
        index_path = self._make_index(tmp_path, [
            {"id": "a1", "name": "Alpha", "description": "First", "category": "test"},
            {"id": "a2", "name": "Beta", "description": "Second", "category": "test"},
        ])
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        with patch.object(sys, "argv", ["check-dupes.py", "--threshold", "0.90"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 0
        assert "No duplicate pairs found" in capsys.readouterr().out

    def test_finds_duplicates(self, tmp_path, monkeypatch, capsys):
        index_path = self._make_index(tmp_path, [
            {"id": "a1", "name": "Frontend Dev", "description": "React", "category": "eng"},
            {"id": "a2", "name": "Frontend Dev", "description": "React", "category": "eng"},
        ])
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        with patch.object(sys, "argv", ["check-dupes.py", "--threshold", "0.85"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1
        assert "flagged for review" in capsys.readouterr().out

    def test_json_output(self, tmp_path, monkeypatch, capsys):
        index_path = self._make_index(tmp_path, [
            {"id": "a1", "name": "Frontend Dev", "description": "React", "category": "eng"},
            {"id": "a2", "name": "Frontend Dev", "description": "React", "category": "eng"},
        ])
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        with patch.object(sys, "argv", ["check-dupes.py", "--threshold", "0.85", "--json"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1
        output = json.loads(capsys.readouterr().out)
        assert len(output) == 1
        assert output[0]["agent_a"] == "a1"

    def test_category_filter(self, tmp_path, monkeypatch, capsys):
        index_path = self._make_index(tmp_path, [
            {"id": "a1", "name": "Dev", "description": "x", "category": "eng"},
            {"id": "a2", "name": "Dev", "description": "x", "category": "sci"},
        ])
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        with patch.object(sys, "argv",
                          ["check-dupes.py", "--threshold", "0.85", "--category", "eng"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 0

    def test_missing_index(self, tmp_path, monkeypatch, capsys):
        index_path = tmp_path / "nonexistent.json"
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        with patch.object(sys, "argv", ["check-dupes.py"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1
        assert "not found" in capsys.readouterr().out

    def test_json_output_no_pairs(self, tmp_path, monkeypatch, capsys):
        index_path = self._make_index(tmp_path, [
            {"id": "a1", "name": "Alpha", "description": "First", "category": "test"},
        ])
        monkeypatch.setattr(mod, "INDEX_PATH", index_path)
        with patch.object(sys, "argv", ["check-dupes.py", "--json"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 0
        assert json.loads(capsys.readouterr().out) == []
