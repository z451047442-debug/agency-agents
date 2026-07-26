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
score_agent_v7 = mod.score_agent_v7
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
        # v2: word_count no longer directly scored; short content gets 0 expertise

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
        assert result["scores"]["content_depth"] == 0

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
        assert result["scores"]["content_depth"] == 0  # 500 words=wc 0.5, ds=0, ac=0 → round(0.5)=0

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
        assert result["scores"]["content_depth"] == 0  # v2: no tools/cases in 'word '*850

    def test_seven_sections_sec_score_3(self, tmp_path):
        """7 sections each with 30+ substantive words → sec_score = 3."""
        P = "test content " * 30  # 30 words of padding
        content = f"""---
name: "SevenSections"
description: "Agent with all seven sections matching to get the max structure score of three"
emoji: "X"
color: red
---

## Your Identity
Identity content here. {P}

## Your Core Mission
Mission content here. {P}

## Critical Rules You Must Follow
Rules content here. {P}

## Deliverables
Deliverables content here. {P}

## Workflow
Workflow content here. {P}

## Success Metrics
Metrics content here. {P}

## Communication Style
Communication content here. {P}
"""
        f = tmp_path / "seven.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["scores"]["structure"] == 1  # v3: max structure is 1

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
        """Well-crafted agent with domain depth + full sections → grade A (≥9)."""
        P = "test content " * 30  # 30-word padding for substantive sections
        # Domain terms + actionable items to reach content_depth=3
        domain_terms = (
            "AWS Lambda EC2 S3 DynamoDB RDS CloudFormation "
            "Terraform Kubernetes Helm ArgoCD Istio Prometheus Grafana "
            "CI/CD GitOps DevSecOps SLI SLO error budget "
        )
        actionables = (
            "- You must verify infrastructure as code before deployment. "
            "- Always check security group rules for least privilege. "
            "- Ensure IAM policies follow principle of least privilege. "
            "- Validate Terraform plan output before applying changes. "
            "- Monitor CloudWatch metrics for any anomalous patterns. "
            "- You should use AWS Well-Architected Framework as reference. "
            "- Never expose secrets in plaintext configuration files. "
            "- Always encrypt data at rest and in transit using KMS. "
            "- Implement proper error handling with exponential backoff. "
            "- Document all architectural decisions in ADR format. "
            "- Use infrastructure drift detection to maintain compliance. "
            "- Regular penetration testing is mandatory for production systems. "
        )
        content = f"""---
name: "AGrade"
description: "{'A' * 80}"
emoji: "X"
color: red
vibe: professional
nexus_roles: ["Discovery"]
---

## Your Identity
Cloud infrastructure architect with deep expertise in AWS, Terraform, and Kubernetes. {domain_terms} {P}

## Your Core Mission
Design and implement secure, scalable cloud infrastructure following Well-Architected principles. {P}

## Critical Rules You Must Follow
{actionables} {P}

## Deliverables
Infrastructure as Code templates, architecture diagrams, security compliance reports. {P}

## Workflow
Assess requirements, design architecture, implement IaC, validate security, deploy. {P}

## Success Metrics
Infrastructure uptime SLO, deployment frequency, mean time to recovery, cost optimization. {P}

## Communication Style
Clear technical communication with architecture decision records and runbooks. {P}
"""
        f = tmp_path / "agrade.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["grade"] in ("A", "B")  # well-crafted agent should score A or B

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
        """3 substantive sections → sec_score = 1 (need 2+ substantive for 1 pt)."""
        P = "test content " * 30
        content = f"""---
name: "ThreeSections"
description: "Agent with three matching sections"
emoji: "X"
color: red
---

## Identity
Identity content here. {P}

## Core Mission
Mission content here. {P}

## Critical Rules You Must Follow
Rules content here. {P}
"""
        f = tmp_path / "three.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["scores"]["structure"] == 0  # v2: 3 substantive → 0 pt (need ≥4 for 1)

    def test_five_sections_sec_score_2(self, tmp_path):
        """5 substantive sections → sec_score = 1 (need >=6 for 2 pts in v2)."""
        P = "test content " * 30
        content = f"""---
name: "FiveSections"
description: "Agent with five matching sections"
emoji: "X"
color: red
---

## Identity
Identity content here. {P}

## Core Mission
Mission content here. {P}

## Critical Rules
Rules content here. {P}

## Deliverables
Deliverables content here. {P}

## Workflow
Workflow content here. {P}
"""
        f = tmp_path / "five.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["scores"]["structure"] == 1  # v2: 5 substantive → 1 pt (need ≥6 for 2)

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
        """Agent with moderate domain content should score grade C."""
        P = "test content " * 10  # padding for section length
        domain = "Docker Kubernetes Terraform AWS CI/CD pipeline"
        content = f"""---
name: "CAgent"
description: "Agent that should get a C grade with moderate domain expertise and tool references"
emoji: "X"
color: red
---

## Identity
DevOps engineer specializing in cloud infrastructure. {domain} {P}

## Core Mission
Design and implement containerized applications and cloud infrastructure. {P}

## Critical Rules
Never deploy to production without approval. Validate all inputs. {P}

## Deliverables
I produce deployment manifests, Dockerfiles, and CI/CD pipeline configurations. {P}

## Workflow
Step 1: Assess current infrastructure state. Step 2: Design architecture. Step 3: Implement changes. {P}
"""
        f = tmp_path / "cagent.md"
        f.write_text(content, encoding="utf-8")
        result = score_agent(f)
        assert result["grade"] == "C"

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
            _make_result("a1", "t", 13, "A"),
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
            _make_result("a1", "t", 13, "A"),
            _make_result("a2", "t", 9, "A"),
            _make_result("a3", "t", 6, "B"),
        ]
        print_terminal_report(results, self._make_args())
        captured = capsys.readouterr()
        assert "PASS" in captured.out

    def test_quality_gate_fail(self, capsys):
        """Line 286: A/B < 60% → FAIL."""
        results = [
            _make_result("a1", "t", 13, "A"),
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
            _make_result("a1", "t", 13, "A"),
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
            _make_result("a1", "t", 13, "A"),
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
            _make_result("a1", "t", 13, "A"),
            _make_result("b1", "t", 11, "B"),
            _make_result("c1", "t", 9, "C"),
            _make_result("d1", "t", 5, "D"),
        ]
        print_terminal_report(results, self._make_args())
        captured = capsys.readouterr()
        # All four grade labels should appear
        for label in ("A (≥12.5)", "B (10-12)", "C (8-10)", "D (<8)"):
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
            _make_result("a1", "t", 13, "A"),
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
            _make_result("a1", "t", 13, "A"),
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
    pytestmark = pytest.mark.skip(reason="removed in v7 unification")
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
                           lambda results, v5_results=None, v6_results=None, v7_results=None: json_reports.append(True))
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

    def test_main_min_score_floor_fail(self, monkeypatch, tmp_path):
        """--min-score gate fails when agent scores below absolute floor."""
        cat = tmp_path / "testing"
        cat.mkdir()
        r = _make_result(total=3, agent_id="testing-fail", category="testing")
        monkeypatch.setattr(mod, "discover_agents",
                           lambda category_filter=None: [
                               ("testing", "testing/testing-fail.md", cat / "fail.md")
                           ])
        monkeypatch.setattr(mod, "score_agent",
                           lambda fp, check_freshness=True: r)
        monkeypatch.setattr(mod, "print_terminal_report",
                           lambda results, args: None)
        monkeypatch.setattr(sys, "argv",
                           ["score-agents.py", "--min-score", "5"])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 1

    def test_main_min_score_floor_pass(self, monkeypatch, tmp_path):
        """--min-score gate passes when all agents meet the floor."""
        cat = tmp_path / "testing"
        cat.mkdir()
        r = _make_result(total=8, agent_id="testing-pass", category="testing")
        monkeypatch.setattr(mod, "discover_agents",
                           lambda category_filter=None: [
                               ("testing", "testing/testing-pass.md", cat / "pass.md")
                           ])
        monkeypatch.setattr(mod, "score_agent",
                           lambda fp, check_freshness=True: r)
        monkeypatch.setattr(mod, "print_terminal_report",
                           lambda results, args: None)
        monkeypatch.setattr(sys, "argv",
                           ["score-agents.py", "--min-score", "5"])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 0


