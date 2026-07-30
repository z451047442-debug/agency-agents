#!/usr/bin/env python3
"""Batch-populate new metadata fields (tags, keywords, complexity, estimated_duration).

Auto-population logic:
  - tags:         category name + key concepts from body section headers (3-5)
  - keywords:     meaningful terms from description + name + Identity section (3-5)
  - complexity:   inferred from role title (director/chief/VP/etc -> high,
                  manager/architect/lead -> medium, else low)
  - duration:     inferred from complexity (high->4-8h, medium->2-4h, low->1-2h)

Usage:
    python scripts/batch-add-metadata.py --dry-run --field all
    python scripts/batch-add-metadata.py --field tags --category engineering
    python scripts/batch-add-metadata.py --field all --verbose
"""

import argparse
import re

from _shared import atomic_write
from _shared.discovery import discover_agents
from _shared.frontmatter import get_body, get_field, get_frontmatter_text

# Complexity inference patterns
HIGH_COMPLEXITY = re.compile(
    r"\b(director|chief|president|vp[-_]|ceo|cto|cfo|ciso|coo|"
    r"c-suite|c.level|head.of|general.manager|gm[-_])\b",
    re.IGNORECASE,
)
MEDIUM_COMPLEXITY = re.compile(
    r"\b(manager|coordinator|architect|lead|senior|strategist|"
    r"supervisor|principal|team[._ ]lead|scrum[._ ]master)\b",
    re.IGNORECASE,
)

# English stop words for keyword filtering
STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "as", "is", "was", "are",
    "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "can", "could", "should",
    "may", "might", "shall", "about", "into", "over", "after",
    "before", "between", "under", "above", "below", "this", "that",
    "these", "those", "it", "its", "you", "your", "they", "them",
    "their", "we", "our", "he", "she", "his", "her", "not", "no",
    "nor", "so", "if", "then", "than", "too", "very", "just",
    "also", "more", "some", "any", "each", "every", "all", "both",
    "few", "most", "other", "such", "only", "own", "same", "new",
    "one", "two", "who", "whom", "which", "what", "when", "where",
    "why", "how", "use", "used", "using", "based", "via",
})


# ---------------------------------------------------------------------------
# Keyword / tag extraction helpers
# ---------------------------------------------------------------------------

def _split_and_clean(text: str) -> list[str]:
    """Split text by common delimiters, yield cleaned non-stop-word tokens >=3 chars."""
    results = []
    seen: set[str] = set()
    for part in re.split(r"[/,、;:\s|()\[\]{}]+", text):
        part = part.strip().strip("「」『』""''【】")  # noqa: B005  # intentional set-of-chars strip
        if not part or len(part) < 2:
            continue
        # Skip pure-English stop words (allow CJK and mixed)
        if re.match(r"^[a-zA-Z]+$", part) and part.lower() in STOP_WORDS:
            continue
        # Skip digit-only tokens
        if re.match(r"^[0-9.]+$", part):
            continue
        key = part.lower()
        if key not in seen:
            seen.add(key)
            results.append(part)
    return results


def extract_tags(category: str, body: str) -> list[str]:
    """Extract 3-5 tags from category name and body section headers."""
    tags: list[str] = []
    seen: set[str] = set()

    def add(t: str) -> None:
        t = t.strip()
        if not t or len(t) < 2:
            return
        key = t.lower()
        if key not in seen:
            seen.add(key)
            tags.append(t)

    add(category)

    # Extract domain-specific nouns from section headers
    section_header_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    for match in section_header_pattern.finditer(body):
        header = match.group(1).strip()
        # Remove emoji and special chars
        header_clean = re.sub(r"[^\w\s/&-]", " ", header)
        for word in header_clean.split():
            word = word.strip()
            if len(word) >= 4 and word.lower() not in STOP_WORDS:
                add(word)

    # If still too few, extract from bullet points / bold terms in first 1000 chars
    if len(tags) < 3:
        for match in re.finditer(r"\*\*([^*]+)\*\*", body[:1000]):
            for part in _split_and_clean(match.group(1)):
                if len(part) >= 3:
                    add(part)

    return tags[:5]


def extract_keywords(description: str, name: str, body: str) -> list[str]:
    """Extract 3-5 meaningful keywords from description, name, and Identity section."""
    keywords: list[str] = []
    seen: set[str] = set()

    def add(kw: str) -> None:
        kw = kw.strip().strip(":;,.")
        if not kw or len(kw) < 2:
            return
        if re.match(r"^[0-9.]+$", kw):
            return
        if re.match(r"^[a-zA-Z]+$", kw) and kw.lower() in STOP_WORDS:
            return
        key = kw.lower()
        if key not in seen:
            seen.add(key)
            keywords.append(kw)

    # From name and description
    for source in (name, description):
        for part in _split_and_clean(source):
            add(part)

    # From Identity section headers
    identity_match = re.search(
        r"##\s+.*?(?:identity|memory|角色|身份|personality)",
        body,
        re.IGNORECASE,
    )
    if identity_match:
        start = identity_match.start()
        snippet = body[start : start + 600]
        for term_match in re.finditer(r"\*\*([^*]+)\*\*", snippet):
            for part in _split_and_clean(term_match.group(1)):
                if len(part) >= 3:
                    add(part)

    # If still too few, extract from section headers
    if len(keywords) < 3:
        for match in re.finditer(r"^##\s+(.+)$", body, re.MULTILINE):
            for part in _split_and_clean(match.group(1)):
                if len(part) >= 3:
                    add(part)

    return keywords[:5]


