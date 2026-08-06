"""v1 scoring engine — scores a single agent file on 7 dimensions (0-10)."""

import re
from datetime import date
from pathlib import Path

from _shared import REPO, get_body, get_field, get_frontmatter_text, get_list_field
from _shared.validators import CORE_SECTIONS, git_last_modified

from scoring.patterns import _ACTIONABLE_RE
from scoring.signals import (
    _actionable_density,
    _compute_risk_tier,
    _count_boilerplate_matches,
    _count_case_examples,
    _count_domain_signals,
    _count_reference_signals,
    _count_safeguard_signals,
    _count_tool_references,
    _has_cross_category_deps,
    _section_body_words,
)

# Test files monkeypatch REPO/git_last_modified on the importlib-loaded shim
# module; engine looks up the patched namespace at call time.
_SHIMS = []
_REPO_DEFAULT = REPO
_GIT_DEFAULT = git_last_modified


def _register_shim(namespace):
    _SHIMS.append(namespace)


def _sync_repo():
    ns = _SHIMS[-1] if _SHIMS else None
    for candidate in _SHIMS:
        if (candidate.get("REPO") is not _REPO_DEFAULT
                or candidate.get("git_last_modified") is not _GIT_DEFAULT):
            ns = candidate
            break
    if ns is not None:
        globals()["REPO"] = ns.get("REPO", REPO)
        globals()["git_last_modified"] = ns.get("git_last_modified", git_last_modified)


# ── scoring engine ───────────────────────────────────────────────────────────

