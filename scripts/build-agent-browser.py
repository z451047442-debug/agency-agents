#!/usr/bin/env python
"""Build a self-contained agent-browser.html from AGENTS.json.

Usage:
    python scripts/build-agent-browser.py [--out <path>]

Output: a standalone HTML file with embedded agent data — double-click to open,
no server needed.
"""

import json
import sys
from pathlib import Path

from _shared import REPO

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Agency — Agent Browser</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:"Microsoft YaHei","PingFang SC",sans-serif;background:#1a1a2e;color:#e0e0e0;display:flex;height:100vh;overflow:hidden}
/* sidebar */
.sidebar{width:260px;min-width:260px;background:#16213e;border-right:1px solid #333;display:flex;flex-direction:column;overflow:hidden}
.sidebar h2{padding:16px 20px 12px;font-size:16px;color:#fff;border-bottom:1px solid #333}
.cat-list{flex:1;overflow-y:auto;padding:8px 0}
.cat-item{display:flex;justify-content:space-between;align-items:center;padding:8px 20px;cursor:pointer;font-size:13px;transition:background .15s;border-left:3px solid transparent}
.cat-item:hover{background:rgba(255,255,255,.04)}
.cat-item.active{background:rgba(99,102,241,.15);border-left-color:#6366f1;color:#a5b4fc}
.cat-item .count{font-size:11px;color:#666;background:rgba(255,255,255,.06);padding:1px 8px;border-radius:10px}
.cat-item.active .count{background:rgba(99,102,241,.2);color:#a5b4fc}
.cat-item.all{margin-bottom:6px;font-weight:bold}
/* main */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.toolbar{padding:16px 24px;background:#1e1e3a;border-bottom:1px solid #333;display:flex;gap:12px;align-items:center}
.toolbar input{flex:1;padding:10px 16px;border-radius:8px;border:1px solid #444;background:#16213e;color:#e0e0e0;font-size:14px;outline:none;transition:border-color .2s}
.toolbar input:focus{border-color:#6366f1}
.toolbar .stats{font-size:13px;color:#888;white-space:nowrap}
.grid{flex:1;overflow-y:auto;padding:20px 24px;display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:14px;align-content:start}
/* card */
.card{background:#1e1e3a;border-radius:12px;padding:18px 20px;border:1px solid #2a2a4a;transition:transform .15s,border-color .15s;cursor:default;display:flex;flex-direction:column;gap:10px}
.card:hover{transform:translateY(-2px);border-color:#6366f1}
.card .head{display:flex;align-items:flex-start;gap:12px}
.card .emoji{font-size:32px;line-height:1;flex-shrink:0}
.card .info{flex:1;min-width:0}
.card .name{font-size:15px;font-weight:bold;color:#fff;margin-bottom:4px}
.card .desc{font-size:12px;color:#999;line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card .meta{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.card .tag{font-size:10px;padding:3px 8px;border-radius:4px;font-weight:bold}
.tag-cat{background:rgba(99,102,241,.15);color:#a5b4fc}
.tag-nexus{background:rgba(16,185,129,.12);color:#6ee7b7}
.card .extra{display:none;border-top:1px solid #2a2a4a;padding-top:10px}
.card.open .extra{display:block}
.card .extra .label{font-size:10px;color:#666;text-transform:uppercase;letter-spacing:.5px;margin:6px 0 4px}
.card .extra .deps{display:flex;flex-wrap:wrap;gap:4px}
.card .extra .dep{font-size:10px;background:rgba(245,158,11,.12);color:#fcd34d;padding:2px 6px;border-radius:3px}
.card .path{font-size:10px;color:#555;font-family:monospace;word-break:break-all}
.empty{grid-column:1/-1;text-align:center;padding:60px 20px;color:#666;font-size:14px}
</style>
</head>
<body>
<div class="sidebar">
  <h2>📂 The Agency</h2>
  <div class="cat-list" id="catList"></div>
</div>
<div class="main">
  <div class="toolbar">
    <input type="text" id="search" placeholder="搜索 Agent 名称、描述、分类、依赖…">
    <span class="stats" id="stats"></span>
  </div>
  <div class="grid" id="grid"></div>
</div>
<script>
var DATA = __DATA__;

var activeCat = "";
var query = "";
var expanded = {};

function buildCatList() {
  var cats = {};
  DATA.agents.forEach(function(a) {
    cats[a.category] = (cats[a.category] || 0) + 1;
  });
  var sorted = Object.keys(cats).sort();
  var html = '<div class="cat-item all active" data-cat=""><span>全部 Agent</span><span class="count">' + DATA.total_agents + '</span></div>';
  sorted.forEach(function(c) {
    html += '<div class="cat-item" data-cat="' + c + '"><span>' + c + '</span><span class="count">' + cats[c] + '</span></div>';
  });
  document.getElementById('catList').innerHTML = html;
  document.querySelectorAll('.cat-item').forEach(function(el) {
    el.addEventListener('click', function() {
      activeCat = el.dataset.cat;
      document.querySelectorAll('.cat-item').forEach(function(x) { x.classList.remove('active'); });
      el.classList.add('active');
      render();
    });
  });
}

function render() {
  var agents = DATA.agents.filter(function(a) {
    if (activeCat && a.category !== activeCat) return false;
    if (!query) return true;
    var q = query.toLowerCase();
    return [a.id, a.name, a.description, a.category, (a.depends_on||[]).join(' '), (a.nexus_roles||[]).join(' ')].join(' ').toLowerCase().indexOf(q) !== -1;
  });
  document.getElementById('stats').textContent = '显示 ' + agents.length + ' / ' + DATA.total_agents + ' 个 Agent';
  if (agents.length === 0) {
    document.getElementById('grid').innerHTML = '<div class="empty">没有匹配的 Agent</div>';
    return;
  }
  document.getElementById('grid').innerHTML = agents.map(function(a) {
    var deps = (a.depends_on || []).map(function(d) { return '<span class="dep">' + d + '</span>'; }).join('');
    var nexus = (a.nexus_roles || []).map(function(n) { return '<span class="tag tag-nexus">' + n + '</span>'; }).join(' ');
    var sub = a.subcategory ? ' / ' + a.subcategory : '';
    var isOpen = expanded[a.id] ? ' open' : '';
    return '<div class="card' + isOpen + '" data-id="' + a.id + '">' +
      '<div class="head">' +
        '<div class="emoji">' + a.emoji + '</div>' +
        '<div class="info">' +
          '<div class="name">' + a.name + '</div>' +
          '<div class="desc">' + a.description + '</div>' +
        '</div>' +
      '</div>' +
      '<div class="meta">' +
        '<span class="tag tag-cat">' + a.category + sub + '</span>' +
        nexus +
      '</div>' +
      '<div class="extra">' +
        (deps ? '<div class="label">依赖 (depends_on)</div><div class="deps">' + deps + '</div>' : '') +
        '<div class="label">文件路径</div><div class="path">' + a.path + '</div>' +
      '</div>' +
    '</div>';
  }).join('');
  document.querySelectorAll('.card').forEach(function(el) {
    el.addEventListener('click', function() {
      var id = el.dataset.id;
      if (expanded[id]) { delete expanded[id]; } else { expanded[id] = true; }
      el.classList.toggle('open');
    });
  });
}

document.getElementById('search').addEventListener('input', function() {
  query = this.value;
  render();
});

buildCatList();
render();
</script>
</body>
</html>"""


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Build agent-browser.html")
    parser.add_argument("--out", default=str(REPO / "agent-browser.html"),
                        help="Output path (default: repo-root/agent-browser.html)")
    args = parser.parse_args()

    index_path = REPO / "AGENTS.json"
    if not index_path.exists():
        print("ERROR: AGENTS.json not found. Run scripts/generate-index.py first.")
        sys.exit(1)

    data = json.loads(index_path.read_text(encoding="utf-8"))
    del data["generated"]

    html = HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False))

    out = Path(args.out)
    out.write_text(html, encoding="utf-8")
    print(f"Built {out} ({data['total_agents']} agents, {data['total_categories']} categories)")


if __name__ == "__main__":
    main()