# ── v5 scoring tests ───────────────────────────────────────────────────────────

V5_MINIMAL_AGENT = """---
name: "Minimal Agent"
description: "A minimal agent"
emoji: "\U0001f310"
color: gray
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
I am a test agent.

## Mission
Help with things.

## Rules
Be helpful.

## Deliverables
General assistance.

## Workflow
Do the work.
"""


# ── V7 test constants ─────────────────────────────────────────────────────────

V7_RICH_AGENT = """---
name: "V7 Expert Agent"
description: "Deep expertise agent with safeguards, decision models, and edge cases"
emoji: "💡"
color: teal
version: "1.0.0"
date_added: "2026-07-03"
depends_on:
  - cybersecurity-penetration-tester
  - engineering-frontend-developer
  - design-ui-designer
---

## Identity
V7 test agent with Kubernetes, Docker, Terraform, Ansible, Jenkins, Prometheus,
Grafana, and ELK Stack expertise. For standards, follow ISO 27001 and NIST SP 800-53.

## Mission
Deliver production-grade infrastructure. When using Kubernetes, choose between
Deployment and StatefulSet based on workload persistence needs. For monitoring,
prefer Prometheus over ELK for metrics but use ELK for log aggregation.

## Rules
1. Always verify with a qualified professional before deploying to production.
2. Within your scope: infrastructure design. Outside scope: legal compliance.
3. Escalate to human when dealing with production incidents.

## Deliverables
| Deliverable | Format | Contents |
|-------------|--------|----------|
| Architecture Diagram | Draw.io + ASCII | Network topology, data flow |
| Risk Assessment | Markdown report | Threat model, mitigation plan |

## Workflow
1. Assess current infrastructure against ISO 27001 Annex A controls.
2. Choose monitoring stack: Prometheus for metrics, ELK for logs, Grafana for dashboards.
3. When trade-offs arise, document both options.

## Communication Style
Direct and technical. Reference NIST SP 800-53 Rev. 5 where applicable.


## Methodology Decision Framework

### Decision Matrix: Tool Selection by Scenario
| Scenario | Condition | Recommended Tool | Rationale |
|---|---|---|---|
| High-throughput data pipeline | Data volume > 1TB/day, latency > 5s | Apache Spark | Batch-optimized |
| Real-time event processing | Latency < 100ms, event rate > 10K/s | Kafka + Flink | Sub-100ms end-to-end |
| Ad-hoc analytical queries | Response < 2s, < 50 concurrent users | Snowflake | Serverless scaling |

### Quantitative Decision Triggers
- **When to add read replicas**: if p95 query latency > 200ms AND read:write ratio > 5:1 -> add read replicas; but if write contention is the bottleneck -> consider sharding first
- **When to enable auto-scaling**: if peak:off-peak ratio > 3:1 AND instance cost > 000/month -> enable HPA with 50% target CPU; otherwise use scheduled scaling

## Limitations & Constraints

### What This Agent Cannot Do
- Cannot provide legally binding advice or make decisions on your behalf
- Not designed for real-time incident response requiring sub-second latency
- Outside its scope: hardware-level debugging, physical security assessments,
  and regulatory filings that require licensed professional sign-off

### When to Consult a Real Expert
- If the situation involves life-safety systems or critical infrastructure
- When financial transactions exceed organizational risk thresholds
- When legal compliance precedents are ambiguous or contradictory

## Collaboration Protocol

### Inputs Expected from Other Agents
- **From Discovery Agent**: problem domain classification, stakeholder requirements
- **From Architecture Agent**: system design decisions, technology stack choices
- **From Security Agent**: threat model, compliance requirements, security findings

### Outputs Produced for Downstream Agents
- **To Implementation Agent**: validated design spec with acceptance criteria
- **To Testing Agent**: test scenarios, edge case catalog, expected behavior matrix
- **To Documentation Agent**: architecture decision records, methodology rationale

## Edge Cases & Common Pitfalls

### Tricky Scenarios
- **Multi-region deployments**: when latency between regions exceeds 50ms, the standard
  consistency model breaks down. Use the regional-failover pattern instead.
- **Schema migrations with zero downtime**: the common expand-contract approach works
  for additive changes but fails for column renames. Watch for ORM cache invalidation.

### Common Mistakes to Avoid
- Configuring connection pools based on peak load but forgetting cold-start overhead
- Treating all errors as retry-able — idempotency must be verified for payment operations
"""


