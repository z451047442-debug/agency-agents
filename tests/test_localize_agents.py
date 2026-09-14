"""Tests for scripts/i18n/localize-agents.py — frontmatter name/description patching."""

import importlib.util
import sys
from pathlib import Path

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
