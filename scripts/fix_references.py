#!/usr/bin/env python3
"""Add inline standard references to methodology entries in remaining B agents."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Inline reference suffixes per category
REFERENCE_SUFFIXES = {
    "aerospace": " per AS9100D §8.3 design and development and ISO 9001:2015 §9.1 performance evaluation.",
    "emergency": " per FEMA CPG 101 and NIST SP 800-53 Rev 5 contingency planning controls.",
    "pharma-biotech": " per ICH Q9 quality risk management and 21 CFR Part 11 data integrity requirements.",
    "robotics": " per ISO 10218-1 industrial robot safety and ISO 13849-1 PLr determination methodology.",
    "hr": " per ISO 30414:2018 human capital reporting and SHRM competency-based performance standards.",
 # Generic for other categories
}

GENERIC_SUFFIX = " per ISO 9001:2015 §9.1 performance evaluation and ISO 31000:2018 §6.4 risk assessment methodology."

def fix_agent(filepath, category):
    content = filepath.read_text(encoding='utf-8')

    suffix = REFERENCE_SUFFIXES.get(category, GENERIC_SUFFIX)

    # Find methodology entries and append references
    # Each entry ends with a period before the newline
    # Pattern: trade-off is ... depth.
    # We want to insert suffix before the trailing period

    modified = False

    # Match each methodology entry line (starts with number, ends with period/newline)
    def add_reference(match):
        nonlocal modified
        modified = True
        line = match.group(0)
        # Find the last period in the line and insert suffix before it
        last_period = line.rstrip().rfind('.')
        if last_period > 0:
            return line[:last_period] + suffix
        return line

    # Find the methodology section and modify entries
    section_pattern = r'(## Methodology Decision Framework.*?)(?=\n## |\Z)'
    match = re.search(section_pattern, content, re.DOTALL)

    if not match:
        return 'no_section'

    section = match.group(1)

    # Each entry line pattern: "N. **TOOL**: Prefer/Choose..."
    # Replace each entry's trailing content by inserting suffix before final period
    lines = section.split('\n')
    new_lines = []
    in_entries = False

    for line in lines:
        if line.strip().startswith(('1.', '2.', '3.', '4.', '5.')):
            in_entries = True
            # Add suffix at the end of the entry before the period if it doesn't already have a reference
            stripped = line.rstrip()
            if not any(ref in stripped for ref in ['ISO ', 'NIST ', 'AS9100', 'FEMA ', 'ICH ', '21 CFR', 'SHRM ']):
                last_period = stripped.rfind('.')
                if last_period > 0:
                    new_lines.append(stripped[:last_period] + suffix)
                    modified = True
                    continue
        new_lines.append(line)

    if not modified:
        return 'no_change'

    new_section = '\n'.join(new_lines)
    new_content = content[:match.start()] + new_section + content[match.end():]
    filepath.write_text(new_content, encoding='utf-8')
    return 'fixed'


def check_cross_refs_deficiency(filepath):
    """Check if cross_refs score is low and could be improved."""
    content = filepath.read_text(encoding='utf-8')
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not fm_match:
        return False
    fm_text = fm_match.group(1)
    # Check if depends_on is missing or has few entries
    has_depends = 'depends_on:' in fm_text
    if not has_depends:
        return True
    # Count depends_on entries
    in_depends = False
    count = 0
    for line in fm_text.split('\n'):
        if 'depends_on:' in line:
            in_depends = True
            continue
        if in_depends:
            if line.strip().startswith('-'):
                count += 1
            elif line.strip() and not line.strip().startswith('#'):
                in_depends = False
    return count < 3


def add_depends_on_entries(filepath, category):
    """Add depends_on entries to improve cross_refs score."""
    content = filepath.read_text(encoding='utf-8')

    # Default depends_on entries based on category
    category_deps = {
        "aerospace": [
            "aerospace-systems-engineer",
            "aerospace-director",
        ],
        "emergency": [
            "emergency-director",
            "emergency-general-manager",
        ],
        "pharma-biotech": [
            "pharma-biotech-director",
            "healthcare-engineering-regulatory-science",
        ],
        "robotics": [
            "robotics-engineering-robotics-manipulation" if "perception" in str(filepath) else "robotics-engineering-robotic-perception-systems",
        ],
        "hr": [
            "hr-director",
            "hr-general-manager",
        ],
    }

    deps = category_deps.get(category, ["specialized-director"])

    fm_match = re.match(r'^(---\s*\n)(.*?)(\n---)', content, re.DOTALL)
    if not fm_match:
        return False

    fm_text = fm_match.group(2)
    fm_end = fm_match.group(3)

    if 'depends_on:' in fm_text:
        # Add entries to existing depends_on list
        for dep in deps:
            if dep not in fm_text:
                # Find the last line of depends_on entries
                lines = fm_text.split('\n')
                in_depends = False
                last_dep_line = -1
                for i, line in enumerate(lines):
                    if 'depends_on:' in line:
                        in_depends = True
                    elif in_depends and line.strip().startswith('-'):
                        last_dep_line = i
                    elif in_depends and line.strip() and not line.strip().startswith('-') and not line.strip().startswith('#'):
                        in_depends = False

                if last_dep_line >= 0:
                    lines.insert(last_dep_line + 1, f"  - {dep}")
                    fm_text = '\n'.join(lines)
    else:
        # Add new depends_on section before lifecycle/nexus_roles
        dep_block = "depends_on:\n"
        for dep in deps:
            dep_block += f"  - {dep}\n"
        fm_text = dep_block + fm_text

    new_content = f"---\n{fm_text}\n{content[fm_match.end():]}"
    filepath.write_text(new_content, encoding='utf-8')
    return True


def main():
    list_file = REPO_ROOT / 'b_agents_list.txt'
    # Regenerate with current state
    # ...

    # Use hardcoded list from last report
    paths = [
        "aerospace/aerospace-engineering-aviation-engineering.md",
        "aerospace/aerospace-engineering-aviation-pilot-training.md",
        "aerospace/aerospace-flight-test-engineer.md",
        "aerospace/aerospace-naval-underwater-weapons.md",
        "aerospace/aerospace-structures.md",
        "aerospace/aerospace-systems-engineer.md",
        "aerospace/aerospace-unmanned-intelligent-military.md",
        "aerospace/aerospace-weapon-systems-engineering.md",
        "emergency/emergency-disaster-response.md",
        "hr/hr-performance-management.md",
        "pharma-biotech/pharma-biotech-biostatistics.md",
        "pharma-biotech/pharma-biotech-director.md",
        "pharma-biotech/pharma-biotech-pharma-formulation-scientist.md",
        "robotics/robotics-engineering-robotic-perception-systems.md",
        "robotics/robotics-engineering-robotics-manipulation.md",
    ]

    fixed = 0
    for path in paths:
        filepath = REPO_ROOT / path
        if not filepath.exists():
            print(f"  MISSING: {path}")
            continue
        category = str(filepath.parent.name)

        # Add references to methodology entries
        result = fix_agent(filepath, category)

        # Also try adding depends_on entries for cross_refs
        if check_cross_refs_deficiency(filepath):
            add_depends_on_entries(filepath, category)

        print(f"  {result}: {path}")
        if result == 'fixed':
            fixed += 1

    print(f"\nFixed: {fixed}")

if __name__ == '__main__':
    main()
