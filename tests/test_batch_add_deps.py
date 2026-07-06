"""Tests for scripts/batch-add-deps.py frontmatter manipulation logic."""
import importlib.util
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
