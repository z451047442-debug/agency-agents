"""Tests for scripts/score-agents.py"""
import importlib.util
import io
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
spec = importlib.util.spec_from_file_location(
    "score_agents", str(SCRIPTS_DIR / "score-agents.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

score_agent = mod.score_agent
get_frontmatter_text = mod.get_frontmatter_text
get_body = mod.get_body
get_field = mod.get_field
git_last_modified = mod.git_last_modified
print_terminal_report = mod.print_terminal_report
print_json_report = mod.print_json_report
main = mod.main
REPO = mod.REPO
CORE_SECTIONS = mod.CORE_SECTIONS

SAMPLE = """---
name: "Test Agent"
description: "Test agent for scoring"
emoji: "\\U0001f527"
color: blue
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
Test agent identity with background and expertise description.

## Mission
Test agent core mission statement here.

## Rules
1. Follow the rules strictly at all times.

## Deliverables
- Test deliverable format

## Workflow
1. Step one of the workflow.
"""


class TestScoreAgent:
    def test_returns_dict_with_score(self, tmp_path):
        f = tmp_path / "engineering" / "test.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(SAMPLE, encoding="utf-8")
        result = score_agent(f)
        assert isinstance(result, dict)
        assert "scores" in result
        assert 0 <= sum(result["scores"].values()) <= 10

    def test_has_required_detail_keys(self, tmp_path):
        f = tmp_path / "engineering" / "test2.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(SAMPLE, encoding="utf-8")
        result = score_agent(f)
        for key in ("content_depth", "structure", "frontmatter", "file_health"):
            assert key in result["scores"], f"Missing: {key}"


class TestHelpers:
    def test_frontmatter_ok(self):
        fm = get_frontmatter_text("---\nname: X\n---\nbody")
        assert "name: X" in fm

    def test_frontmatter_none(self):
        assert get_frontmatter_text("plain") == ""

    def test_body_ok(self):
        b = get_body("---\na: b\n---\n\nhello")
        assert "hello" in b

    def test_body_none(self):
        assert get_body("plain") == "plain"

    def test_get_field(self):
        assert get_field("name", "\nname: Z\ncolor: red\n") == "Z"

    def test_get_field_missing(self):
        assert get_field("x", "\nname: A\n") == ""


# ── git_last_modified tests ──────────────────────────────────────────────────

class TestGitLastModified:
    def test_git_returns_date(self, tmp_path, monkeypatch):
        """Happy path: subprocess returns a valid date string."""
        def fake_run(*args, **kwargs):
            result = type("Result", (), {})()
            result.stdout = "2026-01-15\n"
            result.returncode = 0
            return result

        monkeypatch.setattr(mod.subprocess, "run", fake_run)
        d = git_last_modified(tmp_path / "test.md")
        assert d == date(2026, 1, 15)

    def test_git_returns_empty(self, tmp_path, monkeypatch):
        """subprocess returns empty → returns None."""
        def fake_run(*args, **kwargs):
            result = type("Result", (), {})()
            result.stdout = "\n"
            return result

        monkeypatch.setattr(mod.subprocess, "run", fake_run)
        d = git_last_modified(tmp_path / "test.md")
        assert d is None

    def test_git_exception_returns_none(self, tmp_path, monkeypatch):
        """Lines 68-69: subprocess.run raises exception → returns None."""
        def fake_run(*args, **kwargs):
            raise OSError("git not found")

        monkeypatch.setattr(mod.subprocess, "run", fake_run)
        d = git_last_modified(tmp_path / "test.md")
        assert d is None


# ── score_agent edge cases ───────────────────────────────────────────────────

class TestScoreAgentEdgeCases:
    """Tests for uncovered branches in score_agent()."""

    def test_file_not_found(self, tmp_path):
        """Lines 94-95: non-existent file returns issues."""
        result = score_agent(tmp_path / "nonexistent.md")
        assert "file not found" in result["issues"]
        assert result["grade"] == "D"
        assert result["total"] == 0

    def test_cannot_read_file(self, tmp_path, monkeypatch):
        """Lines 99-101: file exists but cannot be read."""
        f = tmp_path / "bad.md"
        f.write_text("dummy", encoding="utf-8")
        # Mock read_text to raise an encoding error
        monkeypatch.setattr(Path, "read_text",
                           lambda self, encoding="utf-8": (_ for _ in ()).throw(
                               UnicodeDecodeError("utf-8", b"", 0, 1, "boom")))
        result = score_agent(f)
        assert "cannot read file" in " ".join(result["issues"])

    def test_empty_content_wc_score_0(self, tmp_path):
        """Line 116: word_count < 100 → wc_score = 0, 'too short' issue."""
        content = """---
name: "Short"
description: "A short agent with minimal content"
emoji: "X"
color: red
---

## Identity
tiny
"""
        f = tmp_path / "short.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["scores"]["content_depth"] == 0
        assert any("too short" in i for i in result["issues"])

    def test_medium_content_wc_score_1(self, tmp_path):
        """Line 115: 100 <= word_count < 400 → wc_score = 1."""
        words = "word " * 150  # 150 words, between 100-399
        content = f"""---
name: "Medium"
description: "A medium-length agent with enough words for content depth 1"
emoji: "X"
color: red
---

## Identity
{words}
"""
        f = tmp_path / "medium.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["scores"]["content_depth"] == 1

    def test_long_content_wc_score_2(self, tmp_path):
        """Line 111: 400 <= word_count < 800 → wc_score = 2."""
        words = "word " * 500  # 500 words, between 400-799
        content = f"""---
name: "Long"
description: "A long agent with 500 words for content depth 2 scoring test"
emoji: "X"
color: red
---

## Identity
{words}
"""
        f = tmp_path / "long.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["scores"]["content_depth"] == 2

    def test_very_long_content_wc_score_3(self, tmp_path):
        """Line 109: word_count >= 800 → wc_score = 3."""
        words = "word " * 850  # 850 words
        content = f"""---
name: "VeryLong"
description: "A very long agent with 850 words for content depth 3 scoring test case"
emoji: "X"
color: red
---

## Identity
{words}
"""
        f = tmp_path / "verylong.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["scores"]["content_depth"] == 3

    def test_seven_sections_sec_score_3(self, tmp_path):
        """Line 130: sections_found >= 7 → sec_score = 3."""
        content = """---
name: "SevenSections"
description: "Agent with all seven sections matching to get the max structure score of three"
emoji: "X"
color: red
---

## Your Identity
Identity content here.

## Your Core Mission
Mission content here.

## Critical Rules You Must Follow
Rules content here.

## Deliverables
Deliverables content here.

## Workflow
Workflow content here.

## Success Metrics
Metrics content here.

## Communication Style
Communication content here.
"""
        f = tmp_path / "seven.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["scores"]["structure"] == 3

    def test_long_description_fm_bonus(self, tmp_path):
        """Line 149: description >= 80 chars → fm_score += 0.5."""
        content = f"""---
name: "LongDesc"
description: "{'A' * 80}"
emoji: "X"
color: red
---

## Identity
Identity content here for agent with long description for frontmatter scoring.

## Core Mission
Mission content here for testing purposes and word count.

## Critical Rules
Rules content here for the agent to follow.

## Deliverables
Deliverables content for agent.

## Workflow
Workflow content here for agent.
"""
        f = tmp_path / "longdesc.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        # With emoji + color + long desc, should get high frontmatter score
        assert result["scores"]["frontmatter"] >= 1

    def test_file_size_2_to_8_kb_ideal(self, tmp_path):
        """Line 186: file_size_kb in 2-8 sweet spot → health_score += 1.0."""
        # Generate enough content to fill ~3KB
        padding = "x" * 3000  # ~3KB
        content = f"""---
name: "BigFile"
description: "An agent with enough content to be in the 2-8 KB size sweet spot"
emoji: "X"
color: red
---

## Identity
Identity content {padding}

## Core Mission
Mission content here for testing purposes and word count requirements.

## Critical Rules
Rules content here for the agent to follow strictly.

## Deliverables
Deliverables content for agent.

## Workflow
Workflow content here for agent.
"""
        f = tmp_path / "big.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert 2 <= result["file_size_kb"] <= 8

    def test_file_size_1_to_2_kb_partial(self, tmp_path):
        """Line 188: file_size_kb in 1-12 but not 2-8 → health_score += 0.5."""
        # Generate ~1.5KB of content
        padding = "x" * 1400
        content = f"""---
name: "MediumFile"
description: "An agent just big enough for the partial file size credit"
emoji: "X"
color: red
---

## Identity
Identity content {padding}

## Core Mission
Mission content here.

## Critical Rules
Rules content here.

## Deliverables
Deliverables content.

## Workflow
Workflow content.
"""
        f = tmp_path / "medfile.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert 1 <= result["file_size_kb"] <= 12

    def test_https_link_not_broken(self, tmp_path):
        """Line 201: https:// links are also skipped in link checking."""
        content = """---
name: "HttpsLink"
description: "Agent with an external https link that should be ignored by link checker"
emoji: "X"
color: red
---

## Identity
Check out [SecureSite](https://example.com/some-file.md).

## Core Mission
Mission content here for testing purposes and word count requirements.

## Critical Rules
Rules content here for the agent to follow strictly always.

## Deliverables
Deliverables content for agent workflow testing.

## Workflow
Workflow content here for agent testing purposes.
"""
        f = tmp_path / "httpslink.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["broken_links"] == 0

    def test_grade_a(self, tmp_path):
        """Line 236: total >= 8 → grade A."""
        words = "word " * 900  # 900 words → wc_score = 3
        # Long description (80+ chars) → description bonus
        content = f"""---
name: "AGrade"
description: "{'A' * 80}"
emoji: "X"
color: red
vibe: professional
nexus_roles: ["Discovery"]
---

## Your Identity
Identity content. {words}

## Your Core Mission
Mission content here for testing purposes and word count requirements.

## Critical Rules You Must Follow
Rules content here for the agent to follow strictly always.

## Deliverables
Deliverables content for agent workflow testing.

## Workflow
Workflow content here for agent testing purposes.

## Success Metrics
Metrics content here for seven sections.

## Communication Style
Communication content here for all seven sections.
"""
        f = tmp_path / "agrade.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["grade"] == "A"

    def test_few_sections_sec_score_0(self, tmp_path):
        """Line 136: sections_found < 3 → sec_score = 0."""
        content = """---
name: "Minimal"
description: "Minimal agent with almost no sections"
emoji: "X"
color: red
---

## Identity
Just identity, nothing else here at all folks.
"""
        f = tmp_path / "minimal.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["scores"]["structure"] == 0

    def test_two_sections_sec_score_0(self, tmp_path):
        """Line 136: sections_found = 2 → sec_score = 0."""
        content = """---
name: "TwoSections"
description: "Agent with only two matching sections"
emoji: "X"
color: red
---

## Identity
Just identity.

## Mission
Just mission.
"""
        f = tmp_path / "twosections.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["scores"]["structure"] == 0

    def test_three_sections_sec_score_1(self, tmp_path):
        """Line 134: sections_found = 3 → sec_score = 1."""
        content = """---
name: "ThreeSections"
description: "Agent with three matching sections"
emoji: "X"
color: red
---

## Identity
Identity content here.

## Core Mission
Mission content here.

## Critical Rules You Must Follow
Rules content here.
"""
        f = tmp_path / "three.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["scores"]["structure"] == 1

    def test_five_sections_sec_score_2(self, tmp_path):
        """Line 133: sections_found = 5 → sec_score = 2."""
        content = """---
name: "FiveSections"
description: "Agent with five matching sections"
emoji: "X"
color: red
---

## Identity
Identity content here.

## Core Mission
Mission content here.

## Critical Rules
Rules content here.

## Deliverables
Deliverables content here.

## Workflow
Workflow content here.
"""
        f = tmp_path / "five.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["scores"]["structure"] in (2, 3)

    def test_missing_description(self, tmp_path):
        """Line 154: missing description → fm_checks notes it."""
        content = """---
name: "NoDesc"
emoji: "X"
color: red
---

## Identity
Identity content here and some more words to reach minimum.
## Core Mission
Mission content here for testing purposes.
## Critical Rules
Rules content here.
## Deliverables
Deliverables content here.
"""
        f = tmp_path / "nodesc.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert "missing description" in str(result.get("frontmatter_details", []))

    def test_missing_emoji(self, tmp_path):
        """Line 159: missing emoji → fm_checks notes it."""
        content = """---
name: "NoEmoji"
description: "Agent without emoji, with enough description text for scoring"
color: red
---

## Identity
Identity content here and some more words for content depth.
## Core Mission
Mission content here for testing purposes.
## Critical Rules
Rules content here.
## Deliverables
Deliverables content here.
"""
        f = tmp_path / "noemoji.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert "missing emoji" in str(result.get("frontmatter_details", []))

    def test_missing_color(self, tmp_path):
        """Line 164: missing color → fm_checks notes it."""
        content = """---
name: "NoColor"
description: "Agent without color, with enough description text for scoring"
emoji: "X"
---

## Identity
Identity content here and some more words for content depth here.
## Core Mission
Mission content here for testing purposes.
## Critical Rules
Rules content here.
## Deliverables
Deliverables content here.
"""
        f = tmp_path / "nocolor.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert "missing color" in str(result.get("frontmatter_details", []))

    def test_has_vibe_and_nexus(self, tmp_path):
        """vibe and nexus_roles contribute to frontmatter score."""
        content = """---
name: "Rich"
description: "Agent with rich frontmatter, all fields present for scoring"
emoji: "X"
color: red
vibe: friendly
nexus_roles: ["Discovery", "Strategy"]
---

## Identity
Identity content here with additional words for content depth scoring purposes.
## Core Mission
Mission content here for testing purposes and getting enough word count.
## Critical Rules
Rules content here for the agent to follow strictly.
## Deliverables
Deliverables content here for the agent.
## Workflow
Workflow content here.
"""
        f = tmp_path / "rich.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        fm_details = str(result.get("frontmatter_details", []))
        assert "has vibe" in fm_details
        assert "has nexus_roles" in fm_details

    def test_short_description_partial_score(self, tmp_path):
        """Description 30-79 chars → fm_score += 0.25."""
        content = """---
name: "ShortDesc"
description: "Short desc"  # ~11 chars, so no bonus
emoji: "X"
color: red
---

## Identity
Identity content here for the agent testing short descriptions in frontmatter.
## Core Mission
Mission content here for testing purposes and getting enough word count.
## Critical Rules
Rules content here for the agent to follow strictly.
## Deliverables
Deliverables content here for agent workflow.
## Workflow
Workflow content here for agent workflow and more content.
"""
        f = tmp_path / "shortdesc.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        # Should still have emoji (0.5) + color (0.5) = base 1, scaled to 2
        assert result["scores"]["frontmatter"] >= 1

    def test_http_link_not_broken(self, tmp_path):
        """Line 201: http:// links are skipped (not checked)."""
        content = """---
name: "LinkAgent"
description: "Agent with an external http link that should be ignored by link checker"
emoji: "X"
color: red
---

## Identity
Check out [Google](http://example.com/page).

## Core Mission
Mission content here for testing purposes and word count requirements.

## Critical Rules
Rules content here for the agent to follow strictly always.

## Deliverables
Deliverables content for agent workflow testing.

## Workflow
Workflow content here for agent testing purposes.
"""
        f = tmp_path / "linkagent.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["broken_links"] == 0

    def test_absolute_link_resolution(self, tmp_path, monkeypatch):
        """Line 203-204: absolute /path/to/file.md links resolved from REPO."""
        monkeypatch.setattr(mod, "REPO", tmp_path)
        # Create the target file so link resolves
        target = tmp_path / "some-target.md"
        target.write_text("# Target\n", encoding="utf-8")

        content = """---
name: "AbsLink"
description: "Agent with an absolute path link that resolves from REPO root"
emoji: "X"
color: red
---

## Identity
See [absolute link](/some-target.md) for more info.

## Core Mission
Mission content here for testing purposes and word count requirements.

## Critical Rules
Rules content here for the agent to follow strictly always.

## Deliverables
Deliverables content for agent workflow testing.

## Workflow
Workflow content here for agent testing purposes.
"""
        f = tmp_path / "abslink.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["broken_links"] == 0

    def test_broken_relative_link(self, tmp_path, monkeypatch):
        """Line 207, 212: broken relative link → issue added."""
        monkeypatch.setattr(mod, "REPO", tmp_path)
        cat = tmp_path / "cat"
        cat.mkdir()
        content = """---
name: "BrokenLink"
description: "Agent with a broken relative link that should be detected"
emoji: "X"
color: red
---

## Identity
See [missing](missing-file.md) and also [another](nope.md).

## Core Mission
Mission content here for testing purposes and word count requirements.

## Critical Rules
Rules content here for the agent to follow strictly always.

## Deliverables
Deliverables content for agent workflow testing.

## Workflow
Workflow content here for agent testing purposes.
"""
        f = cat / "broken.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["broken_links"] == 2
        assert any("broken internal link" in i for i in result["issues"])

    def test_freshness_sets_last_modified(self, tmp_path, monkeypatch):
        """Lines 216-225: when check_freshness=True and git returns date."""
        monkeypatch.setattr(mod, "REPO", tmp_path)
        cat = tmp_path / "fresh"
        cat.mkdir()
        content = """---
name: "FreshAgent"
description: "Agent to test freshness scoring with git last modified date"
emoji: "X"
color: red
---

## Identity
Identity content here for the agent testing freshness scoring with git dates.

## Core Mission
Mission content here for testing purposes and word count requirements.

## Critical Rules
Rules content here for the agent to follow strictly always.

## Deliverables
Deliverables content for agent workflow testing.

## Workflow
Workflow content here for agent testing purposes.
"""
        f = cat / "fresh.md"
        f.write_text(content, encoding="utf-8")
        monkeypatch.setattr(mod, "git_last_modified",
                           lambda fp: date.today())
        result = score_agent(f, check_freshness=True)
        assert "last_modified" in result
        assert result["days_since_modified"] == 0

    def test_freshness_181_to_365_days(self, tmp_path, monkeypatch):
        """Line 222: 180 < days_ago <= 365 → health_score += 0.25."""
        monkeypatch.setattr(mod, "REPO", tmp_path)
        cat = tmp_path / "old"
        cat.mkdir()
        content = """---
name: "OldAgent"
description: "Agent last modified 200 days ago to test freshness partial credit"
emoji: "X"
color: red
---

## Identity
Identity content here for the agent testing freshness with partial credit scoring.

## Core Mission
Mission content here for testing purposes and word count requirements.

## Critical Rules
Rules content here for the agent to follow strictly always.

## Deliverables
Deliverables content for agent workflow testing.

## Workflow
Workflow content here for agent testing purposes.
"""
        f = cat / "old.md"
        f.write_text(content, encoding="utf-8")
        monkeypatch.setattr(mod, "git_last_modified",
                           lambda fp: date.today() - timedelta(days=200))
        result = score_agent(f, check_freshness=True)
        assert result["days_since_modified"] == 200

    def test_freshness_over_365_days(self, tmp_path, monkeypatch):
        """Line 224: days_ago > 365 → stale issue, no health credit."""
        monkeypatch.setattr(mod, "REPO", tmp_path)
        cat = tmp_path / "stale"
        cat.mkdir()
        content = """---
name: "StaleAgent"
description: "Agent last modified 400 days ago to test stale detection"
emoji: "X"
color: red
---

## Identity
Identity content here for the agent testing stale detection with old modification dates.

## Core Mission
Mission content here for testing purposes and word count requirements.

## Critical Rules
Rules content here for the agent to follow strictly always.

## Deliverables
Deliverables content for agent workflow testing.

## Workflow
Workflow content here for agent testing purposes.
"""
        f = cat / "stale.md"
        f.write_text(content, encoding="utf-8")
        monkeypatch.setattr(mod, "git_last_modified",
                           lambda fp: date.today() - timedelta(days=400))
        result = score_agent(f, check_freshness=True)
        assert result["days_since_modified"] == 400
        assert any("stale" in i.lower() for i in result["issues"])

    def test_no_freshness_check(self, tmp_path, monkeypatch):
        """Line 215: check_freshness=False skips git check."""
        monkeypatch.setattr(mod, "REPO", tmp_path)
        cat = tmp_path / "nofresh"
        cat.mkdir()
        content = """---
name: "NoFreshAgent"
description: "Agent tested with check_freshness=False to skip git date check"
emoji: "X"
color: red
---

## Identity
Identity content here for the agent testing with freshness check disabled.

## Core Mission
Mission content here for testing purposes and word count requirements.

## Critical Rules
Rules content here for the agent to follow strictly always.

## Deliverables
Deliverables content for agent workflow testing.

## Workflow
Workflow content here for agent testing purposes.
"""
        f = cat / "nofresh.md"
        f.write_text(content, encoding="utf-8")
        # monkeypatch git_last_modified to raise if called
        monkeypatch.setattr(mod, "git_last_modified",
                           lambda fp: (_ for _ in ()).throw(RuntimeError("should not be called")))
        result = score_agent(f, check_freshness=False)
        assert "days_since_modified" not in result
        assert "last_modified" not in result

    def test_grade_d(self, tmp_path):
        """Line 242: total < 3 → grade D."""
        content = """---
name: "Bad"
---

## Identity
tiny
"""
        f = tmp_path / "bad.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["grade"] == "D"

    def test_grade_c(self, tmp_path):
        """Line 240: 3 <= total < 5 → grade C."""
        content = """---
name: "CAgent"
description: "Agent that should get a C grade with moderate quality"
emoji: "X"
color: red
---

## Identity
Some identity content here.

## Core Mission
Some mission content.

## Critical Rules
Some rules content.
"""
        f = tmp_path / "cagent.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["grade"] in ("C", "B", "A")

    def test_relative_to_value_error(self, tmp_path, monkeypatch):
        """Lines 80-81: filepath not under REPO → uses filepath.name for rel."""
        # tmp_path is not under the real REPO, so relative_to raises ValueError
        cat = tmp_path / "outside"
        cat.mkdir()
        content = """---
name: "Outside"
description: "Agent outside REPO to test the ValueError fallback path in relative_to"
emoji: "X"
color: red
---

## Identity
Identity content here for the agent testing outside REPO location.

## Core Mission
Mission content here for testing purposes and word count.

## Critical Rules
Rules content here for the agent to follow.

## Deliverables
Deliverables content for agent.

## Workflow
Workflow content here for agent.
"""
        f = cat / "outside.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["path"] == "outside.md"


# ── print_terminal_report tests ──────────────────────────────────────────────

def _make_result(agent_id="test", category="testing", total=7, grade="B",
                 word_count=500, broken_links=0, scores=None, issues=None,
                 sections_found=5, file_size_kb=3.0, path=None,
                 last_modified=None, days_since_modified=None):
    """Helper to build a result dict like score_agent returns."""
    d = {
        "id": agent_id,
        "category": category,
        "path": path or f"{category}/{agent_id}.md",
        "total": total,
        "grade": grade,
        "scores": scores or {"content_depth": 3, "structure": 2,
                             "frontmatter": 1, "file_health": 1},
        "word_count": word_count,
        "sections_found": sections_found,
        "file_size_kb": file_size_kb,
        "issues": issues or [],
        "broken_links": broken_links,
    }
    if last_modified is not None:
        d["last_modified"] = last_modified
    if days_since_modified is not None:
        d["days_since_modified"] = days_since_modified
    return d


class TestPrintTerminalReport:
    """Tests for print_terminal_report() covering lines 254-336."""

    def _make_args(self, category=None, threshold=0, json=False, no_freshness=False):
        class Args:
            pass
        args = Args()
        args.category = category
        args.threshold = threshold
        args.json = json
        args.no_freshness = no_freshness
        return args

    def test_basic_report(self, capsys):
        """Basic terminal report with mixed grades."""
        results = [
            _make_result("a1", "t", 9, "A"),
            _make_result("a2", "t", 6, "B"),
            _make_result("a3", "t", 3, "C"),
        ]
        print_terminal_report(results, self._make_args())
        captured = capsys.readouterr()
        assert "Agent Quality Report" in captured.out
        assert "Score Distribution" in captured.out

    def test_quality_gate_pass(self, capsys):
        """Line 283: A/B >= 60% → PASS."""
        results = [
            _make_result("a1", "t", 9, "A"),
            _make_result("a2", "t", 9, "A"),
            _make_result("a3", "t", 6, "B"),
        ]
        print_terminal_report(results, self._make_args())
        captured = capsys.readouterr()
        assert "PASS" in captured.out

    def test_quality_gate_fail(self, capsys):
        """Line 286: A/B < 60% → FAIL."""
        results = [
            _make_result("a1", "t", 9, "A"),
            _make_result("a2", "t", 3, "C"),
            _make_result("a3", "t", 1, "D"),
        ]
        print_terminal_report(results, self._make_args())
        captured = capsys.readouterr()
        assert "FAIL" in captured.out

    def test_with_category_filter(self, capsys):
        """Line 265-266: category filter shown."""
        results = [_make_result("a1", "engineering", 9, "A")]
        print_terminal_report(results, self._make_args(category="engineering"))
        captured = capsys.readouterr()
        assert "Category: engineering" in captured.out

    def test_top_10_when_fewer(self, capsys):
        """Lines 290-296: top 10 shown with fewer agents."""
        results = [
            _make_result("a1", "t", 9, "A"),
            _make_result("a2", "t", 6, "B"),
        ]
        print_terminal_report(results, self._make_args())
        captured = capsys.readouterr()
        assert "Top 10" in captured.out

    def test_bottom_10_with_issues(self, capsys):
        """Lines 300-306: bottom 10 shows issues."""
        results = [
            _make_result("low", "t", 1, "D",
                        issues=["too short", "missing sections"]),
            _make_result("mid", "t", 5, "B"),
            _make_result("high", "t", 9, "A"),
        ]
        print_terminal_report(results, self._make_args())
        captured = capsys.readouterr()
        assert "Bottom 10" in captured.out

    def test_category_averages(self, capsys):
        """Lines 311-318: category averages with A/D counts."""
        results = [
            _make_result("a1", "engineering", 9, "A"),
            _make_result("a2", "engineering", 1, "D"),
            _make_result("a3", "design", 6, "B"),
        ]
        print_terminal_report(results, self._make_args())
        captured = capsys.readouterr()
        assert "Category Averages" in captured.out

    def test_perimeter_stats(self, capsys):
        """Lines 322-328: perimeter stats for short/stale/broken."""
        results = [
            _make_result("a1", "t", 9, "A", word_count=50),
            _make_result("a2", "t", 7, "B", days_since_modified=400),
            _make_result("a3", "t", 5, "B", broken_links=3),
        ]
        print_terminal_report(results, self._make_args())
        captured = capsys.readouterr()
        assert "Perimeter" in captured.out
        assert "short" in captured.out.lower()
        assert "stale" in captured.out.lower()
        assert "broken" in captured.out.lower()

    def test_threshold_fail(self, capsys):
        """Lines 331-336: threshold check FAIL when agents below threshold."""
        results = [
            _make_result("a1", "t", 3, "C"),
            _make_result("a2", "t", 9, "A"),
        ]
        print_terminal_report(results, self._make_args(threshold=5))
        captured = capsys.readouterr()
        assert "THRESHOLD FAIL" in captured.out

    def test_threshold_pass(self, capsys):
        """Lines 335-336: threshold check PASS when all agents above threshold."""
        results = [
            _make_result("a1", "t", 9, "A"),
            _make_result("a2", "t", 7, "B"),
        ]
        print_terminal_report(results, self._make_args(threshold=5))
        captured = capsys.readouterr()
        assert "THRESHOLD PASS" in captured.out

    def test_threshold_zero_all_pass(self, capsys):
        """Line 331: threshold=0 (truthy-falsy edge) → still checks since not None."""
        results = [_make_result("a1", "t", 1, "D")]
        print_terminal_report(results, self._make_args(threshold=0))
        captured = capsys.readouterr()
        # threshold=0 is not None, so the check runs; all scores >= 0 => PASS
        assert "THRESHOLD PASS" in captured.out

    def test_grade_bar_display(self, capsys):
        """Lines 270-276: each grade level shows count, percentage, bar."""
        results = [
            _make_result("a1", "t", 9, "A"),
            _make_result("b1", "t", 6, "B"),
            _make_result("c1", "t", 3, "C"),
            _make_result("d1", "t", 1, "D"),
        ]
        print_terminal_report(results, self._make_args())
        captured = capsys.readouterr()
        # All four grade labels should appear
        for label in ("A (8-10)", "B (5-7)", "C (3-4)", "D (0-2)"):
            assert label in captured.out

    def test_no_agents_displays_zero(self, capsys):
        """Report with zero agents (empty results list)."""
        print_terminal_report([], self._make_args())
        captured = capsys.readouterr()
        assert "Total: 0 agents" in captured.out


# ── print_json_report tests ──────────────────────────────────────────────────

class TestPrintJsonReport:
    """Tests for print_json_report() covering lines 341-372."""

    def test_outputs_valid_json(self, capsys):
        """Valid JSON output with all fields."""
        results = [_make_result("test", "testing", 9, "A")]
        print_json_report(results)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["total_agents"] == 1
        assert len(data["agents"]) == 1
        a = data["agents"][0]
        assert a["id"] == "test"
        assert a["grade"] == "A"
        assert "scores" in a

    def test_multiple_agents(self, capsys):
        results = [
            _make_result("a1", "t1", 9, "A"),
            _make_result("a2", "t2", 3, "C"),
        ]
        print_json_report(results)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["total_agents"] == 2
        assert len(data["agents"]) == 2

    def test_quality_gate_in_output(self, capsys):
        """Lines 366-369: quality_gate field PASS/FAIL."""
        results = [
            _make_result("a1", "t", 9, "A"),
            _make_result("a2", "t", 9, "A"),
        ]
        print_json_report(results)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "quality_gate" in data
        assert data["quality_gate"] == "PASS"

    def test_quality_gate_fail(self, capsys):
        """Quality gate FAIL when A+B < 60%."""
        results = [
            _make_result("a1", "t", 2, "D"),
            _make_result("a2", "t", 4, "C"),
            _make_result("a3", "t", 3, "C"),
        ]
        print_json_report(results)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["quality_gate"] == "FAIL"

    def test_grade_distribution_in_output(self, capsys):
        results = [
            _make_result("a1", "t", 9, "A"),
            _make_result("a2", "t", 6, "B"),
            _make_result("a3", "t", 3, "C"),
        ]
        print_json_report(results)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "grade_distribution" in data
        assert data["grade_distribution"]["A"] == 1
        assert data["grade_distribution"]["B"] == 1
        assert data["grade_distribution"]["C"] == 1


# ── main() tests ─────────────────────────────────────────────────────────────

class TestMain:
    """Tests for main() covering lines 378-428."""

    def test_main_default_terminal_report(self, monkeypatch):
        """Lines 415-418: default mode calls print_terminal_report."""
        reports = []
        monkeypatch.setattr(mod, "print_terminal_report",
                           lambda results, args: reports.append(True))
        monkeypatch.setattr(sys, "argv", ["score-agents.py"])
        # discover_agents will find real agents; monkeypatch to return one
        monkeypatch.setattr(mod, "discover_agents",
                           lambda category_filter=None: [("test", "test/test.md",
                                                          REPO / "test" / "test.md")])
        monkeypatch.setattr(mod, "score_agent",
                           lambda fp, check_freshness=True: _make_result())
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 0
        assert len(reports) == 1

    def test_main_json_mode(self, monkeypatch):
        """Lines 415-416: --json flag calls print_json_report."""
        json_reports = []
        monkeypatch.setattr(mod, "print_json_report",
                           lambda results: json_reports.append(True))
        monkeypatch.setattr(sys, "argv", ["score-agents.py", "--json"])
        monkeypatch.setattr(mod, "discover_agents",
                           lambda category_filter=None: [("test", "test/test.md",
                                                          REPO / "test" / "test.md")])
        monkeypatch.setattr(mod, "score_agent",
                           lambda fp, check_freshness=True: _make_result())
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 0
        assert len(json_reports) == 1

    def test_main_file_mode(self, tmp_path, monkeypatch):
        """Lines 393-400: --file flag scores a single file."""
        f = tmp_path / "single.md"
        content = """---
name: "SingleFile"
description: "A single file agent for testing the --file flag in main"
emoji: "X"
color: red
---

## Identity
Identity content here for the single file agent testing.

## Core Mission
Mission content here for testing purposes.

## Critical Rules
Rules content here for the agent.

## Deliverables
Deliverables content for agent.

## Workflow
Workflow content here for agent.
"""
        f.write_text(content, encoding="utf-8")
        monkeypatch.setattr(mod, "REPO", tmp_path)
        reports = []
        monkeypatch.setattr(mod, "print_terminal_report",
                           lambda results, args: reports.append(results))
        monkeypatch.setattr(sys, "argv", ["score-agents.py", "--file", str(f)])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 0
        assert len(reports) == 1
        assert reports[0][0]["id"] == "single"

    def test_main_file_not_found(self, monkeypatch, capsys):
        """Lines 397-399: --file with non-existent path → stderr + exit 1."""
        monkeypatch.setattr(sys, "argv",
                           ["score-agents.py", "--file", "/nonexistent/path.md"])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "file not found" in captured.err.lower() or "ERROR" in captured.err

    def test_main_no_files_found(self, monkeypatch):
        """Line 404-406: discover_agents returns empty → stderr + exit 1."""
        monkeypatch.setattr(mod, "discover_agents",
                           lambda category_filter=None: [])
        monkeypatch.setattr(sys, "argv", ["score-agents.py", "--category", "nonexistent"])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 1

    def test_main_threshold_ci_gate_fail(self, monkeypatch):
        """Lines 421-426: threshold CI gate exits 1 when agents below."""
        monkeypatch.setattr(mod, "discover_agents",
                           lambda category_filter=None: [("test", "test/test.md",
                                                          REPO / "test" / "test.md")])
        monkeypatch.setattr(mod, "score_agent",
                           lambda fp, check_freshness=True: _make_result(total=3, grade="C"))
        monkeypatch.setattr(mod, "print_terminal_report",
                           lambda results, args: None)
        monkeypatch.setattr(sys, "argv", ["score-agents.py", "--threshold", "5"])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 1

    def test_main_no_threshold_ci_gate_pass(self, monkeypatch):
        """Lines 421: threshold=0 (default) → no CI gate check."""
        monkeypatch.setattr(mod, "discover_agents",
                           lambda category_filter=None: [("test", "test/test.md",
                                                          REPO / "test" / "test.md")])
        monkeypatch.setattr(mod, "score_agent",
                           lambda fp, check_freshness=True: _make_result(total=1, grade="D"))
        monkeypatch.setattr(mod, "print_terminal_report",
                           lambda results, args: None)
        monkeypatch.setattr(sys, "argv", ["score-agents.py"])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 0

    def test_main_no_freshness_passed(self, monkeypatch, tmp_path):
        """--no-freshness flag is passed to score_agent."""
        monkeypatch.setattr(mod, "REPO", tmp_path)
        cat = tmp_path / "cat"
        cat.mkdir()
        content = """---
name: "NoFreshMain"
description: "Agent for testing --no-freshness flag passed through main function"
emoji: "X"
color: red
---

## Identity
Identity content here for the agent testing no-freshness flag in main.

## Core Mission
Mission content here for testing purposes.

## Critical Rules
Rules content here for the agent to follow.

## Deliverables
Deliverables content for agent.

## Workflow
Workflow content here for agent.
"""
        (cat / "nofresh.md").write_text(content, encoding="utf-8")
        score_calls = []
        monkeypatch.setattr(mod, "score_agent",
                           lambda fp, check_freshness=True: score_calls.append(check_freshness) or _make_result())
        monkeypatch.setattr(mod, "discover_agents",
                           lambda category_filter=None: [("cat", "cat/nofresh.md",
                                                          cat / "nofresh.md")])
        monkeypatch.setattr(mod, "print_terminal_report",
                           lambda results, args: None)
        monkeypatch.setattr(sys, "argv", ["score-agents.py", "--no-freshness"])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 0
        assert score_calls[0] is False

    def test_main_category_filter(self, monkeypatch):
        """--category filter is forwarded to discover_agents."""
        discover_calls = []

        def _track(category_filter=None):
            discover_calls.append(category_filter)
            return [("test", "test/test.md", REPO / "test" / "test.md")]

        monkeypatch.setattr(mod, "discover_agents", _track)
        monkeypatch.setattr(mod, "score_agent",
                           lambda fp, check_freshness=True: _make_result())
        monkeypatch.setattr(mod, "print_terminal_report",
                           lambda results, args: None)
        monkeypatch.setattr(sys, "argv",
                           ["score-agents.py", "--category", "design"])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 0
        assert discover_calls[0] == "design"
