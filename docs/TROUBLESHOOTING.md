# 🔧 Troubleshooting Guide

Common issues when installing, converting, or contributing agents — and how to fix them.

---

## Installation

### "bash: scripts/install.sh: No such file or directory"

You're not in the repo root. Run from the top-level directory:

```bash
cd /path/to/agency-agents
./scripts/install.sh
```

### "bash: command not found" (Windows)

You need a bash environment. Options:

| Solution | Recommendation |
|----------|---------------|
| **Git Bash** (bundled with Git for Windows) | Best for most users |
| **WSL** (Windows Subsystem for Linux) | Best for heavy use |
| **Python scripts** | Cross-platform fallback (`python scripts/convert.py`, `python scripts/lint-agents.py`) |

### "permission denied: ./scripts/install.sh"

The script isn't executable. Fix it:

```bash
chmod +x scripts/install.sh
```

Or run with bash explicitly:

```bash
bash scripts/install.sh
```

### "integrations/ directory is missing or empty"

You need to run conversion first. Claude Code reads `.md` files directly and doesn't need this step, but all other tools do:

```bash
# Bash (Linux/macOS/Git Bash)
./scripts/convert.sh

# Python (cross-platform, Windows compatible)
python scripts/convert.py
```

Then retry: `./scripts/install.sh --tool cursor` (or your tool).

### "Tool not detected" in installer

The installer auto-detects tools by checking config directories. If detection fails:

1. Verify the tool is installed: run it once so it creates its config directory
2. Use `--path` to specify the directory manually:
   ```bash
   ./scripts/install.sh --tool claude-code --path /custom/path/to/agents
   ```
3. Check `tools.json` for the expected install directory

### Symlink doesn't work on Windows

The `--link` flag creates symlinks. On Windows this requires:
- **Developer Mode** enabled (Settings → For Developers)
- OR running as Administrator
- OR using Git Bash with `MSYS=winsymlinks:nativestrict` set

Fallback: omit `--link` to copy files instead.

---

## Conversion

### "convert.sh: command not found" or converter errors

Each converter in `convert.sh` generates tool-specific files. If a specific converter fails:

```bash
# Run a single converter to isolate the issue
./scripts/convert.sh --tool cursor

# Use Python version for better error messages
python scripts/convert.py --tool cursor
```

### "AGENTS.json is out of date" (CI or local check)

The index is stale. Regenerate it:

```bash
./scripts/generate-index.sh
```

This scans all agent `.md` files and rebuilds the JSON catalog. CI requires this to be current.

---

## Agent Validation (Lint)

### "ERROR: missing required frontmatter field: name/description/emoji/color"

Your agent file's YAML frontmatter (the `---` block at the top) is missing a required field.

```yaml
---
name: "My Agent Name"       # required: 1-120 chars
description: "What it does"  # required: 10-500 chars
emoji: 🎯                    # required: 1-8 chars
color: cyan                  # required: named color or #RRGGBB
---
```

### "WARN: file is under 100 words"

The agent content is too thin. Add more detail to body sections — expand the workflow steps, add code examples, flesh out the communication style.

### "WARN: file exceeds 10 KB"

The file is unusually large. Consider:
- Moving lengthy code examples to referenced external files
- Trimming redundant workflow steps
- Moving background/context paragraphs to a README if the agent had one

### "WARN: missing recommended section: Identity / Core Mission / Critical Rules"

These section headers are checked by fuzzy matching. Make sure you have headings containing these keywords:

- `## 🧠 Your Identity` or `## Identity`
- `## 🎯 Your Core Mission` or `## Mission`
- `## 🚨 Critical Rules` or `## Rules`

### "CRLF line endings detected"

Windows line endings (`\r\n`) can cause issues. Convert to LF:

```bash
# Git can handle this automatically
git config core.autocrlf input

# Fix existing files
dos2unix path/to/agent.md
```

Or configure your editor to use LF line endings for `.md` files.

---

## CI Failures

### Originality check fails (similarity > 40%)

Your agent is too similar to an existing one. The check neutralizes proper nouns (country names, platform names) before comparison, so "Marketing for Japan" vs "Marketing for Brazil" would still flag if the structure is identical.

**Fix**: Differentiate the agent with genuinely different workflows, examples, and tactics — not just find-replace of names.

### "AGENTS.json is out of date" in CI

You added or modified an agent but forgot to regenerate the index. Run:

```bash
./scripts/generate-index.sh
git add AGENTS.json
git commit --amend  # or create a new commit
```

### "integrations/ is out of sync" in CI

The converted files don't match current source agents. Run:

```bash
./scripts/convert.sh
```

Note: `integrations/` is `.gitignore`d and should not be committed.

---

## Agent Creation

### "Invalid category" when using create-agent.sh

Check available categories:

```bash
./scripts/search-agents.sh --list-categories
```

If you need a new category, the script will prompt you to confirm. New categories must also be added to `divisions.json`.

### Emoji validation fails

The emoji field accepts 1-8 characters. Common issues:
- Using a multi-codepoint emoji that exceeds 8 chars (e.g., some flag emojis)
- Using an HTML entity instead of the actual emoji character

Use the actual emoji character, not `:shortcode:` syntax.

---

## Platform-Specific Notes

### Windows (Git Bash)

- Use forward slashes in paths: `./scripts/install.sh`, not `.\scripts\install.sh`
- If `python` isn't found, try `python3` or `py`
- Symlink mode (`--link`) requires Developer Mode

### macOS

- macOS ships with bash 3.2 (zsh is default since Catalina). Scripts require bash 3.2+. Run with `bash scripts/install.sh` if your default shell is zsh.
- `realpath` is not available by default. Install via `brew install coreutils` or use Python scripts as fallback.

### Linux

- Most distributions ship compatible bash. If you get "bad substitution" errors, your bash is too old — upgrade to 3.2+ or use Python scripts.

---

## Still Stuck?

1. Search [existing issues](https://github.com/z451047442-debug/agency-agents/issues) for your error message
2. Open a [bug report](https://github.com/z451047442-debug/agency-agents/issues/new?template=bug-report.yml) with:
   - Your OS and shell version (`bash --version` or `python --version`)
   - The exact command you ran
   - The full error output
   - What you've already tried
