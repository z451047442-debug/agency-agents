#!/usr/bin/env python
"""Build self-updating ARCHITECTURE.md and ARCHITECTURE.html from live project data.

Usage:
    python scripts/build-architecture.py              # generate both files
    python scripts/build-architecture.py --check      # CI mode: verify files are up to date
    python scripts/build-architecture.py --out-md <path> --out-html <path>
"""

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

UTC = timezone.utc

REPO = Path(__file__).resolve().parent.parent

# ==========================================================================
# Data Collection
# ==========================================================================


def get_version() -> str:
    """Return version from pyproject.toml (e.g. 'v2.1.3')."""
    try:
        text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip().startswith("version"):
                ver = line.split("=", 1)[1].strip().strip('"')
                return f"v{ver}"
    except (OSError, subprocess.CalledProcessError):
        pass
    return "v0.0.0"


def get_python_req() -> str:
    """Return requires-python from pyproject.toml."""
    try:
        text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip().startswith("requires-python"):
                return line.split("=", 1)[1].strip().strip('"')
    except (OSError, subprocess.CalledProcessError):
        pass
    return ">=3.10"


def get_coverage_threshold() -> str:
    """Return coverage threshold from pyproject.toml."""
    try:
        text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
        for line in text.splitlines():
            if "cov-fail-under" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except (OSError, subprocess.CalledProcessError):
        pass
    return "90"


def collect_ci_workflows() -> list[dict]:
    """Return list of CI workflow info dicts."""
    desc = {
        "ci.yml": ("CI", "push/PR to main", "lint -> test -> validate -> score-gate"),
        "lint-agents.yml": ("Lint Agent Files", "on *.md change", "YAML + structure validation"),
        "quality-gate.yml": ("Quality Gate", "push/PR", "score >= 5 threshold"),
        "release.yml": ("Release", "tag push", "version + changelog"),
        "nightly-full-audit.yml": ("Nightly Full Audit", "cron daily", "full pipeline audit"),
        "check-divisions.yml": ("Check Divisions", "push/PR", "validate division structure"),
        "check-tools.yml": ("Check Tools", "push/PR", "verify integrations sync"),
    }
    workflows = []
    for yml in sorted((REPO / ".github" / "workflows").glob("*.yml")):
        name = yml.name
        if name in desc:
            wf_name, trigger, actions = desc[name]
            workflows.append({"file": name, "name": wf_name, "trigger": trigger, "actions": actions})
    return workflows