# ---------------------------------------------------------------------------
# Complexity / duration inference
# ---------------------------------------------------------------------------

def infer_complexity(agent_id: str, name: str, description: str) -> str:
    """Infer complexity from role title in the agent id, name, or description."""
    text = f"{agent_id} {name} {description}"
    if HIGH_COMPLEXITY.search(text):
        return "high"
    if MEDIUM_COMPLEXITY.search(text):
        return "medium"
    return "low"


def infer_duration(complexity: str) -> str:
    """Map complexity tier to estimated duration."""
    mapping = {
        "high": "4-8h",
        "medium": "2-4h",
        "low": "1-2h",
    }
    return mapping.get(complexity, "1-2h")


# ---------------------------------------------------------------------------
# Frontmatter manipulation
# ---------------------------------------------------------------------------

def has_field(field: str, fm_text: str) -> bool:
    """Check if a YAML field already exists in the frontmatter."""
    return bool(re.search(rf"^{re.escape(field)}:", fm_text, re.MULTILINE))


def insert_fields(
    fm_text: str,
    new_fields: list[tuple[str, str | list[str]]],
) -> tuple[str, bool, list[str]]:
    """Insert new fields into frontmatter before ``depends_on`` (if it exists),
    otherwise before the closing ``---``.

    Returns (new_fm_text, was_modified, list_of_inserted_field_names).
    """
    to_insert = [(n, v) for n, v in new_fields if not has_field(n, fm_text)]
    if not to_insert:
        return fm_text, False, []

    lines = fm_text.split("\n")

    # Find the insertion point
    insert_at = len(lines)  # default: end of frontmatter
    for i, line in enumerate(lines):
        if re.match(r"^depends_on:", line):
            insert_at = i
            break

    # Build result: original lines up to insertion point
    result = list(lines[:insert_at])

    # Insert the new fields
    for field_name, value in to_insert:
        if isinstance(value, list):
            result.append(f"{field_name}:")
            for item in value:
                result.append(f"  - {item}")
        else:
            result.append(f"{field_name}: {value}")

    # Append remaining original lines
    result.extend(lines[insert_at:])

    # Ensure the frontmatter ends with a trailing newline (the YAML closing
    # ``---`` must be on its own line).
    if result and result[-1] != "":
        result.append("")

    inserted = [n for n, _ in to_insert]
    return "\n".join(result), True, inserted


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch-populate new frontmatter metadata fields for all agents",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing any files",
    )
    parser.add_argument(
        "--field",
        choices=["tags", "keywords", "complexity", "duration", "all"],
        default="all",
        help="Which field(s) to populate (default: all)",
    )
    parser.add_argument(
        "--category",
        help="Only process agents in this category directory",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed per-file output",
    )
    args = parser.parse_args()

    processed = 0
    skipped = 0
    errors = 0
    already = 0

    for category, rel, filepath in discover_agents(args.category):
        try:
            content = filepath.read_text(encoding="utf-8")
        except OSError:
            errors += 1
            continue

        fm_text = get_frontmatter_text(content)
        if not fm_text:
            skipped += 1
            continue

        body = get_body(content)
        name = get_field("name", fm_text)
        description = get_field("description", fm_text)
        agent_id = filepath.stem

        # Determine which fields already exist
        has_tags = has_field("tags", fm_text)
        has_keywords = has_field("keywords", fm_text)
        has_complexity = has_field("complexity", fm_text)
        has_duration = has_field("estimated_duration", fm_text)

        tags: list[str] | None = None
        keywords: list[str] | None = None
        complexity: str | None = None
        duration: str | None = None

        f = args.field

        if f in ("all", "tags") and not has_tags:
            tags = extract_tags(category, body)

        if f in ("all", "keywords") and not has_keywords:
            keywords = extract_keywords(description, name, body)

        # Complexity is needed directly or for duration inference
        comp: str | None = None
        if has_complexity:
            comp = get_field("complexity", fm_text)
        else:
            comp = infer_complexity(agent_id, name, description)

        if f in ("all", "complexity") and not has_complexity:
            complexity = comp

        if f in ("all", "duration") and not has_duration:
            duration = infer_duration(comp)

        # If nothing new to insert, skip
        if all(v is None for v in (tags, keywords, complexity, duration)):
            already += 1
            continue

        # Build the list of field inserts
        new_fields: list[tuple[str, str | list[str]]] = []
        if tags is not None:
            new_fields.append(("tags", tags))
        if keywords is not None:
            new_fields.append(("keywords", keywords))
        if complexity is not None:
            new_fields.append(("complexity", complexity))
        if duration is not None:
            new_fields.append(("estimated_duration", duration))

        new_fm, dirty, inserted = insert_fields(fm_text, new_fields)
        if not dirty:
            already += 1
            continue

        new_content = "---" + new_fm + "\n---" + body

        if args.dry_run:
            if args.verbose:
                print(f"  WOULD UPDATE {rel} -> {inserted}")
            processed += 1
        else:
            atomic_write(filepath, new_content, newline="\n")
            if args.verbose:
                print(f"  UPDATED {rel} -> {inserted}")
            processed += 1

    print(f"\nProcessed: {processed}  Already had: {already}  "
          f"Skipped: {skipped}  Errors: {errors}")
    if args.dry_run:
        print("DRY RUN — no files modified")


if __name__ == "__main__":
    main()
