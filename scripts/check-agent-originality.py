#!/usr/bin/env python3
"""Flag agent files that substantially duplicate an existing agent.

A new agent should be genuinely new. Find-replace "re-skins" are easy to miss
in review but bloat the library. This uses entity-neutralized 8-word shingle
overlap so a swapped proper noun can't hide the copy.
"""

import argparse
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


DEFAULT_AGENT_DIRS = [
    "academic", "design", "engineering", "finance", "game-development",
    "marketing", "paid-media", "product", "project-management", "sales",
    "spatial-computing", "specialized", "strategy", "support", "testing",
]

# Proper nouns we neutralize so find-replace re-skins still score as duplicates.
ENTITY = re.compile(
    r'\b(vietnam|vietnamese|china|chinese|douyin|tiktok|korea|korean|japan|japanese|'
    r'india|indian|indonesia|indonesian|thailand|thai|philippines|filipino|brazil|'
    r'brazilian|mexico|mexican|wechat|weixin|weibo|xiaohongshu|rednote|kuaishou|'
    r'bilibili|zhihu|baidu|shopee|lazada|zalo|tokopedia|taobao|tmall|pinduoduo|'
    r'instagram|facebook|youtube|reels|shorts|linkedin|twitter|threads|snapchat)\b')


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2]
    return text


def tokens(text: str) -> list[str]:
    text = ENTITY.sub(" ", strip_frontmatter(text).lower())
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return text.split()


def shingles(words: list[str], k: int = 8) -> set[str]:
    return {" ".join(words[i : i + k]) for i in range(max(0, len(words) - k + 1))}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_agent(path: Path) -> bool:
    try:
        return path.read_text(encoding="utf-8").startswith("---")
    except OSError:
        return False


def build_corpus(agent_dirs: list[str]) -> dict[str, set[str]]:
    corpus: dict[str, set[str]] = {}
    for d in agent_dirs:
        for f in sorted(REPO.glob(f"{d}/**/*.md")):
            if is_agent(f):
                corpus[str(f.resolve())] = shingles(tokens(f.read_text(encoding="utf-8")))
    return corpus


def check_originality(
    candidate_paths: list[Path],
    corpus: dict[str, set[str]],
    fail_threshold: float = 40,
    warn_threshold: float = 20,
) -> tuple[int, list[str]]:
    """Run originality check. Returns (exit_code, report_lines)."""
    lines: list[str] = []

    cand_sh: dict[str, set[str]] = {}
    for p in candidate_paths:
        key = str(p)
        cand_sh[key] = corpus.get(key) or shingles(tokens(p.read_text(encoding="utf-8")))

    worst = 0.0
    fails: list[tuple[str, str, float]] = []
    warns: list[tuple[str, str, float]] = []

    def _rel(p: str) -> str:
        try:
            return str(Path(p).relative_to(REPO)).replace("\\", "/")
        except ValueError:
            return p

    for p in candidate_paths:
        key = str(p)
        sh = cand_sh[key]
        best_name, best_score = "", 0.0

        for cf, csh in corpus.items():
            if cf == key:
                continue
            s = jaccard(sh, csh)
            if s > best_score:
                best_name, best_score = _rel(cf), s

        for op_key, op_sh in cand_sh.items():
            if op_key == key:
                continue
            s = jaccard(sh, op_sh)
            if s > best_score:
                best_name, best_score = _rel(op_key) + " (same change set)", s

        pct = best_score * 100
        worst = max(worst, pct)
        tag = "OK   "
        if pct >= fail_threshold:
            tag = "FAIL "
            fails.append((_rel(key), best_name, pct))
        elif pct >= warn_threshold:
            tag = "WARN "
            warns.append((_rel(key), best_name, pct))

        lines.append(f"  [{tag}] {pct:5.1f}%  {_rel(key)}")
        if best_name:
            lines.append(f"            closest: {best_name}")

    lines.append("")
    lines.append(
        f"Thresholds: WARN >= {warn_threshold:.0f}%, FAIL >= {fail_threshold:.0f}%  "
        "(existing-library baseline max ~1.5%)"
    )

    if fails:
        lines.append("")
        lines.append(f"FAILED: {len(fails)} agent(s) substantially duplicate existing content:")
        for name, match, pct in fails:
            lines.append(f"  - {name}  ~{pct:.0f}% like  {match}")
        lines.append("")
        lines.append("A new agent should be genuinely new. If this is intended market/platform")
        lines.append("localization, make the body distinct (different platforms, tactics, examples)")
        lines.append("rather than a find-replace of an existing agent.")
        return 1, lines

    if warns:
        lines.append(f"\n{len(warns)} warning(s) — review for overlap, but not blocking.")
    lines.append("\nPASSED")
    return 0, lines


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Flag agent files that substantially duplicate an existing agent"
    )
    parser.add_argument(
        "files", nargs="*",
        help="Agent .md files to check (default: audit all)",
    )
    parser.add_argument(
        "--fail-threshold", type=float, default=40,
        help="Similarity %% above which to fail (default: 40)",
    )
    parser.add_argument(
        "--warn-threshold", type=float, default=20,
        help="Similarity %% above which to warn (default: 20)",
    )
    args = parser.parse_args()

    if args.files:
        candidates = []
        for a in args.files:
            p = Path(a).resolve() if os.path.isabs(a) else Path.cwd().joinpath(a).resolve()
            if not p.is_file():
                print(f"  skip (not found): {a}")
                continue
            if not is_agent(p):
                try:
                    rel = str(p.relative_to(REPO)).replace("\\", "/")
                except ValueError:
                    rel = str(p)
                print(f"  skip (no frontmatter, not an agent): {rel}")
                continue
            candidates.append(p)
    else:
        corpus = build_corpus(DEFAULT_AGENT_DIRS)
        candidates = [Path(p) for p in corpus]
        exit_code, lines = check_originality(
            candidates, corpus, args.fail_threshold, args.warn_threshold
        )
        print("\n".join(lines))
        sys.exit(exit_code)

    if not candidates:
        print("No agent files to check.")
        sys.exit(0)

    corpus = build_corpus(DEFAULT_AGENT_DIRS)
    exit_code, lines = check_originality(
        candidates, corpus,
        fail_threshold=args.fail_threshold,
        warn_threshold=args.warn_threshold,
    )
    print("\n".join(lines))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