# ── V7 tests ──────────────────────────────────────────────────────────────────

class TestScoreAgentV7:
    """Tests for score_agent_v7() function."""

    def test_returns_v7_dict_structure(self, tmp_path):
        f = tmp_path / "testing" / "v7-struct.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(V7_RICH_AGENT, encoding="utf-8")
        result = score_agent_v7(f, check_freshness=False)
        assert isinstance(result, dict)
        for key in ("v7_scores", "v7_total", "v7_grade", "v7_improvement_plan",
                    "v7_gate_passed", "v7_gate_failures"):
            assert key in result, f"Missing: {key}"

    def test_rich_agent_scores_high(self, tmp_path):
        f = tmp_path / "testing" / "v7-rich.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(V7_RICH_AGENT, encoding="utf-8")
        result = score_agent_v7(f, check_freshness=False)
        assert result["v7_total"] >= 13
        assert result["v7_grade"] in ("A", "B")

    def test_rich_agent_gate_passes(self, tmp_path):
        f = tmp_path / "testing" / "v7-gate.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(V7_RICH_AGENT, encoding="utf-8")
        result = score_agent_v7(f, check_freshness=False)
        assert result["v7_gate_passed"] is True
        assert result["v7_gate_failures"] == []

    def test_minimal_agent_scores_low(self, tmp_path):
        f = tmp_path / "testing" / "v7-min.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(V5_MINIMAL_AGENT, encoding="utf-8")
        result = score_agent_v7(f, check_freshness=False)
        assert result["v7_total"] <= 12

    def test_constraint_awareness_detected(self, tmp_path):
        f = tmp_path / "testing" / "v7-constraint.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(V7_RICH_AGENT, encoding="utf-8")
        result = score_agent_v7(f, check_freshness=False)
        assert result["v7_scores"]["constraint_awareness"] >= 0.5

    def test_collab_protocol_detected(self, tmp_path):
        f = tmp_path / "testing" / "v7-collab.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(V7_RICH_AGENT, encoding="utf-8")
        result = score_agent_v7(f, check_freshness=False)
        assert result["v7_scores"]["collab_protocol"] >= 0.5

    def test_edge_cases_detected(self, tmp_path):
        f = tmp_path / "testing" / "v7-edge.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(V7_RICH_AGENT, encoding="utf-8")
        result = score_agent_v7(f, check_freshness=False)
        assert result["v7_scores"]["edge_cases"] >= 0.5

    def test_method_decision_model_expanded(self, tmp_path):
        f = tmp_path / "testing" / "v7-dm.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(V7_RICH_AGENT, encoding="utf-8")
        result = score_agent_v7(f, check_freshness=False)
        assert result["v7_scores"]["method_decision_model"] >= 1.0

    def test_v7_scores_excludes_gate_dimensions(self, tmp_path):
        f = tmp_path / "testing" / "v7-nogate.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(V7_RICH_AGENT, encoding="utf-8")
        result = score_agent_v7(f, check_freshness=False)
        assert "safeguards" not in result["v7_scores"]
        assert "output_spec" not in result["v7_scores"]

    def test_v7_improvement_plan_includes_new_dimensions(self, tmp_path):
        f = tmp_path / "testing" / "v7-plan.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(V5_MINIMAL_AGENT, encoding="utf-8")
        result = score_agent_v7(f, check_freshness=False)
        dims = [p["dim"] for p in result["v7_improvement_plan"]]
        for dim in ("constraint_awareness", "collab_protocol", "edge_cases"):
            assert dim in dims, f"Missing: {dim}"


