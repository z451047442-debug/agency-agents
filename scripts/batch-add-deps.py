#!/usr/bin/env python3
"""Batch-apply high-confidence depends_on suggestions to agent frontmatter."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GENERIC = {
    'data-science-engineering-knowledge-management',
}

def find_file(aid):
    for cat_dir in ROOT.iterdir():
        if not cat_dir.is_dir() or cat_dir.name in ('docs','examples','integrations','schemas','scripts','tests','env','.git','.github','__pycache__','.pytest_cache'):
            continue
        p = cat_dir / f"{aid}.md"
        if p.exists(): return p
        for sd in cat_dir.iterdir():
            if sd.is_dir():
                p = sd / f"{aid}.md"
                if p.exists(): return p
    for s in ('libraries','specialized','_solution','strategy','network-engineering'):
        sd = ROOT / s
        if sd.is_dir():
            p = sd / f"{aid}.md"
            if p.exists(): return p
    return None

def add_deps(filepath, dep_ids):
    c = filepath.read_text(encoding='utf-8')
    lines = c.split('\n')
    fm_end = None
    for i, line in enumerate(lines):
        if i > 0 and line.strip() == '---':
            fm_end = i; break
    if fm_end is None: return False

    fm = '\n'.join(lines[1:fm_end])
    if 'depends_on:' in fm:
        # Add to existing list
        dep_line = None
        for i in range(fm_end):
            if lines[i].strip().startswith('depends_on:'):
                dep_line = i; break
        if dep_line is None: return False
        existing = []
        for j in range(dep_line + 1, fm_end):
            l = lines[j].strip()
            if l.startswith('- '):
                existing.append(l[2:].strip().strip('"').strip("'"))
            elif l and not l.startswith('  '): break
        to_add = [d for d in dep_ids if d not in existing]
        if not to_add: return False
        insert_at = dep_line + 1 + len(existing)
        for d in to_add:
            lines.insert(insert_at, f'  - {d}')
            insert_at += 1
            fm_end += 1
    else:
        # Find last multi-line field or nexus_roles block
        insert_at = None
        for i in range(1, fm_end):
            ls = lines[i].strip()
            if ls.startswith('nexus_roles:'):
                # Find end of list
                j = i + 1
                while j < fm_end and lines[j].strip().startswith('- '):
                    j += 1
                insert_at = j; break
        if insert_at is None:
            for i in range(1, fm_end):
                if ':' in lines[i] and not lines[i].strip().startswith('-'):
                    insert_at = i + 1
        if insert_at is None: insert_at = fm_end
        new_lines = ['', 'depends_on:'] + [f'  - {d}' for d in dep_ids]
        for nl in reversed(new_lines):
            lines.insert(insert_at, nl)
            fm_end += 1

    filepath.write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    return True

def main():
    with open(ROOT / 'suggested_deps.json', encoding='utf-8') as f:
        data = json.load(f)
    high = data['high_confidence']
    print(f"Loaded {len(high)} high-confidence suggestions")
    applied = skipped = total = 0
    for aid, deps in high.items():
        filtered = [d for d in deps if d['agent_id'] not in GENERIC]
        if not filtered: skipped += 1; continue
        dep_ids = [d['agent_id'] for d in filtered[:3]]
        mdf = find_file(aid)
        if not mdf: skipped += 1; continue
        try:
            if add_deps(mdf, dep_ids):
                applied += 1; total += len(dep_ids)
        except Exception:
            skipped += 1
    print(f"Applied: {applied} agents, {total} deps, Skipped: {skipped}")
    # Count
    agents_data = json.load(open(ROOT / 'AGENTS.json', encoding='utf-8'))
    with_deps = sum(1 for a in agents_data['agents'] if a.get('depends_on') and len(a['depends_on']) > 0)
    # Not regenerated yet, add our applied count
    est = with_deps + applied
    print(f"Est coverage: {est}/{len(agents_data['agents'])} ({est/len(agents_data['agents'])*100:.0f}%)")
    print("Run ./scripts/generate-index.sh to update AGENTS.json")

if __name__ == '__main__':
    main()
