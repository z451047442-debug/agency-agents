"""One-shot: convert CRLF line endings to LF across agent .md files.

Run: python scripts/fix-crlf.py
Only touches top-level category agent files (excludes docs/tests/generated dirs).
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXCLUDE = {".git", "env", "integrations", "_archive", "docs", "tests", "examples",
           "schemas", "nexus-demo", "nexus-projects", ".claude", ".agents",
           ".superpowers", ".swarm", ".mypy_cache", ".pytest_cache", ".ruff_cache"}

converted = 0
for p in ROOT.iterdir():
    if not p.is_dir() or p.name in EXCLUDE:
        continue
    for f in p.rglob("*.md"):
        data = f.read_bytes()
        if b"\r\n" in data:
            f.write_bytes(data.replace(b"\r\n", b"\n"))
            converted += 1
            print(f"LF: {f.relative_to(ROOT)}")

print(f"CONVERTED: {converted} files")
