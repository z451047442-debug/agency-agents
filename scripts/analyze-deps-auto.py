#!/usr/bin/env python3
"""
Auto-detect agent dependencies — v3: body content matching within same category.

Strategy: For each agent without depends_on, scan its body content for references
to other agents' key concepts within the SAME category. Same-category matching
eliminates most false positives while finding genuine workflow/pipeline relationships.

Confidence levels:
- HIGH (>=12): strong concept overlap OR named reference in body text
- MEDIUM (6-11): moderate overlap, needs human review
"""
import json
import os
import re
from collections import defaultdict, Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def load_agents():
    with open(REPO_ROOT / 'AGENTS.json', encoding='utf-8') as f:
        return json.load(f)['agents']

def find_agent_file(agent_id):
    """Find the .md file for an agent by ID."""
    for cat_dir in REPO_ROOT.iterdir():
        if not cat_dir.is_dir():
            continue
        name = cat_dir.name
        if name in ('docs','examples','integrations','schemas','scripts','tests','env','.git','.github','.pytest_cache','__pycache__'):
            continue
        # Direct match
        md_file = cat_dir / f"{agent_id}.md"
        if md_file.exists():
            return md_file
        # Subdirectory match (game-development subdirs)
        for subdir in cat_dir.iterdir():
            if subdir.is_dir():
                md_file = subdir / f"{agent_id}.md"
                if md_file.exists():
                    return md_file
    # Check special directories
    for sdir in ('libraries','specialized','_solution','strategy','network-engineering'):
        sd = REPO_ROOT / sdir
        if sd.is_dir():
            md_file = sd / f"{agent_id}.md"
            if md_file.exists():
                return md_file
    return None

def extract_keywords(name, description):
    """Extract meaningful domain keywords from name + description."""
    text = f"{name} {description}".lower()
    # Split on Chinese/English word boundaries
    tokens = re.findall(r'[a-z0-9一-鿿]+', text)
    # Remove generic stop words
    stop = {'the','and','for','with','from','that','this','over','expert','all','of','in','to','a',
            'is','on','by','an','or','at','its','has','per','can','are','it','as','be','was','not',
            'but','into','using','their','have','also','each','more','when','one','use','may','new',
            'our','been','will','out','up','no','if','so','than','support','platform','management',
            'system','process','data','service','business','product','design','manager','role','work',
            'team','access','project','solution','development','agent','ensure','based','key','well',
            'time','including','help','provide','across','features','tools','applications','used',
            'related','available','required','experience','experience','specific','focus','best',
            'build','knowledge','needs','skills','deliver','through','enable','ability','complex',
            'approach','different','advanced','modern','technical','critical','analysis','projects',
            'years','handling','testing','within','including','creating','specialist','background',
            'digital','various','expertise','strategies','issues','professional','multiple','drive',
            'success','quality','performance','industry','strategic','improvement','continuous'}
    tokens = [t for t in tokens if len(t) >= 3 and t not in stop]
    return set(tokens)

def main():
    all_agents = load_agents()
    needs_deps = [a for a in all_agents if not a.get('depends_on') or len(a['depends_on']) == 0]
    print(f"Agents without depends_on: {len(needs_deps)}/{len(all_agents)}")

    # Build keyword profiles for all agents
    agent_keywords = {}
    agent_files = {}
    for a in all_agents:
        kw = extract_keywords(a.get('name',''), a.get('description',''))
        agent_keywords[a['id']] = kw
        agent_files[a['id']] = find_agent_file(a['id'])

    # Group agents by category for same-category matching
    by_category = defaultdict(list)
    for a in all_agents:
        by_category[a['category']].append(a)

    high_conf = {}
    med_conf = {}

    for i, agent in enumerate(needs_deps):
        if i % 100 == 0:
            print(f"  Processing {i}/{len(needs_deps)}...")

        aid = agent['id']
        cat = agent['category']
        existing = set(agent.get('depends_on', []))
        my_kw = agent_keywords.get(aid, set())

        # Load body content
        mdfile = agent_files.get(aid)
        if not mdfile:
            continue
        body = mdfile.read_text(encoding='utf-8')
        # Skip frontmatter
        fm_end = body.find('---', 3)
        if fm_end < 0:
            continue
        body_lower = body[fm_end:].lower()

        candidates = []
        same_cat = [a for a in by_category.get(cat, []) if a['id'] != aid and a['id'] not in existing]

        for target in same_cat:
            tid = target['id']
            tk = agent_keywords.get(tid, set())

            # Count how many target keywords appear in this agent's body
            matches = 0
            weighted = 0.0
            matched_terms = []
            for term in tk:
                if len(term) < 4:  # skip very short terms
                    continue
                c = body_lower.count(term)
                if c > 0:
                    matches += 1
                    weighted += min(c, 5)
                    matched_terms.append(term)

            # Also check if target agent name appears explicitly
            target_name = target.get('name','').lower()
            name_refs = body_lower.count(target_name) if len(target_name) > 4 else 0

            if matches >= 2 and (weighted >= 4 or name_refs >= 1):
                score = weighted + name_refs * 3
                candidates.append({
                    'agent_id': tid,
                    'score': round(score, 1),
                    'matches': matches,
                    'name_refs': name_refs,
                    'terms': matched_terms[:8],
                })

        candidates.sort(key=lambda x: -x['score'])
        if candidates:
            hi = [c for c in candidates if c['score'] >= 8]
            med = [c for c in candidates if 4 <= c['score'] < 8]
            if hi:
                high_conf[aid] = hi[:4]
            elif med:
                med_conf[aid] = med[:4]

    total_hi = sum(len(v) for v in high_conf.values())
    total_med = sum(len(v) for v in med_conf.values())

    print(f"\n=== Results ===")
    print(f"High-confidence (>=8): {len(high_conf)} agents, {total_hi} deps")
    print(f"Medium-confidence (4-8): {len(med_conf)} agents, {total_med} deps")

    existing = len([a for a in all_agents if a.get('depends_on') and len(a['depends_on']) > 0])
    new_hi = existing + len(high_conf)
    new_all = existing + len(high_conf) + len(med_conf)
    print(f"Coverage: {existing}/{len(all_agents)} ({existing/len(all_agents)*100:.0f}%)")
    print(f"  + high only: {new_hi}/{len(all_agents)} ({new_hi/len(all_agents)*100:.0f}%)")
    print(f"  + all: {new_all}/{len(all_agents)} ({new_all/len(all_agents)*100:.0f}%)")

    output = {'high_confidence': high_conf, 'medium_confidence': med_conf}
    with open(REPO_ROOT / 'suggested_deps.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Show samples
    print("\n=== Sample HIGH ===")
    for i, (aid, deps) in enumerate(list(high_conf.items())[:20]):
        cat = next((a['category'] for a in all_agents if a['id'] == aid), '')
        print(f"\n{aid} ({cat}):")
        for d in deps[:3]:
            print(f"  -> {d['agent_id']} score={d['score']} matches={d['matches']} terms={d['terms'][:4]}")

if __name__ == '__main__':
    main()