def collect_test_modules() -> tuple[list[dict], int]:
    """Run pytest --collect-only and return per-module test counts and total.

    Handles two output formats:
    - Standard:  tests/test_file.py::TestClass::test_func
    - Tree/XML:  <Module test_file.py> ... <Function test_func>
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q", "--no-header"],
            capture_output=True, text=True, cwd=REPO,
        )
        output = result.stdout + result.stderr
    except (OSError, subprocess.CalledProcessError):
        output = ""

    modules: dict[str, int] = {}
    total = 0

    # Format 1: standard "::" separators
    for line in output.splitlines():
        line = line.strip()
        if "test_" in line and "::" in line and ".py" in line:
            mod = line.split(".py")[0].split("/")[-1].split("\\")[-1]
            if mod.startswith("test_"):
                modules[mod] = modules.get(mod, 0) + 1
                total += 1

    # Format 2: tree format with <Module> / <Function> tags
    if not modules:
        current_module = ""
        for line in output.splitlines():
            line = line.strip()
            if "<Module " in line:
                current_module = line.split("<Module ")[1].split(">")[0].strip()
            elif "<Function test_" in line and current_module:
                modules[current_module] = modules.get(current_module, 0) + 1
                total += 1

    if not modules:
        # Fallback: count test files without running pytest
        for f in sorted((REPO / "tests").glob("test_*.py")):
            modules[f.name] = 0
            total = 0  # "n/a" sentinel replaced with 0 so output reads cleanly

    return [{"module": k, "count": v} for k, v in sorted(modules.items(), key=lambda x: -x[1])], total


def collect_category_counts() -> list[dict]:
    """Read AGENTS.json and return sorted category distribution."""
    with open(REPO / "AGENTS.json", encoding="utf-8") as f:
        index = json.load(f)
    agents = index["agents"]
    counter: Counter[str] = Counter(a["category"] for a in agents)
    return [{"category": cat, "count": cnt} for cat, cnt in counter.most_common()]


def collect_script_categories() -> dict:
    """Return categorized scripts with descriptions."""
    SCRIPT_MAP: dict[str, tuple[str, str]] = {
        # Quality Pipeline
        "lint-agents.py": ("quality", "YAML validation, section checks, CRLF detection, security scanning"),
        "score-agents.py": ("quality", "A-D grading with risk tiers, domain signals, and score variance"),
        "analyze-deps.py": ("quality", "depends_on validation + cross-category coverage + --apply"),
        "feedback.py": ("discovery", "User feedback collection — ratings, comments, issue reports"),
        "analyze-deps-auto.py": ("quality", "NLP-based auto dependency mapping from agent content"),
        "quality-report.py": ("quality", "Unified dashboard + risk tiers + feedback integration"),
        "quality.py": ("quality", "Quality pipeline orchestration entry point"),
        "validate-index.py": ("quality", "AGENTS.json JSON schema + filesystem cross-reference validation"),
        "check-agent-originality.py": ("quality", "Agent originality and similarity detection"),
        "check-divisions.py": ("quality", "Division directory structure validation"),
        "check-dupes.py": ("quality", "Duplicate detection via semantic similarity"),
        # Maintenance Tools
        "agent-lifecycle.py": ("maintenance", "draft -> review -> published -> deprecated lifecycle"),
        "contribute.py": ("maintenance", "Contribution dashboard with skill-level filtering"),
        "expand-agent.py": ("maintenance", "B-grade to A-grade content expansion with template engine"),
        "add-comm-section.py": ("maintenance", "Communication Style section generator with domain traits"),
        "batch-add-deps.py": ("maintenance", "Bulk depends_on frontmatter field manipulation"),
        "batch-nexus-roles.py": ("maintenance", "Bulk nexus_roles field assignment"),
        "batch-date-added.py": ("maintenance", "Bulk date_added field population"),
        "batch-version.py": ("maintenance", "Bulk version field population"),
        "clean.py": ("maintenance", "Project cleanup: __pycache__, build artifacts"),
        "rebalance-nexus-phases.py": ("maintenance", "Rebalance agent distribution across NEXUS phases"),
        "suggest-nexus-roles.py": ("maintenance", "Auto-suggest NEXUS roles based on agent content"),
        # Integration Tools
        "convert.py": ("integration", ".md to 9 target tool formats, with parallel mode"),
        "build-hermes-plugin.py": ("integration", "Hermes IDE plugin packaging and bundling"),
        "generate-index.py": ("integration", "AGENTS.json index generator with --check CI mode"),
        "shard-index.py": ("integration", "AGENTS.json splitter for parallel processing"),
        # Discovery / Orchestration
        "search-agents.py": ("discovery", "Keyword, category, and regex search with paginated results"),
        "nexus-orchestrator.py": ("discovery", "NEXUS multi-agent orchestration engine"),
        "build-agent-browser.py": ("discovery", "Self-contained agent browser HTML generator"),
        "build-architecture.py": ("discovery", "ARCHITECTURE.md / .html auto-generator from live project data"),
    }

    cats: dict[str, list[dict]] = {"quality": [], "maintenance": [], "integration": [], "discovery": []}
    for py_file in sorted(REPO.glob("scripts/*.py")):
        if py_file.parent != REPO / "scripts":
            continue
        name = py_file.name
        if name in SCRIPT_MAP:
            cat, desc = SCRIPT_MAP[name]
            cats[cat].append({"name": name, "desc": desc})

    # i18n scripts in subdirectory
    cats["discovery"].append({"name": "i18n/check-i18n.py", "desc": "Translation coverage tracking and template generation"})
    cats["discovery"].append({"name": "i18n/localize-agents.py", "desc": "Name + description patching from JSON translation maps"})

    sh_count = len(list(REPO.glob("scripts/*.sh")))
    py_count = sum(len(v) for v in cats.values())

    return {"categories": cats, "py_total": py_count, "sh_total": sh_count}


def collect_shared_library() -> dict:
    """Inspect _shared module and count consumers."""
    modules = [
        {"name": "discovery.py", "exports": "REPO, EXCLUDE_DIRS, discover_agents()", "desc": "Agent file discovery engine"},
        {"name": "frontmatter.py", "exports": "get_body(), get_field(), get_frontmatter_text(), get_list_field()", "desc": "YAML frontmatter parsing utilities"},
        {"name": "terminal.py", "exports": "BOLD, CYAN, GREEN, RED, RESET, YELLOW, supports_color()", "desc": "ANSI terminal color constants + TTY detection"},
        {"name": "__init__.py", "exports": "Re-exports all 15 symbols + load_module()", "desc": "Module entry point and dynamic loader"},
    ]

    consumers: list[str] = []
    for py_file in sorted(REPO.glob("scripts/**/*.py")):
        if "_shared" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            text = py_file.read_text(encoding="utf-8")
            if "from _shared import" in text or "from _shared" in text or "load_module(" in text:
                name = py_file.stem
                if name not in consumers:
                    consumers.append(name)
        except (OSError, subprocess.CalledProcessError):
            pass

    return {"modules": modules, "consumers": consumers, "exports_count": 16}


def collect_integration_targets() -> list[dict]:
    """Parse convert.py and return integration target list."""
    targets = [{"tool": "Claude Code", "format": ".md", "converter": "direct (no conversion)"}]
    try:
        text = (REPO / "scripts" / "convert.py").read_text(encoding="utf-8")
        tool_map = {
            "convert_cursor": ("Cursor", ".mdc"),
            "convert_copilot": ("Copilot", ".md"),
            "convert_gemini_cli": ("Gemini CLI", ".gm.md"),
            "convert_windsurf": ("Windsurf", ".windsurf"),
            "convert_codex": ("Codex", ".txt"),
            "convert_kimi": ("Kimi", ".kimi.md"),
            "convert_antigravity": ("Antigravity", ".ag.md"),
        }
        for func, (tool, fmt) in tool_map.items():
            if func in text:
                targets.append({"tool": tool, "format": fmt, "converter": f"{func}()"})
    except (OSError, subprocess.CalledProcessError):
        pass
    return targets


def collect_nexus_phases() -> list[str]:
    """Extract unique NEXUS phases from AGENTS.json agents."""
    with open(REPO / "AGENTS.json", encoding="utf-8") as f:
        index = json.load(f)
    phases: set[str] = set()
    for agent in index["agents"]:
        for role in agent.get("nexus_roles", []):
            if role.startswith("phase-"):
                phases.add(role)
    return sorted(phases)


def load_index() -> dict[str, Any]:
    with open(REPO / "AGENTS.json", encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


def collect_architecture_data() -> dict:
    """Master data collection - single source of truth for both renderers."""
    index = load_index()
    test_modules, total_tests = collect_test_modules()
    cat_counts = collect_category_counts()
    script_data = collect_script_categories()
    shared = collect_shared_library()
    ci_wfs = collect_ci_workflows()
    targets = collect_integration_targets()
    phases = collect_nexus_phases()

    return {
        "version": get_version(),
        "python_req": get_python_req(),
        "coverage_threshold": get_coverage_threshold(),
        "generated": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "total_agents": index["total_agents"],
        "total_categories": index["total_categories"],
        "category_counts": cat_counts,
        "total_tests": total_tests,
        "test_modules": test_modules,
        "test_modules_count": len(test_modules),
        "script_categories": script_data,
        "shared": shared,
        "ci_workflows": ci_wfs,
        "ci_workflows_count": len(ci_wfs),
        "integration_targets": targets,
        "integration_targets_count": len(targets),
        "nexus_phases": phases,
        "nexus_phases_count": len(phases),
    }


# ==========================================================================
# MD Rendering
# ==========================================================================


def _fmt_table(headers: list[str], rows: list[list[str]]) -> str:
    """Build a Markdown table."""
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join("-" * (len(h) + 2) for h in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def format_md_ci_table(workflows: list[dict]) -> str:
    rows = [[w["name"], w["trigger"], w["actions"]] for w in workflows]
    return _fmt_table(["Workflow", "Trigger", "Actions"], rows)


def format_md_test_table(test_modules: list[dict]) -> str:
    half = (len(test_modules) + 1) // 2
    left = test_modules[:half]
    right = test_modules[half:]
    rows = []
    for i in range(half):
        l_val = f"{left[i]['module']} ({left[i]['count']})" if i < len(left) else ""
        r_val = f"{right[i]['module']} ({right[i]['count']})" if i < len(right) else ""
        rows.append([l_val, r_val])
    return _fmt_table(["Module (tests)", "Module (tests)"], rows)


def format_md_shared(shared: dict) -> str:
    lines = [f"**{shared['exports_count']} public API symbols** across 4 modules", ""]
    for m in shared["modules"]:
        lines.append(f"**{m['name']}** — {m['desc']}")
        lines.append(f"- Exports: `{m['exports']}`")
        lines.append("")
    lines.append(f"**{len(shared['consumers'])} consumers**: " + " · ".join(shared["consumers"]))
    return "\n".join(lines)


def format_md_scripts(script_data: dict) -> str:
    lines = []
    labels = {
        "quality": "Quality Pipeline",
        "maintenance": "Maintenance Tools",
        "integration": "Integration Tools",
        "discovery": "Discovery & Orchestration",
    }
    for cat_key in ["quality", "maintenance", "integration", "discovery"]:
        items = script_data["categories"].get(cat_key, [])
        lines.append(f"### {labels[cat_key]} ({len(items)} scripts)")
        rows = [[s["name"], s["desc"]] for s in items]
        lines.append(_fmt_table(["Script", "Purpose"], rows))
        lines.append("")
    lines.append(f"Plus {script_data['sh_total']} shell wrappers (thin entry points delegating to .py counterparts).")
    return "\n".join(lines)


def format_md_categories(cat_counts: list[dict]) -> str:
    """Return a full table of ALL categories with Chinese labels."""
    rows = [[ZH_LABELS.get(c["category"], c["category"]), c["category"], str(c["count"])] for c in cat_counts]
    return _fmt_table(["中文", "English", "Agents"], rows)


def format_md_integration(targets: list[dict]) -> str:
    rows = [[t["tool"], t["format"], t["converter"]] for t in targets]
    return _fmt_table(["Tool", "Format", "Converter"], rows)


def render_markdown(data: dict) -> str:
    sc = data["script_categories"]
    return f"""# The Agency — System Architecture {data['version']}

