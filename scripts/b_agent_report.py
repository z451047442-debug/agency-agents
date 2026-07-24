import json
import sys
from collections import Counter

d = json.load(sys.stdin)
agents = d['v5']['agents']
b_agents = [a for a in agents if a['v5_grade'] == 'B']
print(f'Remaining B agents: {len(b_agents)}')
cats = Counter(a['category'] for a in b_agents)
for cat, count in sorted(cats.items()):
    print(f'  {cat}: {count}')
for a in b_agents:
    scores = a.get('v5_scores', {})
    print(f'  {a["v5_risk_tier"]:8s} | total={a["v5_total"]} | {a["path"]}')
