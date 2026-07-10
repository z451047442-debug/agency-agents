"""Tests for scripts/batch-add-deps.py frontmatter manipulation logic."""
import importlib.util
import json
import tempfile
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
spec = importlib.util.spec_from_file_location(
    "batch_add_deps", str(SCRIPTS_DIR / "batch-add-deps.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

find_file = mod.find_file
add_deps = mod.add_deps


class TestFindFile:
    def test_real_agent_found(self):
        path = find_file("engineering-frontend-developer")
        assert path is not None
        assert path.exists()

    def test_no_duplicate_suffix(self):
        path = find_file("engineering-frontend-developer")
        assert path.suffix == ".md"


class TestAddDeps:
    def make_temp_agent(self, tmp_path, frontmatter_lines):
        """Create a temp agent file with given frontmatter."""
        content = "---\n" + "\n".join(frontmatter_lines) + "\n---\n\n# Test\n"
        f = tmp_path / "tests" / "test-agent.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
        return f

    def test_adds_to_existing_list(self, tmp_path):
        lines = [
            'name: "Test Agent"',
            'description: "A test agent"',
            'emoji: "🔧"',
            'color: blue',
            "depends_on:",
            "  - existing-agent-1",
        ]
        f = self.make_temp_agent(tmp_path, lines)
        assert add_deps(f, ["new-agent-2"])
        content = f.read_text(encoding="utf-8")
        assert "existing-agent-1" in content
        assert "new-agent-2" in content

    def test_adds_missing_depends_on_section(self, tmp_path):
        lines = [
            'name: "Test Agent"',
            'description: "A test agent"',
            'emoji: "🔧"',
            'color: blue',
            "nexus_roles:",
            "  - phase-3-build",
        ]
        f = self.make_temp_agent(tmp_path, lines)
        assert add_deps(f, ["new-dependency"])
        content = f.read_text(encoding="utf-8")
        assert "depends_on:" in content
        assert "new-dependency" in content

    def test_no_duplicate_deps(self, tmp_path):
        lines = [
            'name: "Test Agent"',
            'description: "A test agent"',
            'emoji: "🔧"',
            'color: blue',
            "depends_on:",
            "  - existing-agent",
        ]
        f = self.make_temp_agent(tmp_path, lines)
        # Should not add if already exists
        assert not add_deps(f, ["existing-agent"])

    def test_multiple_deps_added(self, tmp_path):
        lines = [
            'name: "Test Agent"',
            'description: "A test agent"',
            'emoji: "🔧"',
            'color: blue',
            "depends_on:",
            "  - dep-a",
        ]
        f = self.make_temp_agent(tmp_path, lines)
        assert add_deps(f, ["dep-b", "dep-c"])
        content = f.read_text(encoding="utf-8")
        assert "dep-a" in content
        assert "dep-b" in content
        assert "dep-c" in content

    def test_non_list_line_breaks_dep_parsing(self, tmp_path):
        """A non-indented non-list line after depends_on stops parsing (line 51)."""
        lines = [
            'name: "Test Agent"',
            'description: "A test agent"',
            'emoji: "🔧"',
            'color: blue',
            "depends_on:",
            "  - existing-dep",
            "version: 1.0.0",  # non-list, non-indented — breaks parsing
            "extra_field: value",
        ]
        f = self.make_temp_agent(tmp_path, lines)
        assert add_deps(f, ["new-dep"])
        content = f.read_text(encoding="utf-8")
        assert "existing-dep" in content
        assert "new-dep" in content
        # version should still be present
        assert "version: 1.0.0" in content

    def test_no_nexus_roles_insert_after_last_field(self, tmp_path):
        """Without nexus_roles, depends_on is inserted after the last colon field (lines 71-73)."""
        lines = [
            'name: "Test Agent"',
            'description: "No nexus roles here"',
            'emoji: "🔧"',
            'color: blue',
        ]
        f = self.make_temp_agent(tmp_path, lines)
        assert add_deps(f, ["new-dep"])
        content = f.read_text(encoding="utf-8")
        assert "depends_on:" in content
        assert "new-dep" in content
        # depends_on should be inserted after color (the last field with colon)
        idx_color = content.index("color:")
        idx_deps = content.index("depends_on:")
        assert idx_deps > idx_color

    def test_only_name_field_no_nexus_roles(self, tmp_path):
        """Minimal frontmatter — insert_at falls through to fm_end (line 74)."""
        lines = [
            'name: "Test Agent"',
        ]
        f = self.make_temp_agent(tmp_path, lines)
        assert add_deps(f, ["minimal-dep"])
        content = f.read_text(encoding="utf-8")
        assert "depends_on:" in content
        assert "minimal-dep" in content


# ── find_file fallback to special directories ──────────────────────────────

class TestFindFileFallback:
    def test_finds_in_special_directory(self, tmp_path, monkeypatch):
        """find_file searches libraries/specialized/_solution/strategy/network-engineering (lines 22-27)."""
        for d in ("libraries", "specialized", "_solution", "strategy", "network-engineering"):
            (tmp_path / d).mkdir(parents=True)

        # Put agent in _solution dir
        agent_path = tmp_path / "_solution" / "solution-architect.md"
        agent_path.write_text("---\nname: test\n---\n", encoding="utf-8")

        monkeypatch.setattr(mod, "ROOT", tmp_path)

        result = find_file("solution-architect")
        assert result is not None
        assert result.exists()

    def test_returns_none_when_not_found(self, tmp_path, monkeypatch):
        """find_file returns None when agent is not found anywhere."""
        monkeypatch.setattr(mod, "ROOT", tmp_path)
        result = find_file("nonexistent-agent-xyz")
        assert result is None

    def test_finds_in_libraries_dir(self, tmp_path, monkeypatch):
        (tmp_path / "libraries").mkdir(parents=True)
        agent_path = tmp_path / "libraries" / "libraries-archivist.md"
        agent_path.write_text("---\nname: test\n---\n", encoding="utf-8")

        monkeypatch.setattr(mod, "ROOT", tmp_path)
        result = find_file("libraries-archivist")
        assert result is not None

    def test_finds_in_subdirectory_first(self, tmp_path, monkeypatch):
        """Regular category dir is searched before special dirs."""
        (tmp_path / "engineering").mkdir(parents=True)
        (tmp_path / "libraries").mkdir(parents=True)

        agent_eng = tmp_path / "engineering" / "engineering-tester.md"
        agent_eng.write_text("---\nname: test\n---\n", encoding="utf-8")
        agent_lib = tmp_path / "libraries" / "engineering-tester.md"
        agent_lib.write_text("---\nname: test\n---\n", encoding="utf-8")

        monkeypatch.setattr(mod, "ROOT", tmp_path)
        result = find_file("engineering-tester")
        assert result is not None
        # Should find in engineering first
        assert "engineering" in str(result)


# ── main ───────────────────────────────────────────────────────────────────

class TestMain:
    def test_runs_and_prints_summary(self, tmp_path, monkeypatch, capsys):
        """main() loads suggested_deps.json and AGENTS.json, processes agents."""
        # Setup ROOT
        monkeypatch.setattr(mod, "ROOT", tmp_path)

        # Create suggested_deps.json
        suggested = {
            "high_confidence": {
                "engineering-frontend-dev": [
                    {"agent_id": "engineering-ux-designer", "confidence": 0.95},
                    {"agent_id": "data-science-engineering-knowledge-management", "confidence": 0.80},
                ],
            }
        }
        (tmp_path / "suggested_deps.json").write_text(
            json.dumps(suggested), encoding="utf-8"
        )

        # Create an agent file so find_file succeeds
        (tmp_path / "engineering").mkdir(parents=True)
        agent_md = (
            "---\nname: Test\ndescription: Test\nemoji: X\ncolor: blue\n"
            "---\n\n# Body\n"
        )
        (tmp_path / "engineering" / "engineering-frontend-dev.md").write_text(
            agent_md, encoding="utf-8"
        )

        # Create AGENTS.json
        agents_data = {
            "agents": [
                {"id": "engineering-frontend-dev", "depends_on": []},
            ]
        }
        (tmp_path / "AGENTS.json").write_text(
            json.dumps(agents_data), encoding="utf-8"
        )

        mod.main()
        captured = capsys.readouterr()
        assert "Loaded" in captured.out
        assert "Applied" in captured.out

    def test_all_generic_deps_skipped(self, tmp_path, monkeypatch, capsys):
        """When all deps are generic, the agent is skipped."""
        monkeypatch.setattr(mod, "ROOT", tmp_path)

        suggested = {
            "high_confidence": {
                "engineering-frontend-dev": [
                    {"agent_id": "data-science-engineering-knowledge-management", "confidence": 0.95},
                ],
            }
        }
        (tmp_path / "suggested_deps.json").write_text(
            json.dumps(suggested), encoding="utf-8"
        )

        # Need AGENTS.json for the final count (at least 1 agent to avoid div-by-zero)
        (tmp_path / "AGENTS.json").write_text(
            json.dumps({"agents": [{"id": "dummy"}]}), encoding="utf-8"
        )

        mod.main()
        captured = capsys.readouterr()
        assert "Skipped" in captured.out

    def test_add_deps_exception_handled(self, tmp_path, monkeypatch, capsys):
        """When add_deps raises, the exception is caught and agent is skipped (line 98-99)."""
        monkeypatch.setattr(mod, "ROOT", tmp_path)

        suggested = {
            "high_confidence": {
                "engineering-frontend-dev": [
                    {"agent_id": "engineering-ux-designer", "confidence": 0.95},
                ],
            }
        }
        (tmp_path / "suggested_deps.json").write_text(
            json.dumps(suggested), encoding="utf-8"
        )

        # Create agent file so find_file succeeds
        (tmp_path / "engineering").mkdir(parents=True)
        agent_md = (
            "---\nname: Test\ndescription: Test\nemoji: X\ncolor: blue\n"
            "---\n\n# Body\n"
        )
        (tmp_path / "engineering" / "engineering-frontend-dev.md").write_text(
            agent_md, encoding="utf-8"
        )

        # Create AGENTS.json
        (tmp_path / "AGENTS.json").write_text(
            json.dumps({"agents": [{"id": "dummy"}]}), encoding="utf-8"
        )

        # Monkeypatch add_deps to raise an exception
        monkeypatch.setattr(mod, "add_deps", lambda f, deps: (_ for _ in ()).throw(Exception("boom")))

        mod.main()
        captured = capsys.readouterr()
        # Should show Skipped: 1 since the exception was caught
        assert "Skipped: 1" in captured.out