**{data['total_agents']:,} AI Agent Personality Definitions · {data['total_categories']} Categories · {sc['py_total']} Tooling Scripts · {data['total_tests']:,} Tests**

Generated: {data['generated']}

---

## Layer 0: CI/CD Pipeline ({data['ci_workflows_count']} workflows)

{format_md_ci_table(data['ci_workflows'])}

---

## Layer 1: Test Suite ({data['test_modules_count']} modules, {data['total_tests']:,} tests)

{format_md_test_table(data['test_modules'])}

---

## Layer 2: Shared Library (scripts/_shared/)

{format_md_shared(data['shared'])}

---

## Layer 3: Tooling Scripts ({sc['py_total']} Python modules + {sc['sh_total']} shell wrappers)

{format_md_scripts(sc)}

---

## Layer 4: Agent Content ({data['total_agents']:,} .md files, {data['total_categories']} categories)

### Category Distribution (all {data['total_categories']})

{format_md_categories(data['category_counts'])}

### Special Directories

- `_solution/` — meta-agents for multi-agent team coordination
- `libraries/` — cross-industry infrastructure (archivists, librarians)
- `specialized/` — cross-cutting roles (CFO, CSM, DPO, ESG officer, grant writer)
- `strategy/` — strategy consulting (CEO coach, VC advisory, ESG)
- `docs/` — NEXUS orchestration (playbooks, runbooks, coordination)

### Agent File Anatomy

