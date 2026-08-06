"""v7 scoring engine — Gate+Score architecture on 7 dimensions (0-18)."""

from pathlib import Path

from _shared import REPO, get_body, get_frontmatter_text

from scoring.engine import _sync_repo
from scoring.patterns import _METHODOLOGY_DEPTH_RE, _REFERENCE_RE, _TOOL_FRAMEWORK_RE
from scoring.signals import (
    _actionable_density,
    _check_cross_references,
    _compute_risk_tier,
    _count_boilerplate_matches,
    _count_case_examples,
    _count_collab_protocol_signals,
    _count_constraint_signals,
    _count_decision_model_signals,
    _count_domain_signals,
    _count_edge_case_signals,
    _count_methodology_depth_signals,
    _count_output_spec_signals,
    _count_reference_signals,
    _count_safeguard_signals,
)


def _compute_v7_grade(total, risk_tier):
    """Compute v7 letter grade with calibrated thresholds (0-18 scale).

    Thresholds calibrated against actual score distribution (mean ~10.9, range 9-13):
                   A        B        C        D
    critical      >=13     >=10.5   >=8.5    <=8.4
    high/general  >=12.5   >=10     >=8      <=7.9

    Note: gate failure is handled BEFORE this function is called.
    If gate fails, grade is D regardless of score.
    """
    if risk_tier == "critical":
        if total >= 13:
            return "A"
        if total >= 10.5:
            return "B"
        if total >= 8.5:
            return "C"
        return "D"
    else:
        if total >= 12.5:
            return "A"
        if total >= 10:
            return "B"
        if total >= 8:
            return "C"
        return "D"


def _generate_v7_improvement_plan(v7_scores, risk_tier):
    """Generate actionable improvement suggestions per low-scoring v7 dimension.

    Each entry: {"dim": str, "score": float, "max": float, "gap": float, "action": str}
    """
    dims = [
        ("content_depth", 6, "Add domain-specific tools/methodologies, case studies, "
         "and actionable directives in workflow sections"),
        ("references", 2, "Add inline standards references (ISO/IEC/NIST) in workflow "
         "context, cite authoritative sources with DOIs where applicable"),
        ("cross_refs", 2, "Add depends_on frontmatter linking to complementary agents; "
         "reference cross-category agents for cross-functional workflows"),
        ("method_decision_model", 3, "Add decision matrices, quantitative thresholds, "
         "multi-way branching logic, and scenario-anchored decision frameworks near tool refs. "
         "At minimum, add trade-off language explaining when/why to choose each approach"),
        ("constraint_awareness", 2, "Add explicit limitations section stating what the agent "
         "CANNOT do, its boundaries, and when to consult a real expert"),
        ("collab_protocol", 1.5, "Define what inputs are needed from other agents and what "
         "outputs this agent produces for downstream consumers"),
        ("edge_cases", 1.5, "Add domain-specific tricky scenarios, common pitfalls, "
         "and grey areas that require special handling"),
    ]
    plan = []
    for dim, max_val, action in dims:
        score = v7_scores.get(dim, 0)
        gap = max_val - score
        if gap > 0:
            plan.append({
                "dim": dim,
                "score": score,
                "max": max_val,
                "gap": gap,
                "action": action,
            })
    plan.sort(key=lambda x: -x["gap"])
    return plan


# ── v7 scoring engine ─────────────────────────────────────────────────────────

