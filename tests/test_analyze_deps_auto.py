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


# ── find_agent_file: special directories fallback (line 48) ─────────────────

class TestFindAgentFileSpecial:
    """Test the special-directory fallback path (line 48)."""

    def test_find_in_special_directory(self, tmp_path, monkeypatch):
        """Line 48: agent found in special directory when first loop finds nothing."""
        # Create the special directory with an agent file
        lib_dir = tmp_path / "libraries"
        lib_dir.mkdir()
        (lib_dir / "libraries-test.md").write_text("", encoding="utf-8")

        # Also create an excluded dir so first loop has something to iterate
        (tmp_path / "docs").mkdir()

        monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

        # Mock iterdir to only return "docs" (excluded) — first loop finds nothing
        original_iterdir = tmp_path.__class__.iterdir

        def _mock_iterdir(self):
            for entry in original_iterdir(self):
                if entry.name == "docs":
                    yield entry

        monkeypatch.setattr(tmp_path.__class__, "iterdir", _mock_iterdir)

        result = find_agent_file("libraries-test")
        assert result is not None
        assert result.name == "libraries-test.md"

    def test_special_dir_not_found_returns_none(self, tmp_path, monkeypatch):
        """Special directories exist but agent file not present — returns None."""
        (tmp_path / "docs").mkdir()
        (tmp_path / "libraries").mkdir()

        monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
        original_iterdir = tmp_path.__class__.iterdir

        def _mock_iterdir(self):
            for entry in original_iterdir(self):
                if entry.name == "docs":
                    yield entry

        monkeypatch.setattr(tmp_path.__class__, "iterdir", _mock_iterdir)

        result = find_agent_file("nonexistent-agent")
        assert result is None


# ── main() function with mocked data ────────────────────────────────────────

class TestMainFunctionFull:
    """Tests covering the main() processing loop (lines 95-155, 176-181)."""

    def test_main_with_agents_without_deps(self, tmp_path, monkeypatch, capsys):
        """Full main() run with agents missing depends_on, covering all branches."""
        eng_dir = tmp_path / "engineering"
        eng_dir.mkdir()

        test_agents = [
            {
                "id": "eng-etl", "name": "ETL Pipeline Engineer",
                "category": "engineering",
                "description": "data pipeline etl developer",
                "depends_on": [],
            },
            {
                "id": "eng-platform",
                "name": "Platform Developer",
                "category": "engineering",
                "description": "infrastructure kubernetes docker container developer",
                "depends_on": [],
            },
            {
                "id": "eng-ml",
                "name": "Machine Learning Engineer",
                "category": "engineering",
                "description": "machine learning python tensorflow engineer",
                "depends_on": [],
            },
            {
                "id": "eng-sre",
                "name": "Site Reliability Engineer",
                "category": "engineering",
                "description": "sre kubernetes docker container reliability monitoring engineer",
                "depends_on": [],
            },
            {
                "id": "eng-no-file",
                "name": "No File Agent",
                "category": "engineering",
                "description": "no file agent",
                "depends_on": [],
            },
            {
                "id": "eng-bad-fm",
                "name": "Bad Frontmatter Agent",
                "category": "engineering",
                "description": "bad frontmatter agent",
                "depends_on": [],
            },
        ]

        # eng-etl body: many keyword overlaps for HIGH confidence with eng-platform
        (eng_dir / "eng-etl.md").write_text(
            "---\nname: etl\n---\n\n"
            "ETL pipeline engineer working with kubernetes docker container infrastructure "
            "kubernetes container docker kubernetes platform developer tools for data processing "
            "kubernetes docker machine learning tensorflow python developer",
            encoding="utf-8"
        )

        # eng-ml body: moderate keyword overlap for MEDIUM confidence
        (eng_dir / "eng-ml.md").write_text(
            "---\nname: ml\n---\n\n"
            "Machine learning engineer working with docker containers kubernetes "
            "for model deployment. Uses python tensorflow developer tools.",
            encoding="utf-8"
        )

        # eng-platform body
        (eng_dir / "eng-platform.md").write_text(
            "---\nname: platform\n---\n\n"
            "Platform developer managing kubernetes docker containers.",
            encoding="utf-8"
        )

        # eng-sre body
        (eng_dir / "eng-sre.md").write_text(
            "---\nname: sre\n---\n\n"
            "SRE engineer monitoring reliability.",
            encoding="utf-8"
        )

        # eng-bad-fm: no closing frontmatter delimiter
        (eng_dir / "eng-bad-fm.md").write_text(
            "---\nname: bad\nno closing fm\nSome body content here.",
            encoding="utf-8"
        )

        # eng-no-file: not created on disk

        monkeypatch.setattr(mod, "load_agents", lambda: test_agents)

        def _mock_find(agent_id):
            mapping = {
                "eng-etl": eng_dir / "eng-etl.md",
                "eng-ml": eng_dir / "eng-ml.md",
                "eng-platform": eng_dir / "eng-platform.md",
                "eng-sre": eng_dir / "eng-sre.md",
                "eng-bad-fm": eng_dir / "eng-bad-fm.md",
            }
            return mapping.get(agent_id)

        monkeypatch.setattr(mod, "find_agent_file", _mock_find)
        monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

        mod.main()

        captured = capsys.readouterr()
        assert "Agents without depends_on: 6/6" in captured.out
        assert "High-confidence" in captured.out
        assert "Medium-confidence" in captured.out
        # Sample HIGH output should show our agent
        assert "=== Sample HIGH ===" in captured.out