```yaml
---
name: "Agent Display Name"     # required (1-120 chars)
description: "One-sentence..." # required (10-500 chars)
emoji: "\U0001f3af"             # required (1-8 chars)
color: cyan                    # required (named or #RRGGBB)

version: "1.0.0"              # standard (auto-populated)
date_added: "2026-07-03"      # standard (auto-populated)

vibe: "personality primer"    # optional
nexus_roles:                  # optional (NEXUS pipeline phases)
  - phase-0-discovery
depends_on:                   # optional (agent IDs this agent needs)
  - engineering-backend-architect
---

## Identity & Memory          <-- required
## Core Mission               <-- required
## Critical Rules             <-- required
[deliverables, workflow,      <-- recommended
 metrics, communication]
```

---

## Layer 5: Integration Targets ({data['integration_targets_count']} tools)

{format_md_integration(data['integration_targets'])}

---

## Layer 6: Data Flow & Module Dependency

### Shared Foundation

All {data['script_categories']['py_total']} Python scripts read agent data through `_shared/` — none call each other's output:

```
                      _shared/
          (discovery, frontmatter, terminal)
         /     /    |     |    \\        \\\\
        /     /     |     |     \\        \\\\
   lint    score  analyze convert  search  validate
 agents  agents  -deps   .py     agents  -index
   .py     .py    .py             .py     .py
    |       |      |               |
    v       v      v               v
  errors  grades  broken       paginated
                  refs          results
```

### Quality Pipeline (orchestrated by quality.py)

```
quality.py
  ├── lint-agents.py       → 0 errors, 2 warnings
  ├── score-agents.py      → 100% A grade
  ├── analyze-deps.py      → 0 broken references
  ├── ruff check           → clean
  └── pytest --cov         → 93%+ coverage
```

### Key Consumers (grouped by role)

| Role | Script |
|------|--------|
| **Quality Gate** | `lint-agents.py`, `score-agents.py`, `analyze-deps.py`, `quality-report.py`, `validate-index.py` |
| **Maintenance** | `agent-lifecycle.py`, `contribute.py`, `expand-agent.py`, `add-comm-section.py` |
| **Integration** | `convert.py`, `generate-index.py`, `build-agent-browser.py`, `build-architecture.py` |
| **Discovery** | `search-agents.py`, `i18n/check-i18n.py`, `i18n/localize-agents.py` |

All 16 consumers depend on `_shared/` modules; cross-script imports use `load_module()` for hyphenated filenames.

---

## Layer 7: NEXUS Multi-Agent Orchestration

{' -> '.join(p.replace('phase-', 'Phase ').replace('-', ': ').title() for p in data['nexus_phases'])}

**{data['nexus_phases_count']} phases** with {data['total_agents']:,} agents distributed across them (agents opt in via `nexus_roles` frontmatter field).

Resources: `docs/nexus-strategy.md` | `docs/nexus-cycle.md` | `docs/playbooks/` | `docs/runbooks/` | `docs/teams/` | `docs/coordination/`

---

## Project Health

| Metric | Value |
|--------|-------|
| Version | {data['version']} |
| Python | {data['python_req']} |
| Coverage threshold | {data['coverage_threshold']}% |
| Agent files | {data['total_agents']:,} |
| Tool scripts | {sc['py_total']} (.py) + {sc['sh_total']} (.sh) |
| Tests | {data['total_tests']:,} across {data['test_modules_count']} modules |
| CI workflows | {data['ci_workflows_count']} |
| Integration targets | {data['integration_targets_count']} |
| NEXUS phases | {data['nexus_phases_count']} |