class TestV7GradeThresholds:
    """Tests for _compute_v7_grade tiered thresholds."""

    def test_critical_a(self):
        assert mod._compute_v7_grade(16, "critical") == "A"
        assert mod._compute_v7_grade(10.5, "critical") == "B"

    def test_critical_b(self):
        assert mod._compute_v7_grade(11, "critical") == "B"
        assert mod._compute_v7_grade(10.4, "critical") == "C"

    def test_critical_c(self):
        assert mod._compute_v7_grade(8.5, "critical") == "C"
        assert mod._compute_v7_grade(8.4, "critical") == "D"

    def test_general_a(self):
        assert mod._compute_v7_grade(15, "general") == "A"
        assert mod._compute_v7_grade(12.4, "general") == "B"

    def test_general_b(self):
        assert mod._compute_v7_grade(10, "general") == "B"
        assert mod._compute_v7_grade(9, "general") == "C"

    def test_general_c(self):
        assert mod._compute_v7_grade(8, "general") == "C"
        assert mod._compute_v7_grade(7.9, "general") == "D"

    def test_high_same_as_general(self):
        assert mod._compute_v7_grade(12.5, "high") == "A"
        assert mod._compute_v7_grade(10, "high") == "B"


class TestV7Gate:
    """Tests for v7 gate logic: gate failure must produce grade D."""

    def test_gate_fails_when_no_safeguards(self, tmp_path):
        content = """---
name: "No Safeguards Agent"
description: "Agent without safeguards for testing"
emoji: "\\U0001f527"
color: blue
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
Test agent identity.

## Mission
Test mission statement.

## Deliverables
- **Assessment Report** (Markdown, PDF): findings and recommendations per ISO 9001

## Workflow
1. Assess the situation and gather all inputs.
2. Analyze findings and formulate recommendations.
"""
        f = tmp_path / "testing" / "v7-nosafe.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
        result = score_agent_v7(f, check_freshness=False)
        assert result["v7_gate_passed"] is False
        assert result["v7_grade"] == "D"
        assert any("safeguards" in f for f in result["v7_gate_failures"])

    def test_gate_fails_when_no_output_spec(self, tmp_path):
        content = """---
name: "No Output Agent"
description: "Agent without output spec for testing"
emoji: "\\U0001f527"
color: blue
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
Test agent identity.

## Mission
Test mission statement.

## Professional Scope & Safeguards
This agent provides advisory guidance only. Consult a qualified professional
before making decisions that carry legal, financial, or safety implications.

## Workflow
1. Assess the situation.
2. Analyze findings.
"""
        f = tmp_path / "testing" / "v7-nooutput.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
        result = score_agent_v7(f, check_freshness=False)
        assert result["v7_gate_passed"] is False
        assert result["v7_grade"] == "D"
        assert any("output_spec" in f for f in result["v7_gate_failures"])

    def test_gate_fails_when_both_missing(self, tmp_path):
        content = """---
name: "Minimal Agent"
description: "Bare minimum agent"
emoji: "\\U0001f527"
color: blue
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
Test agent identity.
## Mission
Test mission statement.
"""
        f = tmp_path / "testing" / "v7-bothmissing.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
        result = score_agent_v7(f, check_freshness=False)
        assert result["v7_gate_passed"] is False
        assert result["v7_grade"] == "D"
        assert len(result["v7_gate_failures"]) == 2

    def test_gate_failure_is_d_even_with_high_other_scores(self, tmp_path):
        # Gate fails (no output_spec signals) but has safeguards + rich domain content.
        # No markdown tables, no code blocks, no "output:" sections to avoid
        # triggering _OUTPUT_SPEC_RE.
        content = """---
name: "Safeguards But No Output Spec"
description: "Has safeguards and rich content but zero output spec signals"
emoji: "\\U0001f527"
color: blue
version: "1.0.0"
date_added: "2026-07-03"
---

## Identity
Test agent with deep expertise in software architecture, Kubernetes orchestration,
AWS services, and distributed systems design per ISO 9001 quality standards.

## Mission
Provide architectural guidance based on NIST SP 800-53 and the AWS
Well-Architected Framework. Focus on reliability and performance efficiency.

## Professional Scope & Safeguards
This agent provides advisory guidance only. It is not a substitute for
professional engineering review. Consult a qualified architect before making
production-critical decisions. This agent cannot provision cloud resources,
modify live infrastructure, or make security group changes without human approval.

## Workflow
Gather all relevant information about the system and its constraints.
Analyze the requirements against established best practices and standards.
Formulate recommendations with explicit trade-offs and assumptions.
Review the guidance with stakeholders before finalizing any decisions.

## Limitations & Constraints
This agent cannot deploy to production, modify live infrastructure, or perform
hardware-level debugging. Not designed for real-time systems requiring
sub-millisecond latency. Cannot perform physical security assessments.

When to consult a real expert: if the system involves safety-critical functions
per IEC 62304, when financial exposure exceeds defined risk thresholds, or when
legal compliance precedents are ambiguous and require professional interpretation.

## Collaboration Protocol
Expected inputs from other agents include: problem domain classification from
Discovery Agent, threat models from Security Agent, and technology stack choices
from Architecture Agent.

This agent produces validated design decisions with acceptance criteria for
downstream Implementation Agents, edge case scenarios for Testing Agents, and
methodology rationale for Documentation Agents.

## Edge Cases & Common Pitfalls
Multi-region deployments are tricky when cross-region latency exceeds 50ms
because standard consistency models may break down. A common mistake is setting
connection pool sizes based only on peak load without accounting for cold-start
overhead after deployments. Another pitfall is treating all errors as safe to
retry without verifying idempotency for payment or transaction operations.

## References & Standards
- ISO 9001:2015 Quality Management Systems
- NIST SP 800-53 Security and Privacy Controls
- AWS Well-Architected Framework Reliability Pillar
- IEC 62304 Medical Device Software Lifecycle Processes
"""
        f = tmp_path / "testing" / "v7-highnogate.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
        result = score_agent_v7(f, check_freshness=False)
        # No markdown tables, code blocks, or structured output -> gate should fail
        assert result["v7_gate_passed"] is False
        assert result["v7_grade"] == "D"


