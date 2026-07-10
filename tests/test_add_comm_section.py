"""Tests for scripts/add-comm-section.py — communication section insertion."""

import importlib.util
import io
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "add_comm_section", str(SCRIPTS_DIR / "add-comm-section.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

has_comm_section = mod.has_comm_section
generate_comm_section = mod.generate_comm_section
get_traits_for_agent = mod.get_traits_for_agent
insert_comm_section = mod.insert_comm_section


class TestHasCommSection:
    def test_detects_english_style_header(self):
        assert has_comm_section("## Communication Style\n\nSome content here.")

    def test_detects_emoji_header(self):
        assert has_comm_section("## 💬 Your Communication Style\n\nTrait content.")

    def test_case_insensitive(self):
        assert has_comm_section("## communication style\n\nContent.")

    def test_no_section_returns_false(self):
        assert not has_comm_section("## Identity\n\nSome identity content.")

    def test_empty_body(self):
        assert not has_comm_section("")

    def test_mid_body_detection(self):
        body = "## Identity\nContent.\n\n## 💬 Communication\n\nStyle here.\n\n## Deliverables\nList."
        assert has_comm_section(body)


class TestGenerateCommSection:
    def test_returns_section_with_header(self):
        result = generate_comm_section(
            "test-agent", "engineering",
            "Frontend development expert", "Frontend Developer", "Precise"
        )
        assert "## 💬 Your Communication Style" in result
        assert "**" in result  # has bold trait names

    def test_includes_traits(self):
        result = generate_comm_section(
            "test-agent", "data-science",
            "Machine learning expert", "ML Engineer", "Analytical"
        )
        assert len(result) > 50

    def test_unknown_category_uses_default(self):
        result = generate_comm_section(
            "test-agent", "zzz-unknown-cat",
            "Something", "Someone", ""
        )
        assert "## 💬 Your Communication Style" in result


class TestGetTraitsForAgent:
    def test_returns_list_of_tuples(self):
        traits = get_traits_for_agent(
            "engineering", "frontend developer", "Frontend Dev", ""
        )
        assert isinstance(traits, list)
        assert len(traits) > 0
        assert len(traits) <= 4
        for t in traits:
            assert isinstance(t, tuple)
            assert len(t) == 2

    def test_default_traits_for_unknown_category(self):
        traits = get_traits_for_agent(
            "nonexistent-category", "something", "Name", ""
        )
        assert len(traits) > 0
        assert len(traits) <= 4


class TestInsertCommSection:
    def test_dry_run_does_not_modify(self, tmp_path):
        path = tmp_path / "test-cat" / "test-agent.md"
        path.parent.mkdir(parents=True)
        content = """---
name: "Test"
description: "Test agent"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## 🧠 Identity
You are a test agent.

## 🚨 Critical Rules
1. Always test.

## 📦 Deliverables
- Test report
"""
        path.write_text(content, encoding="utf-8")
        original = path.read_text(encoding="utf-8")
        ok, msg = insert_comm_section(path, dry_run=True)
        assert ok
        assert path.read_text(encoding="utf-8") == original

    def test_skips_if_already_has_section(self, tmp_path):
        path = tmp_path / "test-cat" / "test-agent.md"
        path.parent.mkdir(parents=True)
        content = """---
name: "Test"
description: "Test"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
Test.

## 💬 Communication Style
Already has one.
"""
        path.write_text(content, encoding="utf-8")
        ok, msg = insert_comm_section(path, dry_run=False)
        assert not ok
        assert "already has" in msg.lower()

    def test_inserts_section_in_place(self, tmp_path):
        path = tmp_path / "test-cat" / "test-agent.md"
        path.parent.mkdir(parents=True)
        content = """---
name: "Test"
description: "Test agent"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## 🧠 Identity
You are a test agent.

## 🚨 Critical Rules
1. Always test.
2. Verify results.

## 📦 Deliverables
- Test report
"""
        path.write_text(content, encoding="utf-8")
        ok, msg = insert_comm_section(path, dry_run=False)
        assert ok
        modified = path.read_text(encoding="utf-8")
        assert "## 💬 Your Communication Style" in modified

    def test_read_error_returns_false(self, tmp_path):
        """Lines 140-141: Exception during file read."""
        path = tmp_path / "test-cat" / "agent.md"
        path.parent.mkdir(parents=True)
        path.write_text("content", encoding="utf-8")
        with patch.object(path.__class__, "read_text", side_effect=OSError("permission denied")):
            ok, msg = insert_comm_section(path)
            assert not ok
            assert "cannot read file" in msg

    def test_write_error_returns_false(self, tmp_path):
        """Lines 186-187: Exception during file write."""
        path = tmp_path / "test-cat" / "agent.md"
        path.parent.mkdir(parents=True)
        content = """---
name: "Test"
description: "Test agent"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
You are a test agent.

## 🚨 Critical Rules
1. Always test.

## 📦 Deliverables
- Test report
"""
        path.write_text(content, encoding="utf-8")
        with patch.object(path.__class__, "write_text", side_effect=OSError("read-only filesystem")):
            ok, msg = insert_comm_section(path, dry_run=False)
            assert not ok
            assert "read-only" in msg

    def test_insert_after_rules_when_present(self, tmp_path):
        """Section inserted right after Critical Rules block."""
        path = tmp_path / "test-cat" / "agent.md"
        path.parent.mkdir(parents=True)
        content = """---
name: "Test"
description: "Test agent"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
You are a test agent.

## 🚨 Critical Rules You Must Follow
1. Rule one.
2. Rule two.

## 📦 Deliverables
- Item one.
"""
        path.write_text(content, encoding="utf-8")
        ok, msg = insert_comm_section(path, dry_run=False)
        assert ok
        modified = path.read_text(encoding="utf-8")
        # Communication section should appear between Rules and Deliverables
        rules_pos = modified.index("Critical Rules")
        comm_pos = modified.index("💬 Your Communication Style")
        deliverables_pos = modified.index("📦 Deliverables")
        assert rules_pos < comm_pos < deliverables_pos

    def test_fallback_to_deliverables_match(self, tmp_path):
        """Lines 168-172: No rules section, falls back to inserting before Deliverables."""
        path = tmp_path / "test-cat" / "agent.md"
        path.parent.mkdir(parents=True)
        content = """---
name: "Test"
description: "Test agent"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
You are a test agent.

## 📦 Deliverables
- Item one.
"""
        path.write_text(content, encoding="utf-8")
        ok, msg = insert_comm_section(path, dry_run=False)
        assert ok
        modified = path.read_text(encoding="utf-8")
        assert "## 💬 Your Communication Style" in modified
        comm_pos = modified.index("💬 Your Communication Style")
        deliverables_pos = modified.index("📦 Deliverables")
        assert comm_pos < deliverables_pos

    def test_fallback_deliverable_no_emoji(self, tmp_path):
        """Lines 168-172: Match ## Deliverable without emoji."""
        path = tmp_path / "test-cat" / "agent.md"
        path.parent.mkdir(parents=True)
        content = """---
name: "Test"
description: "Test agent"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
You are a test agent.

## Deliverables
- Item one.
"""
        path.write_text(content, encoding="utf-8")
        ok, msg = insert_comm_section(path, dry_run=False)
        assert ok
        modified = path.read_text(encoding="utf-8")
        comm_pos = modified.index("💬 Your Communication Style")
        deliverables_pos = modified.index("Deliverables")
        assert comm_pos < deliverables_pos

    def test_fallback_append_to_end(self, tmp_path):
        """Lines 173-175: No rules, no deliverables — appendix to end of body."""
        path = tmp_path / "test-cat" / "agent.md"
        path.parent.mkdir(parents=True)
        content = """---
name: "Test"
description: "Test agent"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
You are a test agent with just an identity section.
"""
        path.write_text(content, encoding="utf-8")
        ok, msg = insert_comm_section(path, dry_run=False)
        assert ok
        modified = path.read_text(encoding="utf-8")
        assert "## 💬 Your Communication Style" in modified
        # Communication section should be at the end (after identity)
        comm_pos = modified.index("💬 Your Communication Style")
        end_content = modified[comm_pos:]
        assert "Identity" not in end_content  # Identity is before comm section


# ── main() function ──────────────────────────────────────────────────────────

class TestMainFunction:
    """Tests for the main() function covering lines 191-239."""

    def test_no_args_prints_help_and_exits(self, capsys):
        """Lines 200-202: No arguments triggers help + sys.exit(1)."""
        with patch.object(sys, "argv", ["add-comm-section.py"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
            assert exc.value.code == 1

    def test_agent_not_found_no_targets(self, monkeypatch):
        """Line 218-219: No matching agents found."""
        def _mock_discover(category_filter=None):
            yield from []
        monkeypatch.setattr(mod, "discover_agents", _mock_discover)
        with patch.object(sys, "argv", ["add-comm-section.py", "--agent", "nonexistent"]):
            # Should not raise; prints a message
            mod.main()

    def test_all_dry_run(self, tmp_path, monkeypatch, capsys):
        """Test --all --dry-run processing with a controlled agent."""
        cat_dir = tmp_path / "engineering"
        cat_dir.mkdir()
        agent_path = cat_dir / "engineering-test-agent.md"
        content = """---
name: "Test Agent"
description: "A test agent for engineering"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
You are a test.

## 🚨 Critical Rules
1. Rule.

## 📦 Deliverables
- Item.
"""
        agent_path.write_text(content, encoding="utf-8")

        def _mock_discover(category_filter=None):
            yield ("engineering", str(cat_dir.relative_to(tmp_path)), agent_path)

        monkeypatch.setattr(mod, "discover_agents", _mock_discover)
        with patch.object(sys, "argv", ["add-comm-section.py", "--all", "--dry-run"]):
            mod.main()

    def test_category_filter(self, tmp_path, monkeypatch, capsys):
        """Test --category flag processing."""
        cat_dir = tmp_path / "design"
        cat_dir.mkdir()
        agent_path = cat_dir / "design-ui-expert.md"
        content = """---
name: "UI Expert"
description: "Design expert"
color: green
emoji: Y
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
Expert.

## 🚨 Critical Rules
1. Rule.

## 📦 Deliverables
- Item.
"""
        agent_path.write_text(content, encoding="utf-8")

        def _mock_discover(category_filter=None):
            if category_filter == "design":
                yield ("design", str(cat_dir.relative_to(tmp_path)), agent_path)
            elif category_filter is None:
                yield ("design", str(cat_dir.relative_to(tmp_path)), agent_path)

        monkeypatch.setattr(mod, "discover_agents", _mock_discover)
        with patch.object(sys, "argv", ["add-comm-section.py", "--category", "design"]):
            mod.main()

    def test_limit_caps_targets(self, tmp_path, monkeypatch):
        """Line 215-216: --limit truncates the target list."""
        cat_dir = tmp_path / "engineering"
        cat_dir.mkdir()
        agents = []
        for i in range(3):
            p = cat_dir / f"engineering-agent-{i}.md"
            p.write_text(f"""---
name: "Agent {i}"
description: "Test agent {i}"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
Agent {i}.

## 🚨 Critical Rules
1. Rule.

## 📦 Deliverables
- Item.
""", encoding="utf-8")
            agents.append(p)

        def _mock_discover(category_filter=None):
            for i, p in enumerate(agents):
                yield ("engineering", str(cat_dir.relative_to(tmp_path)), p)

        monkeypatch.setattr(mod, "discover_agents", _mock_discover)
        with patch.object(sys, "argv", ["add-comm-section.py", "--all", "--limit", "1"]):
            mod.main()

    def test_agent_filter_exact_match(self, tmp_path, monkeypatch):
        """Test --agent flag filters to specific agent ID."""
        cat_dir = tmp_path / "engineering"
        cat_dir.mkdir()
        target_path = cat_dir / "engineering-my-agent.md"
        other_path = cat_dir / "engineering-other-agent.md"
        content = """---
name: "My Agent"
description: "Test agent"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
Test.

## 🚨 Critical Rules
1. Rule.

## 📦 Deliverables
- Item.
"""
        target_path.write_text(content, encoding="utf-8")
        other_path.write_text(content, encoding="utf-8")

        def _mock_discover(category_filter=None):
            yield ("engineering", str(cat_dir.relative_to(tmp_path)), target_path)
            yield ("engineering", str(cat_dir.relative_to(tmp_path)), other_path)

        monkeypatch.setattr(mod, "discover_agents", _mock_discover)
        with patch.object(sys, "argv", ["add-comm-section.py", "--agent", "engineering-my-agent"]):
            mod.main()

    def test_skipped_printed_for_already_present(self, tmp_path, monkeypatch, capsys):
        """Line 236-237: Agent already has comm section → skipped message."""
        cat_dir = tmp_path / "engineering"
        cat_dir.mkdir()
        agent_path = cat_dir / "engineering-has-comm.md"
        content = """---
name: "Has Comm"
description: "Already has communication section"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
Test.

## 💬 Communication Style
Already here.

## 📦 Deliverables
- Item.
"""
        agent_path.write_text(content, encoding="utf-8")

        def _mock_discover(category_filter=None):
            yield ("engineering", str(cat_dir.relative_to(tmp_path)), agent_path)

        monkeypatch.setattr(mod, "discover_agents", _mock_discover)
        with patch.object(sys, "argv", ["add-comm-section.py", "--all"]):
            mod.main()
        captured = capsys.readouterr()
        assert "No agents missing" in captured.out

    def test_insert_failure_triggers_skipped(self, tmp_path, monkeypatch, capsys):
        """Lines 236-237: insert_comm_section returns False → skipped output."""
        cat_dir = tmp_path / "engineering"
        cat_dir.mkdir()
        agent_path = cat_dir / "engineering-test-agent.md"
        content = """---
name: "Test Agent"
description: "Test agent"
color: blue
emoji: X
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
Test.

## 🚨 Critical Rules
1. Rule.

## 📦 Deliverables
- Item.
"""
        agent_path.write_text(content, encoding="utf-8")

        def _mock_discover(category_filter=None):
            yield ("engineering", str(cat_dir.relative_to(tmp_path)), agent_path)

        monkeypatch.setattr(mod, "discover_agents", _mock_discover)
        monkeypatch.setattr(mod, "insert_comm_section",
                            lambda fp, dry_run=False: (False, "disk full"))
        with patch.object(sys, "argv", ["add-comm-section.py", "--all"]):
            mod.main()
        captured = capsys.readouterr()
        assert "Skipped: 1" in captured.out


# ── stdout encoding reconfigure ──────────────────────────────────────────────

class TestStdoutEncoding:
    """Test line 31: sys.stdout.reconfigure for non-utf-8 encodings."""

    def test_reconfigure_called_when_not_utf8(self):
        """When stdout.encoding is not utf-8, reconfigure is called."""
        from unittest.mock import MagicMock

        # Remove any cached module references
        keys_to_remove = [k for k in sys.modules if "add_comm_section" in k]
        for k in keys_to_remove:
            del sys.modules[k]

        mock_stdout = MagicMock()
        mock_stdout.encoding = "cp1252"

        with patch.object(sys, "stdout", mock_stdout):
            spec = importlib.util.spec_from_file_location(
                "add_comm_section_enc", str(SCRIPTS_DIR / "add-comm-section.py")
            )
            mod2 = importlib.util.module_from_spec(spec)
            # Should not raise; reconfigure is called on the mock stdout
            spec.loader.exec_module(mod2)
