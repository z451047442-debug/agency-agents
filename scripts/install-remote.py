#!/usr/bin/env python3
"""Remote installer — install agents directly from GitHub without cloning.

Usage:
    python install-remote.py --tool claude-code --division engineering

Download this script first and inspect it; do not pipe a remote script directly
into an interpreter without verification.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from urllib.request import urlopen

DEFAULT_REPO = "z451047442-debug/agency-agents"
DEFAULT_BRANCH = "main"

_REPO_RE = re.compile(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$")
_BRANCH_RE = re.compile(r"^[a-zA-Z0-9._/-]+$")
# Four shipped agents use a leading underscore (_solution-*), so allow it.
_AGENT_ID_RE = re.compile(r"^[a-z0-9_][a-z0-9_-]*$")
MAX_AGENT_BYTES = 1_000_000


def log(msg: str) -> None:
    print(f"  {msg}")


def _open_url(url: str, timeout: int = 30):
    """Open an HTTPS URL, rejecting file/custom schemes before urlopen."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"refusing non-HTTPS URL: {url}")
    return urlopen(url, timeout=timeout)  # nosec B310 - scheme/host validated above


def _load_checksums(path: str | None) -> dict[str, str] | None:
    """Load an optional local JSON manifest of {repo_path: sha256}."""
    if not path:
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("checksum manifest must be a JSON object")
    return {str(key): str(value).lower() for key, value in data.items()}


def is_safe_agent_id(aid: str) -> bool:
    """Reject path traversal and non-conforming agent IDs."""
    return bool(_AGENT_ID_RE.match(aid)) and ".." not in aid


def install_agents(raw_base: str, tool: str, divisions: set[str] | None,
                   agent_filter: str | None,
                   checksums: dict[str, str] | None = None) -> int:
    if tool != "claude-code":
        raise ValueError(
            f"--tool '{tool}' is not supported. Remote install only supports claude-code."
        )
    dest = Path.home() / ".claude" / "agents"
    dest.mkdir(parents=True, exist_ok=True)

    # Fetch AGENTS.json
    log(f"Fetching {raw_base}/AGENTS.json")
    with _open_url(f"{raw_base}/AGENTS.json", timeout=30) as resp:
        data = json.loads(resp.read().decode())
    agents = data.get("agents", [])
    log(f"{len(agents)} agents in index")

    # For claude-code: download and save each agent
    count = 0
    failures = 0
    for agent in agents:
        aid = agent["id"]
        cat = agent["category"]

        if not is_safe_agent_id(aid):
            log(f"  skip {aid}: invalid agent id (rejected for safety)")
            continue
        if divisions and cat not in divisions:
            continue
        if agent_filter and agent_filter != aid:
            continue

        # Validate the index-supplied path before building the download URL:
        # reject traversal (".."), absolute paths, and root-relative paths.
        path = agent.get("path", "")
        if (not path
                or path.startswith("/")
                or ".." in path.split("/")
                or PurePosixPath(path).name != f"{aid}.md"):
            log(f"  skip {aid}: unsafe path '{path}' in index (rejected for safety)")
            continue

        url = f"{raw_base}/{path}"
        dest_file = (dest / f"{aid}.md").resolve()
        if dest_file.parent != dest.resolve():
            log(f"  skip {aid}: path traversal detected")
            continue

        try:
            with _open_url(url, timeout=30) as resp:
                payload = resp.read(MAX_AGENT_BYTES + 1)
            if len(payload) > MAX_AGENT_BYTES:
                raise ValueError(f"file exceeds {MAX_AGENT_BYTES} bytes")
            try:
                text = payload.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("downloaded file is not valid UTF-8") from exc
            if not text.startswith("---") or not re.search(r"^name:\s*\S", text, re.MULTILINE):
                raise ValueError("downloaded file is missing YAML frontmatter/name")
            if checksums is not None:
                expected = checksums.get(path)
                if not expected:
                    raise ValueError("path is missing from the checksum manifest")
                actual = hashlib.sha256(payload).hexdigest()
                if actual != expected:
                    raise ValueError("SHA256 checksum mismatch")
            dest_file.write_bytes(payload)
            count += 1
            if count % 500 == 0:
                log(f"  {count}/{len(agents)}...")
        except Exception as e:
            failures += 1
            log(f"  skip {aid}: {e}")

    if failures:
        print(f"Error: {failures} agent(s) failed to install; rerun the command.",
              file=sys.stderr)
        return -failures
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Install agency agents remotely")
    parser.add_argument("--tool", default="claude-code")
    parser.add_argument("--division", help="Comma-separated divisions")
    parser.add_argument("--agent", help="Single agent ID")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--sha256-manifest",
                        help="Local JSON manifest mapping agent path to SHA256 (from a trusted channel)")
    args = parser.parse_args()

    if not _REPO_RE.match(args.repo):
        print(f"Error: --repo '{args.repo}' has invalid format (expected owner/name)",
              file=sys.stderr)
        sys.exit(1)
    if not _BRANCH_RE.match(args.branch):
        print(f"Error: --branch '{args.branch}' contains invalid characters", file=sys.stderr)
        sys.exit(1)

    raw_base = f"https://raw.githubusercontent.com/{args.repo}/{args.branch}"
    divisions = {d.strip() for d in args.division.split(",")} if args.division else None
    try:
        checksums = _load_checksums(args.sha256_manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: cannot load checksum manifest: {exc}", file=sys.stderr)
        sys.exit(1)

    print("The Agency — Remote Install")
    print(f"  Source: github.com/{args.repo}")

    try:
        n = install_agents(raw_base, args.tool, divisions, args.agent,
                           checksums=checksums)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    if n < 0:
        sys.exit(1)
    print(f"\nDone. {n} agents -> ~/.claude/agents/")


if __name__ == "__main__":
    main()
