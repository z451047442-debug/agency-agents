"""Tests for scripts/i18n/localize-agents.py — frontmatter name/description patching."""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "localize_agents", str(SCRIPTS_DIR / "i18n" / "localize-agents.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

patch_frontmatter = mod.patch_frontmatter


class TestPatchFrontmatter:
    def test_replaces_wrapped_description_completely(self):
        """A description continued on later lines is replaced whole.

        Real frontmatter wraps long descriptions as YAML plain scalars:

            description: Coordinates multi-agent workflows for aerospace — ...,
              propulsion, space systems, UAM, ...

        Replacing only the first line leaves the wrapped tail behind, which YAML
        then folds into the new (translated) value.
        """
        fm_text = (
            "\n"
            "description: Coordinates multi-agent workflows for aerospace — aircraft structures,\n"
            "  avionics, propulsion, space systems, UAM, certification, and safety lifecycle\n"
            "emoji: ✈️\n"
            "name: Aerospace Multi-Agent Coordinator\n"
        )
        entry = {
            "name": "航空航天多智能体协调专家",
            "description": "航空航天领域多智能体协作协调专家，统筹飞行器结构与航电类 agent 的编排",
        }

        new_fm, changed = patch_frontmatter(fm_text, entry)
        lines = new_fm.split("\n")

        assert changed is True
        assert lines[0] == ""
        assert lines[1] == "description: 航空航天领域多智能体协作协调专家，统筹飞行器结构与航电类 agent 的编排"
        assert "avionics, propulsion" not in new_fm, "wrapped tail was left behind"
        assert lines[2] == "emoji: ✈️"
        assert "name: 航空航天多智能体协调专家" in lines

    def test_replaces_single_line_description(self):
        """Single-line descriptions are replaced; neighbouring lines untouched."""
        fm_text = (
            "\n"
            "color: teal\n"
            "description: Coordinates multi-agent workflows for administration\n"
            "emoji: 🏢\n"
            "name: Administration Multi-Agent Coordinator\n"
        )
        entry = {
            "name": "行政多智能体协调专家",
            "description": "企业行政多智能体协作协调专家，统筹办公运营与后勤保障类 agent 的编排",
        }

        new_fm, changed = patch_frontmatter(fm_text, entry)
        lines = new_fm.split("\n")

        assert changed is True
        assert lines[1] == "color: teal"
        assert lines[2] == "description: 企业行政多智能体协作协调专家，统筹办公运营与后勤保障类 agent 的编排"
        assert lines[3] == "emoji: 🏢"
        assert lines[4] == "name: 行政多智能体协调专家"


# ── check-i18n.py coverage reporting ─────────────────────────────────────────

spec_i18n = importlib.util.spec_from_file_location(
    "check_i18n", str(SCRIPTS_DIR / "i18n" / "check-i18n.py")
)
check_i18n = importlib.util.module_from_spec(spec_i18n)
spec_i18n.loader.exec_module(check_i18n)


class TestCheckCoverage:
    def test_all_localized_reports_full_coverage(self, monkeypatch, capsys):
        monkeypatch.setattr(check_i18n, "load_mapping", lambda lang="zh": {})
        monkeypatch.setattr(check_i18n, "discover_agents", lambda: [
            ("testing", Path("testing/x.md"), "测试代理", "描述"),
        ])
        errors, warnings = check_i18n.check_coverage(
            lang="zh", show_untranslated=False, out=sys.stdout
        )
        out = capsys.readouterr().out
        assert errors == 0
        assert warnings == 0
        assert "Coverage:              100.0%" in out

    def test_untranslated_and_orphaned_entries(self, monkeypatch, capsys):
        monkeypatch.setattr(check_i18n, "load_mapping",
                            lambda lang="zh": {"Ghost Agent": {"name": "幽灵"}})
        monkeypatch.setattr(check_i18n, "discover_agents", lambda: [
            ("testing", Path("testing/x.md"), "English Agent", "desc"),
        ])
        errors, warnings = check_i18n.check_coverage(
            lang="zh", show_untranslated=True, out=sys.stdout
        )
        out = capsys.readouterr().out
        assert errors == 1
        assert warnings == 1
        assert "Coverage:              0.0%" in out
        assert "Untranslated Agents (1 agents in 1 categories)" in out
        assert "Orphaned Mapping Entries (1 entries" in out

    def test_translated_agent_reports_full_coverage(self, monkeypatch, capsys):
        monkeypatch.setattr(check_i18n, "load_mapping",
                            lambda lang="zh": {"English Agent": {"name": "英文代理"}})
        monkeypatch.setattr(check_i18n, "discover_agents", lambda: [
            ("testing", Path("testing/x.md"), "English Agent", "desc"),
        ])
        errors, warnings = check_i18n.check_coverage(
            lang="zh", show_untranslated=False, out=sys.stdout
        )
        out = capsys.readouterr().out
        assert errors == 0
        assert warnings == 0
        assert "Have translations:     1" in out
        assert "Coverage:              100.0%" in out

    def test_template_output(self, monkeypatch, capsys):
        monkeypatch.setattr(check_i18n, "load_mapping", lambda lang="zh": {})
        monkeypatch.setattr(check_i18n, "discover_agents", lambda: [
            ("testing", Path("testing/x.md"), "English Agent", "desc"),
        ])
        check_i18n.check_coverage(
            lang="zh", show_untranslated=False, template=True, out=sys.stderr
        )
        captured = capsys.readouterr()
        assert '"English Agent"' in captured.out
        assert "Translation Template" in captured.err


class TestCheckI18nHelpers:
    def test_has_cjk(self):
        assert check_i18n._has_cjk("测试代理") is True
        assert check_i18n._has_cjk("English Agent") is False
        assert check_i18n._has_cjk("") is False

    def test_load_mapping_reads_file(self, tmp_path, monkeypatch):
        (tmp_path / "agent-names-zh.json").write_text(
            '{"English Agent": {"name": "英文代理"}}', encoding="utf-8"
        )
        monkeypatch.setattr(check_i18n, "I18N_DIR", tmp_path)
        assert check_i18n.load_mapping("zh") == {
            "English Agent": {"name": "英文代理"}
        }

    def test_load_mapping_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(check_i18n, "I18N_DIR", tmp_path)
        assert check_i18n.load_mapping("ja") == {}


class TestCheckEncoding:
    def test_valid_files_pass(self, tmp_path, monkeypatch, capsys):
        good = tmp_path / "good.md"
        good.write_text("---\nname: 测试\n---\n正文", encoding="utf-8")
        monkeypatch.setattr(check_i18n, "discover_agents", lambda: [
            ("testing", good, "测试", "desc"),
        ])
        assert check_i18n.check_encoding(out=sys.stdout) == 0
        out = capsys.readouterr().out
        assert "All 1 agent files pass UTF-8 validation" in out

    def test_invalid_utf8_reported(self, tmp_path, monkeypatch, capsys):
        bad = tmp_path / "bad.md"
        bad.write_bytes(b"---\nname: \xff\xfe\n---\n")
        monkeypatch.setattr(check_i18n, "discover_agents", lambda: [
            ("testing", bad, "坏", "desc"),
        ])
        assert check_i18n.check_encoding(out=sys.stdout) == 1
        out = capsys.readouterr().out
        assert "Invalid UTF-8" in out


class TestCheckI18nMain:
    def test_main_strict_fails_on_missing_mapping(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(check_i18n, "I18N_DIR", tmp_path)
        monkeypatch.setattr(check_i18n, "discover_agents", lambda: [])
        monkeypatch.setattr(sys, "argv", ["check-i18n.py", "--strict"])
        with pytest.raises(SystemExit) as exc:
            check_i18n.main()
        assert exc.value.code == 1
        assert "Mapping file not found" in capsys.readouterr().out

    def test_main_non_strict_warns_but_passes(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(check_i18n, "I18N_DIR", tmp_path)
        monkeypatch.setattr(check_i18n, "discover_agents", lambda: [])
        monkeypatch.setattr(sys, "argv", ["check-i18n.py", "--no-untranslated"])
        with pytest.raises(SystemExit) as exc:
            check_i18n.main()
        assert exc.value.code == 0
        assert "PASSED" in capsys.readouterr().out
