#!/usr/bin/env python
"""Boilerplate cleaner — removes AI template phrases from B-grade agents."""

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

BP_FIXES = [
    (r"Deliver expert, actionable guidance in your domain\.\s*", ""),
    (r"Every output is grounded in best practices,?\s*", ""),
    (r"current industry knowledge, and a commitment to practical,?\s*", ""),
    (r"implementable solutions tailored to the specific context\.\s*", ""),
    (r"You(?:'ve| have) seen [^.]*\.\s*", ""),
    (r"You remember [^.]*\.\s*", ""),
    (r"you carry forward [^.]*\.\s*", ""),
    (r"drawing on your extensive experience[^.]*\.\s*", ""),
    (r"your deep understanding of [^.]*\.\s*", ""),
    (r"You bring deep domain expertise honed through years of professional practice\.?\s*", ""),
    (r"Deliver expert, actionable guidance in your domain",
     "Apply domain methodologies to produce concrete, measurable outcomes"),
    (r"\[Domain Rule \d+\]\s*", ""),
    (r"\[Domain knowledge bullet \d+\]\s*", ""),
    (r"\[key question \d+\]\s*", ""),
    (r"\[Persona Name\]\s*", ""),
    (r"FILL_THIS_IN\s*", ""),
    (r"professional clarity: direct when urgency demands",
     "be direct and specific; use concrete examples over abstractions"),
    (r"professional clarity and precision: structured executive summaries",
     "lead with the conclusion; follow with structured evidence and reasoning"),
]
BP_COMPILED = [(re.compile(p, re.IGNORECASE), r) for p, r in BP_FIXES]


def clean(path):
    c = path.read_text(encoding="utf-8")
    parts = c.split("---", 2)
    if len(parts) < 3:
        return False, 0
    body = parts[2]
    new_body = body
    removed = 0
    for pat_re, repl in BP_COMPILED:
        m = len(pat_re.findall(new_body))
        if m > 0:
            new_body = pat_re.sub(repl, new_body)
            removed += m
    if removed == 0:
        return False, 0
    path.write_text("---".join(parts[:2]) + "---" + new_body, encoding="utf-8")
    return True, removed


def main():
    sc = ["python", str(REPO/"scripts"/"score-agents.py"), "--json", "--no-freshness"]
    r = subprocess.run(sc, capture_output=True, text=True, timeout=120, cwd=str(REPO))
    data = json.loads(r.stdout)
    gold = [a for a in data["agents"] if a["total"]>=8 and a.get("tool_references",0)>=2
            and a.get("boilerplate_count",0)<=3 and a["word_count"]>=500]
    targets = [a for a in gold if a["total"]==8]
    if not targets:
        print("No B-grade agents!")
        return
    print(f"Cleaning {len(targets)} agents\n")
    cleaned = total_removed = 0
    for a in targets:
        p = REPO / a["category"] / f"{a['id']}.md"
        if not p.exists(): continue
        mod, cnt = clean(p)
        if mod:
            cleaned += 1; total_removed += cnt
            if cnt >= 2: print(f"  [{cnt} phrases] {a['id']}")
    print(f"\nCleaned {cleaned} agents ({total_removed} phrases)")
    r2 = subprocess.run(sc, capture_output=True, text=True, timeout=120, cwd=str(REPO))
    nd = json.loads(r2.stdout)
    ng = [a for a in nd["agents"] if a["total"]>=8 and a.get("tool_references",0)>=2
          and a.get("boilerplate_count",0)<=3 and a["word_count"]>=500]
    na = sum(1 for a in ng if a["total"]>=9)
    nb = sum(1 for a in ng if a["total"]==8)
    old_a = sum(1 for a in gold if a["total"]>=9)
    print(f"\nGold A: {na} (+{na-old_a})  Gold B: {nb}  Total: {len(ng)}")
    upgraded = [a for a in ng if a["total"]>=9 and
                next((x for x in gold if x["id"]==a["id"]), {}).get("total",0)==8]
    if upgraded:
        print("\nUpgraded:")
        for a in upgraded[:15]:
            print(f"  {a['id']:<45} {a['total']}/10 {a['grade']} BP={a.get('boilerplate_count',0)}")


if __name__ == "__main__":
    main()