def score_agent(filepath, check_freshness=True):
    """Score a single agent file. Returns dict with scores and metadata.

    The return dict is backward-compatible with v1 consumers (contribute.py,
    expand-agent.py, quality-report.py). New fields (domain_signals,
    actionable_count, substantive_sections, risk_tier) are additive.
    """
    _sync_repo()
    filepath = Path(filepath)
    try:
        rel = str(filepath.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        rel = filepath.name

    result = {
        "id": filepath.stem,
        "category": filepath.parent.name,
        "path": rel,
        "scores": {},
        "total": 0,
        "grade": "D",
        "issues": [],
    }

    if not filepath.is_file():
        result["issues"].append("file not found")
        return result

    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        result["issues"].append("cannot read file (encoding?)")
        return result

    fm_text = get_frontmatter_text(content)
    body = get_body(content)
    risk_tier = _compute_risk_tier(filepath.parent.name)

    # ── Dimension 1: Content Expertise (0-4) ──
    # Expanded from 0-3 to 0-4 — this is the primary quality differentiator.
    # Three sub-dimensions: methodology/tool density + actionable density + case coverage
    word_count = len(body.split())

    # 1a. Methodology & Tools (0-1.5): named frameworks and tools signal real expertise
    tool_count = _count_tool_references(body)
    if tool_count >= 10:
        mt_score = 1.5
    elif tool_count >= 6:
        mt_score = 1.0
    elif tool_count >= 3:
        mt_score = 0.5
    elif tool_count >= 1:
        mt_score = 0.25
    else:
        mt_score = 0
    result["tool_references"] = tool_count

    # 1b. Actionable Density (0-1.5): directives per 100 words (not raw count)
    density = _actionable_density(body, word_count)
    if density >= 2.0:
        ad_score = 1.5
    elif density >= 1.2:
        ad_score = 1.0
    elif density >= 0.6:
        ad_score = 0.5
    elif density >= 0.3:
        ad_score = 0.25
    else:
        ad_score = 0

    # 1c. Case / Scenario Coverage (0-1): concrete examples, not abstract descriptions
    case_count = _count_case_examples(body)
    if case_count >= 8:
        cs_score = 1.0
    elif case_count >= 4:
        cs_score = 0.5
    elif case_count >= 2:
        cs_score = 0.25
    else:
        cs_score = 0
    result["case_examples"] = case_count

    # Boilerplate penalty — applied to expertise total
    boilerplate_count = _count_boilerplate_matches(body)
    bp_penalty = 0.0
    if boilerplate_count >= 5:
        bp_penalty = 1.5
    elif boilerplate_count >= 3:
        bp_penalty = 0.75
    elif boilerplate_count >= 1:
        bp_penalty = 0.25
    result["boilerplate_count"] = boilerplate_count

    expertise_raw = mt_score + ad_score + cs_score
    expertise_score = min(max(int(expertise_raw - bp_penalty + 0.5), 0), 4)
    result["scores"]["content_depth"] = expertise_score
    result["word_count"] = word_count
    # Legacy fields for backward compat
    result["domain_signals"] = _count_domain_signals(body)
    result["actionable_count"] = len(_ACTIONABLE_RE.findall(body))

    # ── Dimension 2: Structure Substance (0-1) ──
    # Reduced from 0-2 to 0-1 — compliance is baseline, not a discriminator.
    substantive = 0
    sections_found = 0
    for section_name, pattern in CORE_SECTIONS.items():
        section_words = _section_body_words(body, pattern)
        if section_words > 0:
            sections_found += 1
            if section_words >= 50:
                substantive += 1
            elif section_words >= 30:
                result["issues"].append(
                    f"thin section '{section_name}' ({section_words} words, borderline)"
                )
            else:
                result["issues"].append(
                    f"thin section '{section_name}' ({section_words} words, need ≥30)"
                )
        else:
            result["issues"].append(f"missing section: {section_name}")

    if substantive >= 5:
        sec_score = 1
    else:
        sec_score = 0

    result["scores"]["structure"] = sec_score
    result["sections_found"] = sections_found
    result["substantive_sections"] = substantive

    # ── Dimension 3: Frontmatter Richness (0-1) ──
    # Reduced from 0-2 to 0-1 — 99.9% of agents have complete metadata.
    fm_score = 0.0
    fm_checks = []

    description = get_field("description", fm_text)
    if description and len(description) >= 80:
        fm_score += 0.5
        fm_checks.append(f"description ({len(description)} chars)")
    elif description:
        fm_score += 0.25
        fm_checks.append(f"short description ({len(description)} chars)")
    else:
        fm_checks.append("missing description")

    if get_field("emoji", fm_text):
        fm_score += 0.25
    else:
        fm_checks.append("missing emoji")

    if get_field("color", fm_text):
        fm_score += 0.25
    else:
        fm_checks.append("missing color")

    bonus = 0.0
    if get_field("vibe", fm_text):
        bonus += 0.2
        fm_checks.append("has vibe")

    nexus_roles_text = get_field("nexus_roles", fm_text)
    if nexus_roles_text:
        bonus += 0.2
        fm_checks.append("has nexus_roles")

    if _has_cross_category_deps(filepath, fm_text):
        bonus += 0.2
        fm_checks.append("has cross-category depends_on")
    else:
        deps = get_list_field("depends_on", fm_text)
        if deps:
            fm_checks.append("depends_on (same-category only)")

    fm_score = min(round(fm_score + bonus), 1)
    result["scores"]["frontmatter"] = fm_score
    result["frontmatter_details"] = fm_checks
    result["risk_tier"] = risk_tier

    # ── Dimension 4: Content Originality (0-1) ──
    # Reduced from 0-2 to 0-1 — shifted weight to Content Expertise (0-4).
    orig_score = 1.0
    if boilerplate_count >= 5:
        orig_score = 0.0
    elif boilerplate_count >= 3:
        orig_score = 0.25
    elif boilerplate_count >= 1:
        orig_score = 0.5

    # Reward tool/methodology richness as a proxy for domain originality
    if tool_count >= 8:
        orig_score = min(orig_score + 0.25, 1.0)
    elif tool_count >= 4:
        orig_score = min(orig_score + 0.15, 1.0)

    originality = round(orig_score * 2) / 2  # round to nearest 0.5
    result["scores"]["originality"] = originality

    # ── Dimension 6: Professional Safeguards (0-1) ──
    # Disclaimers, scope boundaries, escalation guidance, human-in-the-loop.
    # Critical for high-risk categories (medical/legal/finance) but valuable everywhere.
    # Uses partial credit (0/0.5/1) to create score spread.
    safeguard_count = _count_safeguard_signals(body)
    if safeguard_count >= 3:
        safeguard_score = 1
    elif safeguard_count >= 1:
        safeguard_score = 0.5
    else:
        safeguard_score = 0
    result["scores"]["safeguards"] = safeguard_score
    result["safeguard_signals"] = safeguard_count

    # ── Dimension 7: Reference Density (0-1) ──
    # Citations, standards references, DOIs, authoritative sources.
    # Distinguishes research-backed expertise from opinion-based content.
    # Uses partial credit (0/0.5/1) to create score spread.
    reference_count = _count_reference_signals(body)
    if reference_count >= 3:
        reference_score = 1
    elif reference_count >= 1:
        reference_score = 0.5
    else:
        reference_score = 0
    result["scores"]["references"] = reference_score
    result["reference_signals"] = reference_count

    # ── Dimension 5: File Health (0-1) ──
    # Reduced from 0-2 to 0-1 — file health is a hygiene factor, not a quality signal.
    health_score = 0.0

    file_size_kb = len(content.encode("utf-8")) / 1024
    if 2 <= file_size_kb <= 15:
        health_score += 0.5
    elif 1 <= file_size_kb <= 70:
        health_score += 0.25
    else:
        result["issues"].append(f"file size out of range ({file_size_kb:.1f} KB)")

    result["file_size_kb"] = round(file_size_kb, 1)

    link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+\.md)\)")
    file_dir = filepath.parent
    broken_links = 0
    for m in link_pattern.finditer(body):
        url = m.group(2)
        if url.startswith("http://") or url.startswith("https://"):
            continue
        if url.startswith("/"):
            target = REPO / url.lstrip("/")
        else:
            target = (file_dir / url).resolve()
        if not target.exists():
            broken_links += 1

    if broken_links == 0:
        health_score += 0.25
    else:
        result["issues"].append(f"{broken_links} broken internal link(s)")

    if check_freshness:
        last_mod = git_last_modified(filepath)
        if last_mod:
            days_ago = (date.today() - last_mod).days
            if days_ago <= 180:
                health_score += 0.25
            elif days_ago <= 365:
                health_score += 0.15
            else:
                result["issues"].append(f"stale ({days_ago} days since last change)")
            result["last_modified"] = str(last_mod)
            result["days_since_modified"] = days_ago

    health_score = min(int(health_score * 2 + 0.5), 1)
    result["scores"]["file_health"] = health_score
    result["broken_links"] = broken_links

    # Risk-tiered minimum thresholds
    if risk_tier == "critical" and expertise_score < 3:
        result["issues"].append(
            f"CRITICAL-RISK category '{filepath.parent.name}' — content expertise too low "
            f"(scored {expertise_score}/4, needs ≥3 for domains where wrong advice could cause harm)"
        )

    # ── Total & Grade ──
    # Dimensions: expertise(4) + structure(1) + frontmatter(1) + originality(1)
    #            + file_health(1) + safeguards(1) + references(1) = 10
    total = (expertise_score + sec_score + fm_score + originality + health_score
             + safeguard_score + reference_score)
    # v3 thresholds: stricter A, wider spread
    if total >= 8:
        grade = "A"
    elif total >= 6:
        grade = "B"
    elif total >= 4:
        grade = "C"
    else:
        grade = "D"

    result["total"] = total
    result["grade"] = grade

    return result