class TestV7JsonOutput:
    pytestmark = pytest.mark.skip(reason="removed in v7 unification")
    """Tests for JSON report with v7 data."""

    def test_json_includes_v7(self, tmp_path):
        f = tmp_path / "testing" / "v7-json.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(V7_RICH_AGENT, encoding="utf-8")
        r = mod.score_agent(f, check_freshness=False)
        v7_r = score_agent_v7(f, check_freshness=False)
        buf = io.StringIO()
        sys.stdout = buf
        mod.print_json_report([r], v7_results=[v7_r])
        sys.stdout = sys.__stdout__
        data = json.loads(buf.getvalue())
        assert "v7" in data
        assert data["v7"]["agents"][0]["v7_total"] >= 10
        assert data["v7"]["agents"][0]["v7_gate_passed"] is True

    def test_json_includes_gate_info(self, tmp_path):
        f = tmp_path / "testing" / "v7-gatejson.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(V7_RICH_AGENT, encoding="utf-8")
        r = mod.score_agent(f, check_freshness=False)
        v7_r = score_agent_v7(f, check_freshness=False)
        buf = io.StringIO()
        sys.stdout = buf
        mod.print_json_report([r], v7_results=[v7_r])
        sys.stdout = sys.__stdout__
        data = json.loads(buf.getvalue())
        agent_entry = data["v7"]["agents"][0]
        assert "v7_gate_passed" in agent_entry
        assert "v7_gate_failures" in agent_entry

    def test_json_no_v7_when_not_passed(self, tmp_path):
        f = tmp_path / "testing" / "v7-nojson.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(V7_RICH_AGENT, encoding="utf-8")
        r = mod.score_agent(f, check_freshness=False)
        buf = io.StringIO()
        sys.stdout = buf
        mod.print_json_report([r])
        sys.stdout = sys.__stdout__
        data = json.loads(buf.getvalue())
        assert "v7" not in data


class TestV7BackwardCompat:
    """Verify v3/v5/v6 scoring unchanged after v7 additions."""

    def test_v3_fields_unchanged(self, tmp_path):
        f = tmp_path / "testing" / "v7-compat.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(SAMPLE, encoding="utf-8")
        result = score_agent(f, check_freshness=False)