Generated: {data['generated']}
"""


# ==========================================================================
# HTML Rendering
# ==========================================================================

ZH_LABELS: dict[str, str] = {
    "_solution": "解决方案",
    "administration": "行政管理",
    "aerospace": "航空航天",
    "agriculture": "农业",
    "automotive": "汽车",
    "beauty": "美妆",
    "construction": "建筑工程",
    "customer-service": "客户服务",
    "cybersecurity": "网络安全",
    "data-science": "数据科学",
    "design": "设计",
    "education": "教育",
    "emergency": "应急管理",
    "energy": "能源",
    "engineering": "工程开发",
    "environmental": "环境",
    "events": "活动会展",
    "fashion": "时尚",
    "finance": "金融",
    "food-beverage": "食品饮料",
    "forestry": "林业",
    "game-development": "游戏开发",
    "gis": "地理信息",
    "government": "政府",
    "healthcare": "医疗健康",
    "home-lifestyle": "家居生活",
    "hr": "人力资源",
    "hr-tech": "HR科技",
    "infrastructure": "基础设施",
    "insurance": "保险",
    "iot": "物联网",
    "legal": "法律",
    "libraries": "图书馆",
    "localization": "本地化",
    "logistics": "物流",
    "lottery": "彩票",
    "manufacturing": "制造业",
    "marketing": "市场营销",
    "media-entertainment": "媒体娱乐",
    "mining": "矿业",
    "museums": "博物馆",
    "network-engineering": "网络工程",
    "nonprofit": "公益",
    "operations": "运营",
    "parenting-family": "亲子家庭",
    "pets": "宠物",
    "pharma-biotech": "医药生物",
    "product": "产品",
    "project-management": "项目管理",
    "publishing": "出版",
    "quality": "质量管理",
    "real-estate": "房地产",
    "retail": "零售",
    "robotics": "机器人",
    "sales": "销售",
    "securities": "证券",
    "security": "安全",
    "spatial-computing": "空间计算",
    "specialized": "专业角色",
    "sports": "体育",
    "strategy": "战略咨询",
    "telecom": "电信",
    "testing": "测试",
    "thinking-models": "思维模型",
    "tourism": "旅游",
    "web3": "Web3",
}


def format_html_ci_cards(workflows: list[dict]) -> str:
    cards = []
    for i, w in enumerate(workflows):
        alt = "b" if i % 2 else "a"
        cards.append(
            f'<div class="card ci-card {alt}">'
            f'<div class="n">{w["name"]}</div>'
            f'<div class="d">{w["trigger"]}: {w["actions"]}</div>'
            f'</div>'
        )
    return "\n".join(cards)


def format_html_test_cards(test_modules: list[dict]) -> str:
    top = test_modules[:8]
    rest_count = sum(m["count"] for m in test_modules[8:]) if len(test_modules) > 8 else 0
    rest_modules = len(test_modules) - 8
    cards = []
    for m in top:
        name = m["module"].replace("test_", "").replace(".py", "").replace("_", " ")
        cards.append(f'<div class="card tc"><div class="nm">{name}</div><div class="ct">{m["count"]}</div></div>')
    if rest_count > 0:
        cards.append(f'<div class="card tc"><div class="nm">+ {rest_modules} modules</div><div class="ct">{rest_count}</div></div>')
    return "\n".join(cards)


def format_html_shared_modules(shared: dict) -> str:
    cards = []
    colors = {
        "discovery.py": ("#0891b2", "#ecfeff"),
        "frontmatter.py": ("#7c3aed", "#f5f3ff"),
        "terminal.py": ("#d97706", "#fffbeb"),
        "__init__.py": ("#059669", "#ecfdf5"),
    }
    for m in shared["modules"]:
        c, bg = colors.get(m["name"], ("#6366f1", "#eef2ff"))
        cards.append(
            f'<div class="card sh">'
            f'<div class="mt" style="color:{c}">{m["name"]} — {m["desc"]}</div>'
            f'<div class="md">{m["exports"]}</div>'
            f'</div>'
        )
    return "\n".join(cards)


def format_html_script_grid(script_data: dict) -> str:
    labels = {
        "quality": ("质量流水线", "#10b981", "#ecfdf5"),
        "maintenance": ("维护工具", "#f59e0b", "#fffbeb"),
        "integration": ("集成工具", "#8b5cf6", "#f5f3ff"),
        "discovery": ("发现与编排", "#06b6d4", "#ecfeff"),
    }
    panels = []
    for cat_key, (zh_name, border_color, bg_color) in labels.items():
        items = script_data["categories"].get(cat_key, [])
        tiles = []
        for s in items:
            name = s["name"].replace(".py", "")
            tiles.append(
                f'<div class="ti"><div class="tn" style="color:{border_color}">{name}</div>'
                f'<div class="td">{s["desc"]}</div></div>'
            )
        panels.append(
            f'<div class="col"><div class="tg" style="background:{bg_color};border:1.5px solid {border_color}">'
            f'<div style="font-weight:bold;color:{border_color};font-size:13px">{zh_name}</div>'
            f'<div class="tl">{"".join(tiles)}</div>'
            f'</div></div>'
        )
    top_row = f'<div class="cols">{"".join(panels[:2])}</div>'
    bot_row = f'<div class="cols" style="margin-top:16px">{"".join(panels[2:])}</div>'
    return top_row + bot_row


def format_html_category_bars(cat_counts: list[dict], total_agents: int) -> str:
    """Build category visualization — cbox cards for top 12 + scrollable full table below."""
    top12 = cat_counts[:12]

    # cbox cards (top 12)
    cboxes = []
    for c in top12:
        label = ZH_LABELS.get(c["category"], c["category"])
        cboxes.append(f'<div class="cbox"><div class="cn">{label}</div><div class="cc">{c["count"]}</div></div>')

    # Full category table (all 65)
    rows_html = ""
    for i, c in enumerate(cat_counts):
        label = ZH_LABELS.get(c["category"], c["category"])
        pct = c["count"] / total_agents * 100
        rows_html += (
            f'<tr><td style="padding:2px 8px;font-size:11px">{i + 1}</td>'
            f'<td style="padding:2px 8px;font-size:11px">{label}</td>'
            f'<td style="padding:2px 8px;font-size:11px">{c["category"]}</td>'
            f'<td style="padding:2px 8px;font-size:11px;text-align:right">{c["count"]}</td>'
            f'<td style="padding:2px 8px;font-size:11px;text-align:right">{pct:.1f}%</td></tr>'
        )
    table_html = (
        f'<div style="margin-top:16px;max-height:400px;overflow-y:auto;background:#fff;border-radius:8px;padding:8px">'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<tr style="border-bottom:2px solid #ddd">'
        f'<th style="padding:4px 8px;font-size:11px;text-align:left">#</th>'
        f'<th style="padding:4px 8px;font-size:11px;text-align:left">中文</th>'
        f'<th style="padding:4px 8px;font-size:11px;text-align:left">English</th>'
        f'<th style="padding:4px 8px;font-size:11px;text-align:right">Agents</th>'
        f'<th style="padding:4px 8px;font-size:11px;text-align:right">%</th></tr>'
        f'{rows_html}</table></div>'
    )

    return f"""<div class="crow">{"".join(cboxes)}</div>
