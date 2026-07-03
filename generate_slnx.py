"""Generate Visual Studio solution files for the agency-agents project.

Generates TWO formats:
  1. agency-agents.sln  — traditional format (reliable, VS 2005+).
     Uses solution-folders + SolutionItems to organize loose .md files.
  2. agency-agents.slnx — XML format (VS 2022 17.14+).
     Requires at least one <Project>, so we add a placeholder.

Both are re-generated from the same folder definitions below.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent

# Files at repo root shown under "Solution Items"
ROOT_FILES: list[str] = [
    ".gitattributes", ".gitignore",
    "AGENTS.json",
    "CONTRIBUTING.md", "CONTRIBUTING_zh-CN.md",
    "LICENSE", "README.md", "SECURITY.md",
]

# ── Folder definitions ─────────────────────────────────────────────
# (display_name, filesystem_directory, parent_solution_folder)
# parent = "Agents" | "Docs"

AGENTS = "Agents"
DOCS = "Docs"

FOLDERS: list[tuple[str, str, str]] = [
    # -- Agents --
    ("administration",        "administration",        AGENTS),
    ("aerospace",             "aerospace",             AGENTS),
    ("agriculture",           "agriculture",           AGENTS),
    ("automotive",            "automotive",            AGENTS),
    ("beauty",                "beauty",                AGENTS),
    ("construction",          "construction",          AGENTS),
    ("customer-service",      "customer-service",      AGENTS),
    ("cybersecurity",         "cybersecurity",         AGENTS),
    ("data-science",          "data-science",          AGENTS),
    ("design",                "design",                AGENTS),
    ("education",             "education",             AGENTS),
    ("emergency",             "emergency",             AGENTS),
    ("energy",                "energy",                AGENTS),
    ("engineering",           "engineering",           AGENTS),
    ("environmental",         "environmental",         AGENTS),
    ("events",                "events",                AGENTS),
    ("fashion",               "fashion",               AGENTS),
    ("finance",               "finance",               AGENTS),
    ("food-beverage",         "food-beverage",         AGENTS),
    ("forestry",              "forestry",              AGENTS),
    ("gis",                   "gis",                   AGENTS),
    ("game-development",      "game-development",      AGENTS),
    ("blender",               "game-development/blender",       AGENTS),
    ("godot",                 "game-development/godot",         AGENTS),
    ("roblox-studio",         "game-development/roblox-studio", AGENTS),
    ("unity",                 "game-development/unity",         AGENTS),
    ("unreal-engine",         "game-development/unreal-engine", AGENTS),
    ("government",            "government",            AGENTS),
    ("healthcare",            "healthcare",            AGENTS),
    ("hr",                    "hr",                    AGENTS),
    ("hr-tech",               "hr-tech",               AGENTS),
    ("infrastructure",        "infrastructure",        AGENTS),
    ("insurance",             "insurance",             AGENTS),
    ("iot",                   "iot",                   AGENTS),
    ("legal",                 "legal",                 AGENTS),
    ("libraries",             "libraries",             AGENTS),
    ("localization",          "localization",          AGENTS),
    ("logistics",             "logistics",             AGENTS),
    ("lottery",               "lottery",               AGENTS),
    ("manufacturing",         "manufacturing",         AGENTS),
    ("marketing",             "marketing",             AGENTS),
    ("mining",                "mining",                AGENTS),
    ("museums",               "museums",               AGENTS),
    ("media-entertainment",   "media-entertainment",   AGENTS),
    ("network-engineering",   "network-engineering",   AGENTS),
    ("nonprofit",             "nonprofit",             AGENTS),
    ("operations",            "operations",            AGENTS),
    ("pets",                  "pets",                  AGENTS),
    ("pharma-biotech",        "pharma-biotech",        AGENTS),
    ("product",               "product",               AGENTS),
    ("project-management",    "project-management",    AGENTS),
    ("publishing",            "publishing",            AGENTS),
    ("quality",               "quality",               AGENTS),
    ("real-estate",           "real-estate",           AGENTS),
    ("retail",                "retail",                AGENTS),
    ("robotics",              "robotics",              AGENTS),
    ("sales",                 "sales",                 AGENTS),
    ("securities",            "securities",            AGENTS),
    ("security",              "security",              AGENTS),
    ("spatial-computing",     "spatial-computing",     AGENTS),
    ("specialized",           "specialized",           AGENTS),
    ("sports",                "sports",                AGENTS),
    ("telecom",               "telecom",               AGENTS),
    ("testing",               "testing",               AGENTS),
    ("tourism",               "tourism",               AGENTS),
    ("web3",                  "web3",                  AGENTS),
    # -- Docs --
    ("examples",              "examples",              DOCS),
    ("integrations",          "integrations",          DOCS),
    ("aider",                 "integrations/aider",          DOCS),
    ("antigravity",           "integrations/antigravity",    DOCS),
    ("claude-code",           "integrations/claude-code",    DOCS),
    ("cursor",                "integrations/cursor",         DOCS),
    ("gemini-cli",            "integrations/gemini-cli",     DOCS),
    ("github-copilot",        "integrations/github-copilot", DOCS),
    ("kimi",                  "integrations/kimi",           DOCS),
    ("mcp-memory",            "integrations/mcp-memory",     DOCS),
    ("openclaw",              "integrations/openclaw",       DOCS),
    ("opencode",              "integrations/opencode",       DOCS),
    ("qwen",                  "integrations/qwen",           DOCS),
    ("windsurf",              "integrations/windsurf",       DOCS),
    ("schemas",               "schemas",               DOCS),
    ("i18n",                  "scripts/i18n",           DOCS),
    ("docs",                  "docs",                   DOCS),
    ("coordination",          "docs/coordination",      DOCS),
    ("playbooks",             "docs/playbooks",         DOCS),
    ("runbooks",              "docs/runbooks",          DOCS),
    ("teams",                 "docs/teams",             DOCS),
]

# Namespace UUID for deterministic GUID generation.
# Any fixed UUID works; same input → same output every run.
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def folder_guid(name: str) -> str:
    """Deterministic GUID for a solution-folder name."""
    return str(uuid.uuid5(NS, name)).upper()


# ────────────────────────────────────────────────────────────────────
#  File-system helpers
# ────────────────────────────────────────────────────────────────────

def collect_files(subdir: str) -> list[str]:
    """Sorted relative paths (forward slashes) of .md/.json files under *subdir*."""
    full = ROOT / subdir
    if not full.is_dir():
        return []
    return sorted(
        str(f.resolve().relative_to(ROOT)).replace("\\", "/")
        for f in full.iterdir()
        if f.is_file() and f.suffix in (".md", ".json")
    )


# ════════════════════════════════════════════════════════════════════
#  Traditional .sln generator
# ════════════════════════════════════════════════════════════════════

SOLUTION_FOLDER_GUID = "{2150E333-8FDC-42A3-9474-1A3956D46DE8}"

SLN_HEADER = (
    "﻿\r\n"   # UTF-8 BOM + blank line (VS convention)
    "Microsoft Visual Studio Solution File, Format Version 12.00\r\n"
    "# Visual Studio Version 18\r\n"
    "VisualStudioVersion = 18.0\r\n"
    "MinimumVisualStudioVersion = 10.0.40219.1\r\n"
)


def _sln_project_entry(name: str, guid: str, items: list[str] | None = None) -> str:
    """Return a Project entry block for a solution folder.

    If *items* is given, the folder holds SolutionItems (root-level files).
    """
    lines = [
        f'Project("{SOLUTION_FOLDER_GUID}") = "{name}", "{name}", "{guid}"',
    ]
    if items is not None:
        lines.append("    ProjectSection(SolutionItems) = preProject")
        for item in items:
            lines.append(f"        {item} = {item}")
        lines.append("    EndProjectSection")
    lines.append("EndProject")
    return "\r\n".join(lines) + "\r\n"


def generate_sln() -> str:
    """Build the full .sln content."""
    parts: list[str] = [SLN_HEADER]

    # Project entries for every folder
    si_guid = folder_guid("Solution Items")
    parts.append(_sln_project_entry("Solution Items", si_guid, ROOT_FILES))

    agents_guid = folder_guid(AGENTS)
    parts.append(_sln_project_entry(AGENTS, agents_guid))

    docs_guid = folder_guid(DOCS)
    parts.append(_sln_project_entry(DOCS, docs_guid))

    parent_of: dict[str, str] = {}  # folder_name → parent_name

    for display_name, _fs_dir, parent in FOLDERS:
        g = folder_guid(display_name)
        files = collect_files(_fs_dir)
        parts.append(_sln_project_entry(display_name, g, files))
        parent_of[display_name] = parent

    # Global section
    parts.append("Global\r\n")

    # SolutionConfigurationPlatforms
    parts.append(
        "    GlobalSection(SolutionConfigurationPlatforms) = preSolution\r\n"
        "        Debug|Any CPU = Debug|Any CPU\r\n"
        "        Release|Any CPU = Release|Any CPU\r\n"
        "    EndGlobalSection\r\n"
    )

    # SolutionProperties
    parts.append(
        "    GlobalSection(SolutionProperties) = preSolution\r\n"
        "        HideSolutionNode = FALSE\r\n"
        "    EndGlobalSection\r\n"
    )

    # NestedProjects — define folder hierarchy
    parts.append("    GlobalSection(NestedProjects) = preSolution\r\n")
    for child_name, parent_name in parent_of.items():
        child_g = folder_guid(child_name)
        parent_g = folder_guid(parent_name)
        parts.append(f"        {child_g} = {parent_g}\r\n")
    # top-level folders nest under nothing (they stay at root)
    parts.append("    EndGlobalSection\r\n")

    parts.append("EndGlobal\r\n")
    return "".join(parts)


# ════════════════════════════════════════════════════════════════════
#  .slnx generator  (XML format — best-effort, may need a <Project>)
# ════════════════════════════════════════════════════════════════════

def build_slnx() -> str:
    solution = ET.Element("Solution")

    configs = ET.SubElement(solution, "Configurations")
    ET.SubElement(configs, "Platform", Name="Any CPU")
    ET.SubElement(configs, "BuildType", Name="Debug")
    ET.SubElement(configs, "BuildType", Name="Release")

    # Solution Items
    si = ET.SubElement(solution, "Folder", Name="Solution Items")
    for f in ROOT_FILES:
        ET.SubElement(si, "File", Path=f)

    agents_el = ET.SubElement(solution, "Folder", Name=AGENTS)
    docs_el = ET.SubElement(solution, "Folder", Name=DOCS)
    parent_map = {AGENTS: agents_el, DOCS: docs_el}

    for display_name, fs_dir, parent in FOLDERS:
        files = collect_files(fs_dir)
        folder_el = ET.SubElement(parent_map[parent], "Folder", Name=display_name)
        for fp in files:
            ET.SubElement(folder_el, "File", Path=fp)

    raw = ET.tostring(solution, encoding="unicode")
    dom = minidom.parseString(raw)
    return dom.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


# ════════════════════════════════════════════════════════════════════

def main() -> None:
    sln_path = ROOT / "agency-agents.sln"
    slnx_path = ROOT / "agency-agents.slnx"

    sln_content = generate_sln()
    sln_path.write_text(sln_content, encoding="utf-8", newline="")
    print(f"[OK] {sln_path.name}  ({len(sln_content):,} bytes)")

    slnx_content = build_slnx()
    slnx_path.write_text(slnx_content, encoding="utf-8")
    print(f"[OK] {slnx_path.name}  ({len(slnx_content):,} bytes)")


if __name__ == "__main__":
    main()