def score_agent_v7(filepath, check_freshness=True):
    """Score a single agent file using v7 dimensions (0-18 scale).

    Architecture: Gate + Score split.
      - Gate dimensions (safeguards, output_spec): must pass, otherwise grade capped at D
      - Score dimensions (7 total, 0-18):
        content_depth (0-6), references (0-2), cross_refs (0-2),
        method_decision_model (0-3), constraint_awareness (0-2),
        collab_protocol (0-1.5), edge_cases (0-1.5)

    Returns a dict with v7_scores, v7_total, v7_grade, v7_gate_passed,
    v7_gate_failures, and v7_improvement_plan.
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
        "v7_scores": {},
        "v7_total": 0,
        "v7_grade": "D",
        "v7_gate_passed": True,
        "v7_gate_failures": [],
        "v7_improvement_plan": [],
    }

    if not filepath.is_file():
        return result

    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return result

    fm_text = get_frontmatter_text(content)
    body = get_body(content)
    risk_tier = _compute_risk_tier(filepath.parent.name)

    # ── PHASE 1: Gate Checks ──────────────────────────────────────────────
    # Gate dimensions are NOT scored. They cap the grade to D if failed.
    gate_passed = True
    gate_failures = []

    safeguard_count = _count_safeguard_signals(body)
    if safeguard_count < 1:
        gate_passed = False
        gate_failures.append(
            "safeguards: no disclaimer, scope boundary, or escalation guidance detected"
        )

    output_spec_count = _count_output_spec_signals(body)
    if output_spec_count < 1:
        gate_passed = False
        gate_failures.append(
            "output_spec: no concrete deliverable format definition detected"
        )

    result["v7_gate_passed"] = gate_passed
    result["v7_gate_failures"] = gate_failures
    result["v7_safeguard_signals"] = safeguard_count
    result["v7_output_spec_signals"] = output_spec_count

    # ── PHASE 2: Score Dimensions ─────────────────────────────────────────
    # Scores are computed even if gate fails (for diagnostics / improvement plan)

    word_count = len(body.split())
    result["v7_word_count"] = word_count

    # Dimension 1: Content Expertise (0-6)
    tool_matches = list(_TOOL_FRAMEWORK_RE.finditer(body))
    tool_count = len({m.group(0).lower() for m in tool_matches})
    if tool_count >= 14:
        mt_score = 2.0
    elif tool_count >= 10:
        mt_score = 1.5
    elif tool_count >= 6:
        mt_score = 1.0
    elif tool_count >= 3:
        mt_score = 0.5
    elif tool_count >= 1:
        mt_score = 0.25
    else:
        mt_score = 0

    density = _actionable_density(body, word_count)
    if density >= 3.0:
        ad_score = 2.0
    elif density >= 2.0:
        ad_score = 1.5
    elif density >= 1.2:
        ad_score = 1.0
    elif density >= 0.6:
        ad_score = 0.5
    elif density >= 0.3:
        ad_score = 0.25
    else:
        ad_score = 0

    case_count = _count_case_examples(body)
    if case_count >= 8:
        cs_score = 1.0
    elif case_count >= 4:
        cs_score = 0.5
    elif case_count >= 2:
        cs_score = 0.25
    else:
        cs_score = 0

    domain_signal_count = _count_domain_signals(body)
    domain_density = domain_signal_count / max(word_count / 100, 1)
    if domain_density >= 3.0:
        ds_score = 1.0
    elif domain_density >= 1.5:
        ds_score = 0.5
    elif domain_density >= 0.5:
        ds_score = 0.25
    else:
        ds_score = 0

    boilerplate_count = _count_boilerplate_matches(body)
    bp_penalty = 0.0
    if boilerplate_count >= 5:
        bp_penalty = 1.5
    elif boilerplate_count >= 3:
        bp_penalty = 0.75
    elif boilerplate_count >= 1:
        bp_penalty = 0.25

    expertise_raw = mt_score + ad_score + cs_score + ds_score
    expertise_score = min(max(int(expertise_raw - bp_penalty + 0.5), 0), 6)
    result["v7_scores"]["content_depth"] = expertise_score

    # Dimension 2: Reference Density (0-2)
    reference_count = _count_reference_signals(body)
    result["v7_reference_signals"] = reference_count
    if reference_count >= 5:
        ref_count_score = 1
    elif reference_count >= 3:
        ref_count_score = 0.5
    elif reference_count >= 1:
        ref_count_score = 0.25
    else:
        ref_count_score = 0

    ref_quality_score = 0
    ref_matches = list(_REFERENCE_RE.finditer(body))
    if ref_matches:
        inline_count = 0
        for m in ref_matches:
            start = max(0, m.start() - 100)
            end = min(len(body), m.end() + 100)
            if _METHODOLOGY_DEPTH_RE.search(body[start:end]):
                inline_count += 1
        if inline_count >= 3:
            ref_quality_score = 1
        elif inline_count >= 1:
            ref_quality_score = 0.5

    reference_score = ref_count_score + ref_quality_score
    result["v7_scores"]["references"] = reference_score

    # Dimension 3: Cross-References (0-2)
    cross_ref_score = _check_cross_references(filepath, fm_text)
    result["v7_scores"]["cross_refs"] = cross_ref_score

    # Dimension 4: Method Decision Model (0-3) — expanded from v6's 0-1.5
    tool_positions = [(m.start(), m.end()) for m in tool_matches]

    # 4a. Trade-off depth (0-1.5) — absorbed from v6's method_tradeoff
    method_tradeoff_count = _count_methodology_depth_signals(body, tool_positions)
    if method_tradeoff_count >= 8:
        tradeoff_score = 1.5
    elif method_tradeoff_count >= 4:
        tradeoff_score = 1.0
    elif method_tradeoff_count >= 1:
        tradeoff_score = 0.5
    else:
        tradeoff_score = 0

    # 4b. Decision model depth (0-1.5) — same as v6
    decision_model_count = _count_decision_model_signals(body, tool_positions)
    if decision_model_count >= 6:
        dm_score = 1.5
    elif decision_model_count >= 3:
        dm_score = 1.0
    elif decision_model_count >= 1:
        dm_score = 0.5
    else:
        dm_score = 0

    method_decision_model_score = tradeoff_score + dm_score
    result["v7_scores"]["method_decision_model"] = method_decision_model_score
    result["v7_tradeoff_signals"] = method_tradeoff_count
    result["v7_decision_model_signals"] = decision_model_count

    # Dimension 5: Constraint Awareness (0-2) — NEW
    constraint_count = _count_constraint_signals(body)
    if constraint_count >= 5:
        constraint_score = 2
    elif constraint_count >= 3:
        constraint_score = 1
    elif constraint_count >= 1:
        constraint_score = 0.5
    else:
        constraint_score = 0
    result["v7_scores"]["constraint_awareness"] = constraint_score
    result["v7_constraint_signals"] = constraint_count

    # Dimension 6: Collaboration Protocol (0-1.5) — NEW
    collab_count = _count_collab_protocol_signals(body)
    if collab_count >= 4:
        collab_score = 1.5
    elif collab_count >= 2:
        collab_score = 1.0
    elif collab_count >= 1:
        collab_score = 0.5
    else:
        collab_score = 0
    result["v7_scores"]["collab_protocol"] = collab_score
    result["v7_collab_protocol_signals"] = collab_count

    # Dimension 7: Edge Cases (0-1.5) — NEW
    edge_count = _count_edge_case_signals(body)
    if edge_count >= 4:
        edge_score = 1.5
    elif edge_count >= 2:
        edge_score = 1.0
    elif edge_count >= 1:
        edge_score = 0.5
    else:
        edge_score = 0
    result["v7_scores"]["edge_cases"] = edge_score
    result["v7_edge_case_signals"] = edge_count

    # ── Total & Grade ──────────────────────────────────────────────────────
    v7_total = (expertise_score + reference_score + cross_ref_score
                + method_decision_model_score + constraint_score
                + collab_score + edge_score)

    # Gate failure overrides grade to D, regardless of score
    if not gate_passed:
        v7_grade = "D"
    else:
        v7_grade = _compute_v7_grade(v7_total, risk_tier)

    result["v7_total"] = v7_total
    result["v7_grade"] = v7_grade
    result["v7_risk_tier"] = risk_tier
    result["v7_improvement_plan"] = _generate_v7_improvement_plan(
        result["v7_scores"], risk_tier
    )

    return result