<div class="st">共 {len(cat_counts)} 个行业分类，{total_agents} 个 Agent</div>
{table_html}"""


def format_html_integration_cards(targets: list[dict]) -> str:
    cards = []
    for t in targets:
        cards.append(
            f'<div class="card" style="border-top:3px solid #7c3aed">'
            f'<div class="t">{t["tool"]}</div>'
            f'<div class="d">{t["format"]}<br>{t["converter"]}</div>'
            f'</div>'
        )
    return "\n".join(cards)


def format_html_nexus(phases: list[str]) -> str:
    """Render NEXUS phase pipeline with agent counts from AGENTS.json."""
    import json as _json
    with open(REPO / "AGENTS.json", encoding="utf-8") as _f:
        _index = _json.load(_f)
    phase_counts: dict[str, int] = {}
    for agent in _index["agents"]:
        for role in agent.get("nexus_roles", []):
            if role.startswith("phase-"):
                phase_counts[role] = phase_counts.get(role, 0) + 1

    cards = []
    for p in phases:
        num = p.replace("phase-", "").split("-")[0]
        name = p.replace("phase-", "").replace("-", " ").title()
        count = phase_counts.get(p, 0)
        cards.append(
            f'<div class="card" style="border-top:3px solid #22c55e;text-align:center;min-width:120px">'
            f'<div style="font-size:20px;font-weight:bold;color:#22c55e">P{num}</div>'
            f'<div style="font-size:12px;font-weight:bold;color:#fff">{name}</div>'
            f'<div style="font-size:11px;color:#888">{count} agents</div>'
            f'</div>'
        )
    return f'<div class="grid" style="grid-template-columns:repeat({len(phases)},1fr)">{"".join(cards)}</div>'


def format_html_footer_stats(data: dict) -> str:
    sc = data["script_categories"]
    return (
        f"Agent: {data['total_agents']:,} | 分类: {data['total_categories']} | "
        f"脚本: {sc['py_total']} (.py) + {sc['sh_total']} (.sh) | "
        f"测试: {data['total_tests']:,} | CI: {data['ci_workflows_count']} 工作流 | "
        f"目标: {data['integration_targets_count']} 工具 | "
        f"覆盖率阈值: {data['coverage_threshold']}% | Python: {data['python_req']}"
    )


def render_html(data: dict) -> str:
    sc = data["script_categories"]

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=1600">
<title>The Agency - System Architecture {data['version']}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:"Microsoft YaHei","PingFang SC",sans-serif;background:#1a1a2e;color:#e0e0e0;min-width:1400px}}
.header{{background:linear-gradient(135deg,#1a1a2e,#16213e);padding:30px 60px;text-align:center;border-bottom:2px solid #333}}
.header h1{{font-size:28px;margin-bottom:8px}}.header p{{color:#888;font-size:14px}}
.container{{max-width:1600px;margin:0 auto;padding:20px 40px}}
.layer{{border-radius:12px;margin-bottom:24px;overflow:hidden}}
.layer-h{{padding:14px 28px;font-size:15px;font-weight:bold;color:#fff}}
.layer-b{{padding:20px 28px}}
.l0 .layer-h{{background:linear-gradient(135deg,#667eea,#764ba2)}}.l0 .layer-b{{background:#f0edff;color:#333}}
.l1 .layer-h{{background:linear-gradient(135deg,#f093fb,#f5576c)}}.l1 .layer-b{{background:#fff0f3;color:#333}}
.l2 .layer-h{{background:linear-gradient(135deg,#4facfe,#00f2fe)}}.l2 .layer-b{{background:#f0f8ff;color:#333}}
.l3 .layer-h{{background:linear-gradient(135deg,#43e97b,#38f9d7)}}.l3 .layer-b{{background:#f0fff4;color:#333}}
.l4 .layer-h{{background:linear-gradient(135deg,#fa709a,#fee140)}}.l4 .layer-b{{background:#fff5f5;color:#333}}
.l5 .layer-h{{background:linear-gradient(135deg,#a18cd1,#fbc2eb)}}.l5 .layer-b{{background:#faf5ff;color:#333}}
.l6 .layer-h{{background:linear-gradient(135deg,#475569,#64748b)}}.l6 .layer-b{{background:#f8fafc;color:#333}}
.l7 .layer-h{{background:linear-gradient(135deg,#374151,#4b5563)}}.l7 .layer-b{{background:#fafafa;color:#333}}
.grid{{display:flex;flex-wrap:wrap;gap:12px}}
.card{{background:#fff;border-radius:8px;padding:14px 16px;box-shadow:0 2px 8px rgba(0,0,0,.06);min-width:150px;text-align:center}}
.card .t{{font-weight:bold;margin-bottom:4px}}
.card .d{{font-size:12px;color:#666}}
.ci-card{{border-left:3px solid}}.ci-card.a{{border-color:#667eea}}.ci-card.b{{border-color:#764ba2}}
.ci-card .n{{font-weight:bold;font-size:13px;color:#667eea}}.ci-card.b .n{{color:#764ba2}}
.tc{{text-align:center}}.tc .nm{{font-size:12px;color:#555}}.tc .ct{{font-size:18px;font-weight:bold;color:#f5576c}}
.sh{{border:1.5px solid #4facfe;text-align:left;flex:1;min-width:260px}}
.sh .mt{{font-weight:bold;font-size:13px;margin-bottom:6px}}
.sh .md{{font-size:11px;color:#555;line-height:1.6}}
.tg{{border-radius:10px;padding:16px;flex:1;min-width:450px}}
.tl{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}}
.ti{{background:#fff;border-radius:6px;padding:8px 12px;box-shadow:0 1px 4px rgba(0,0,0,.04)}}
.ti .tn{{font-size:11px;font-weight:bold;margin-bottom:2px}}.ti .td{{font-size:10px;color:#666}}
.crow{{display:flex;gap:10px;margin-bottom:10px;flex-wrap:wrap}}
.cbox{{background:#fff;border-radius:8px;padding:12px 16px;text-align:center;min-width:145px;box-shadow:0 1px 6px rgba(0,0,0,.08)}}
.cbox .cn{{font-size:12px;color:#666}}.cbox .cc{{font-size:24px;font-weight:bold;color:#fa709a}}
.cols{{display:flex;gap:20px}}.col{{flex:1}}
.fr{{display:flex;align-items:center;gap:0;margin-bottom:10px}}
.fb{{background:#dbeafe;border:1.5px solid #3b82f6;border-radius:8px;padding:14px 18px;text-align:center;min-width:170px}}
.fb .fn{{font-weight:bold;font-size:12px;color:#1e40af}}.fb .fd{{font-size:10px;color:#3b82f6;margin-top:4px}}
.fb.o{{background:#fef3c7;border-color:#f59e0b}}.fb.o .fn{{color:#92400e}}.fb.o .fd{{color:#b45309}}
.fa{{font-size:22px;color:#3b82f6;padding:0 6px;font-weight:bold}}
.st{{font-size:12px;color:#888;text-align:center;padding:6px 0}}
.footer{{background:#1a1a2e;color:#888;text-align:center;padding:20px;border-top:2px solid #333;margin-top:30px;font-size:12px}}
.arr{{text-align:center;color:#666;font-size:24px;margin:8px 0}}
.ib{{background:#fff;border-radius:10px;padding:16px 20px;margin-bottom:12px}}
.nx{{font-size:10px;display:flex;gap:3px;flex-wrap:wrap;margin:6px 0}}.nx span{{background:#ecfeff;padding:2px 6px;border-radius:3px;color:#0891b2}}
</style></head>
<body>

<div class="header">
  <h1>THE AGENCY — 系统架构图 {data['version']}</h1>
  <p>{data['total_agents']:,} AI Agent 角色定义库 | {data['total_categories']} 行业分类 | {sc['py_total']} 工具脚本 | {data['total_tests']:,} 测试 | {data['integration_targets_count']} 集成目标 | Python {data['python_req']}</p>
</div>
<div class="container">

<div class="layer l0">
  <div class="layer-h">第 0 层: CI/CD 持续集成流水线 ({data['ci_workflows_count']} 个 GitHub Actions 工作流)</div>
  <div class="layer-b">
    <div class="grid">
      {format_html_ci_cards(data['ci_workflows'])}
    </div>
    <div class="st">覆盖 push、PR、tag 和 cron 定时触发 — 在每个变更入口进行质量把关</div>
  </div>
</div>
<div class="arr">&#8595;</div>

<div class="layer l1">
  <div class="layer-h">第 1 层: 测试套件 ({data['test_modules_count']} 个模块 · {data['total_tests']:,} 个测试用例)</div>
  <div class="layer-b">
    <div class="grid">
      {format_html_test_cards(data['test_modules'])}
    </div>
    <div class="st">每个工具脚本都有对应测试 | 全部通过</div>
  </div>
</div>
<div class="arr">&#8595;</div>

<div class="layer l2">
  <div class="layer-h">第 2 层: 共享库 (scripts/_shared/) — {data['shared']['exports_count']} 个公开 API · {len(data['shared']['consumers'])} 个调用方</div>
  <div class="layer-b">
    <div class="grid">
      {format_html_shared_modules(data['shared'])}
    </div>
    <div class="st" style="margin-top:12px">调用方: {" | ".join(data['shared']['consumers'])}</div>
  </div>
</div>
<div class="arr">&#8595;</div>

<div class="layer l3">
  <div class="layer-h">第 3 层: 工具脚本 ({sc['py_total']} 个 Python 模块 + {sc['sh_total']} 个 Shell 包装)</div>
  <div class="layer-b">
    {format_html_script_grid(sc)}
  </div>
</div>
<div class="arr">&#8595;</div>

<div class="layer l4">
  <div class="layer-h">第 4 层: Agent 内容 ({data['total_agents']:,} 个 .md 文件 · {data['total_categories']} 行业分类)</div>
  <div class="layer-b">
    {format_html_category_bars(data['category_counts'], data['total_agents'])}
    <div class="cols" style="margin-top:14px">
      <div class="col" style="flex:2.5">
        <div class="ib" style="border:1.5px solid #fbbf24">
          <div style="font-weight:bold;color:#d97706;font-size:13px;margin-bottom:8px">Agent 文件结构</div>
          <div style="background:#fef3c7;padding:8px 12px;border-radius:4px;font-size:11px;color:#92400e;margin-bottom:6px">--- YAML 前置数据 (Frontmatter) ---</div>
          <div style="font-size:11px;line-height:1.8;color:#555">name | description | emoji | color <span style="color:#ef4444;font-size:10px">(必填)</span><br>version | date_added <span style="color:#f59e0b;font-size:10px">(自动填充)</span><br>vibe | nexus_roles | depends_on <span style="color:#888;font-size:10px">(可选)</span></div>
          <div style="background:#fef3c7;padding:8px 12px;border-radius:4px;font-size:11px;color:#92400e;margin:6px 0">--- 正文 (Body) ---</div>
          <div style="font-size:11px;line-height:1.8;color:#555">身份与记忆 | 核心使命 | 关键规则 | 可交付物 | 工作流程 | 沟通风格 | 成功指标</div>
        </div>
      </div>
      <div class="col">
        <div class="ib" style="border:1.5px solid #8b5cf6">
          <div style="font-weight:bold;color:#7c3aed;font-size:13px;margin-bottom:6px">特殊目录</div>
          <div style="font-size:11px;line-height:1.8;color:#555">libraries/ — 跨行业Agent<br>specialized/ — 跨领域角色<br>strategy/ — 战略咨询<br>nexus-projects/ — NEXUS项目<br>examples/ — 工作流示例</div>
        </div>
      </div>
    </div>
  </div>
</div>
<div class="arr">&#8595;</div>

<div class="layer l5">
  <div class="layer-h">第 5 层: 集成目标 ({data['integration_targets_count']} 种 AI 编程工具, 通过 convert.py 转换)</div>
  <div class="layer-b">
    <div class="grid">
      {format_html_integration_cards(data['integration_targets'])}
    </div>
    <div class="st">Claude Code 是唯一无需转换的目标 — 直接读取原始 .md 文件</div>
  </div>
</div>

<div class="layer l6">
  <div class="layer-h">第 6 层: 数据流转 & 模块依赖</div>
  <div class="layer-b">
    <div style="text-align:center;margin-bottom:12px">
      <div class="ib" style="display:inline-block;padding:8px 24px;background:#312e81;color:#c7d2fe;border-radius:6px;font-size:14px;font-weight:bold">_shared/ <span style="font-weight:normal;font-size:11px">(discovery · frontmatter · terminal)</span></div>
    </div>
    <div class="grid" style="grid-template-columns:repeat(4,1fr)">
      <div><div class="card" style="border-top:3px solid #ef4444"><div class="t">Quality Gate</div><div class="d">lint-agents · score-agents<br>analyze-deps · validate-index<br>quality-report</div></div></div>
      <div><div class="card" style="border-top:3px solid #f59e0b"><div class="t">Maintenance</div><div class="d">agent-lifecycle · contribute<br>expand-agent · add-comm-section</div></div></div>
      <div><div class="card" style="border-top:3px solid #8b5cf6"><div class="t">Integration</div><div class="d">convert · generate-index<br>build-agent-browser<br>build-architecture</div></div></div>
      <div><div class="card" style="border-top:3px solid #06b6d4"><div class="t">Discovery</div><div class="d">search-agents · i18n/*</div></div></div>
    </div>
    <div class="st" style="margin-top:12px">{len(data['shared']['consumers'])} 个脚本依赖 _shared/ → 所有脚本独立读取 agent 数据，通过 quality.py 编排质量流水线</div>
  </div>
</div>
<div class="arr">&#8595;</div>

<div class="layer l7">
  <div class="layer-h">第 7 层: NEXUS 多Agent编排 ({data['nexus_phases_count']} 个阶段)</div>
  <div class="layer-b">
    {format_html_nexus(data['nexus_phases'])}
    <div style="font-size:11px;color:#666;margin-top:12px">Agent 通过 nexus_roles 加入各阶段 | docs/nexus-strategy.md | docs/nexus-cycle.md | docs/playbooks/ | docs/runbooks/ | docs/teams/ | docs/coordination/</div>
  </div>
</div>

</div>
<div class="footer">
  {format_html_footer_stats(data)}<br>
  架构: CI/CD -> 测试 -> 共享库 -> 工具脚本 -> Agent 内容 -> 集成目标 -> 数据流 -> NEXUS 编排<br>
  生成时间: {data['generated']}
</div>
</body></html>"""


