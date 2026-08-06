"""Signal-counting helpers used by the scoring engine."""

import re

from _shared import discover_agents, get_list_field
from _shared.validators import CRITICAL_RISK_CATEGORIES, HIGH_RISK_CATEGORIES

from scoring.patterns import (
    _ACTIONABLE_RE,
    _CASE_SIGNALS_RE,
    _COLLAB_PROTOCOL_RE,
    _CONSTRAINT_RE,
    _DECISION_MODEL_RE,
    _DOMAIN_SIGNAL_RE,
    _EDGE_CASE_RE,
    _EXPANDED_BOILERPLATE_RE,
    _METHODOLOGY_DEPTH_RE,
    _OUTPUT_SPEC_RE,
    _REFERENCE_RE,
    _SAFEGUARD_RE,
    _TOOL_FRAMEWORK_RE,
)

# Agent ID cache for cross-reference validation (lazy populated)
_AGENT_ID_CACHE: set | None = None


def _get_agent_id_cache() -> set:
    """Lazily build a set of all valid agent IDs for cross-reference validation."""
    global _AGENT_ID_CACHE
    if _AGENT_ID_CACHE is None:
        _AGENT_ID_CACHE = set()
        for _cat, _rel, fp in discover_agents():
            _AGENT_ID_CACHE.add(fp.stem)
    return _AGENT_ID_CACHE


def _count_output_spec_signals(body):
    """Count concrete deliverable format definitions in agent body text."""
    return len({m.group(0)[:60].lower() for m in _OUTPUT_SPEC_RE.finditer(body)})


def _count_methodology_depth_signals(body, tool_positions):
    """Count how many tool references have contextual usage explanation nearby."""
    count = 0
    for t_start, t_end in tool_positions:
        start = max(0, t_start - 120)
        end = min(len(body), t_end + 120)
        surrounding = body[start:end]
        if _METHODOLOGY_DEPTH_RE.search(surrounding):
            count += 1
    return count


def _count_decision_model_signals(body, tool_positions):
    """Count tool references with structured decision model content nearby.

    Searches within 300 characters on either side of each tool reference for
    decision matrices, quantitative thresholds, multi-way branching, weighted
    criteria, scenario-anchored decisions, and named decision frameworks.
    """
    count = 0
    for t_start, t_end in tool_positions:
        start = max(0, t_start - 300)
        end = min(len(body), t_end + 300)
        surrounding = body[start:end]
        if _DECISION_MODEL_RE.search(surrounding):
            count += 1
    return count


def _count_constraint_signals(body):
    """Count unique constraint awareness signals in agent body text.

    Detects explicit "I cannot do X" statements, scope boundaries,
    and expert escalation guidance.
    """
    return len({m.group(0)[:80].lower() for m in _CONSTRAINT_RE.finditer(body)})


def _count_collab_protocol_signals(body):
    """Count unique collaboration protocol signals in agent body text.

    Detects input expectations from other agents, output specifications
    for downstream agents, and handoff interface descriptions.
    """
    return len({m.group(0)[:80].lower() for m in _COLLAB_PROTOCOL_RE.finditer(body)})


def _count_edge_case_signals(body):
    """Count unique edge case / pitfall signals in agent body text.

    Detects domain-specific tricky scenarios, common mistakes,
    failure modes, and grey areas.
    """
    return len({m.group(0)[:80].lower() for m in _EDGE_CASE_RE.finditer(body)})


def _check_cross_references(filepath, fm_text):
    """Score agent ecosystem linkage (0-2).

    0: no depends_on entries
    0.5: has 1-2 valid depends_on entries
    1: has 3+ valid depends_on entries
    1.5: has cross-category depends_on entries
    2: has 3+ cross-category depends_on entries
    """
    deps = get_list_field("depends_on", fm_text)
    if not deps:
        return 0
    valid_ids = _get_agent_id_cache()
    valid_deps = [d for d in deps if d in valid_ids]
    if not valid_deps:
        return 0
    own_cat = filepath.parent.name
    cross_cat = [d for d in valid_deps if not d.startswith(f"{own_cat}-")]
    if len(cross_cat) >= 3:
        return 2
    if cross_cat:
        return 1.5
    if len(valid_deps) >= 3:
        return 1
    return 0.5


def _count_safeguard_signals(body):
    """Count unique safeguard/disclaimer signals in agent body text."""
    return len({m.group(0)[:80].lower() for m in _SAFEGUARD_RE.finditer(body)})


def _count_reference_signals(body):
    """Count unique authoritative reference citations in agent body text."""
    return len({m.group(0)[:80].lower() for m in _REFERENCE_RE.finditer(body)})


def _count_boilerplate_matches(body):
    """Count boilerplate/template patterns in agent body text."""
    return len(_EXPANDED_BOILERPLATE_RE.findall(body))


def _count_case_examples(body):
    """Count concrete case studies, scenarios, and practical examples."""
    return len({m.group(0)[:60].lower() for m in _CASE_SIGNALS_RE.finditer(body)})


def _count_tool_references(body):
    """Count uniquely named methodologies, frameworks, and domain-specific tools."""
    return len({m.group(0).lower() for m in _TOOL_FRAMEWORK_RE.finditer(body)})


def _actionable_density(body, word_count):
    """Actionable directives per 100 words — normalizes for content length."""
    if word_count < 100:
        return 0.0
    directives = len(_ACTIONABLE_RE.findall(body))
    return min(directives / (word_count / 100), 10.0)  # cap at 10/100w


def _section_body_words(body, section_header_pattern):
    """Count words in the content following a section header match.

    Extracts text from the matched header position to the next header or EOF,
    then counts words. Returns 0 if the header isn't found.

    Anchors the pattern to ## headers to avoid false matches on keywords
    appearing in body text of other sections.
    """
    anchored = rf"^##[^#\n]*?(?:{section_header_pattern})"
    m = re.search(anchored, body, re.IGNORECASE | re.MULTILINE)
    if not m:
        return 0
    start = m.end()
    # Find next markdown header (only # and ##; ### subsections are part of parent)
    next_header = re.search(r"^#{1,2}\s", body[start:], re.MULTILINE)
    end = start + next_header.start() if next_header else len(body)
    return len(body[start:end].split())


def _count_domain_signals(body):
    """Count unique domain-specific references in the body text."""
    return len({m.group(0).lower() for m in _DOMAIN_SIGNAL_RE.finditer(body)})


def _count_actionable_directives(body):
    """Count actionable directives (bullets, imperatives, workflow steps)."""
    return len(_ACTIONABLE_RE.findall(body))


def _compute_risk_tier(category):
    """Determine the risk tier for a category."""
    if category in CRITICAL_RISK_CATEGORIES:
        return "critical"
    if category in HIGH_RISK_CATEGORIES:
        return "high"
    return "general"


def _has_cross_category_deps(filepath, fm_text):
    """Check if depends_on references any agent outside the current category."""
    deps = get_list_field("depends_on", fm_text)
    if not deps:
        return False
    own_cat = filepath.parent.name
    for dep_id in deps:
        # If the dependency id doesn't start with the own category prefix, it's cross-category
        if not dep_id.startswith(f"{own_cat}-"):
            return True
    return False