# ==========================================================================
# Main
# ==========================================================================


def main():
    parser = argparse.ArgumentParser(description="Build ARCHITECTURE.md and ARCHITECTURE.html from live project data")
    parser.add_argument("--out-md", default=str(REPO / "ARCHITECTURE.md"), help="Output path for Markdown")
    parser.add_argument("--out-html", default=str(REPO / "ARCHITECTURE.html"), help="Output path for HTML")
    parser.add_argument("--check", action="store_true", help="Verify generated files match committed versions")
    args = parser.parse_args()

    data = collect_architecture_data()
    md_content = render_markdown(data)
    html_content = render_html(data)

    if args.check:
        md_path = Path(args.out_md)
        html_path = Path(args.out_html)
        ok = True
        if md_path.read_text(encoding="utf-8") != md_content:
            print(f"ERROR: {md_path} is stale. Run scripts/build-architecture.py to update.", file=sys.stderr)
            ok = False
        if html_path.read_text(encoding="utf-8") != html_content:
            print(f"ERROR: {html_path} is stale. Run scripts/build-architecture.py to update.", file=sys.stderr)
            ok = False
        if ok:
            print("OK: ARCHITECTURE.md and ARCHITECTURE.html are up to date.")
        sys.exit(0 if ok else 1)

    Path(args.out_md).write_text(md_content, encoding="utf-8")
    Path(args.out_html).write_text(html_content, encoding="utf-8")

    print(f"Built {args.out_md} ({data['total_agents']:,} agents, {data['total_categories']} categories)")
    print(f"Built {args.out_html} ({data['total_agents']:,} agents, {data['total_categories']} categories)")


if __name__ == "__main__":
    main()
