# Contributing Translations (i18n)

The Agency supports localizing agent names and descriptions so that users of AI coding tools see agent names in their preferred language. This guide explains how to add or improve translations.

## File overview

| File | Purpose |
|------|---------|
| `scripts/i18n/agent-names-zh.json` | Translation mapping (source of truth) |
| `scripts/i18n/localize-agents.py` | Patches installed agent files with translations |
| `scripts/i18n/check-i18n.py` | Reports coverage stats and encoding issues |

## JSON mapping format

Each language has a file named `agent-names-{lang}.json` (e.g., `agent-names-zh.json` for Chinese). The file maps an English agent `name` field to its translated `name` and `description`:

```json
{
  "Frontend Developer": {
    "name": "前端开发工程师",
    "description": "专注现代 Web 技术、React/Vue/Angular 框架、UI 实现与性能优化的前端专家"
  },
  "Security Engineer": {
    "name": "安全工程师",
    "description": "威胁建模、安全代码审查与应用安全架构专家"
  }
}
```

- **Key**: The exact English `name` value from the agent's YAML frontmatter.
- **`name`**: The translated display name.
- **`description`**: The translated description (one sentence).

## Adding translations for a new language

1. Create `scripts/i18n/agent-names-{lang}.json` (use the [ISO 639-1 code](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes), e.g., `ja` for Japanese, `ko` for Korean).

2. Generate a template of all untranslated agents:

   ```bash
   python scripts/i18n/check-i18n.py --lang ja --template > missing-ja.json
   ```

   This outputs a JSON object with every agent that needs translation, ready to fill in.

3. Fill in the `"name"` and `"description"` values for each entry in the generated file.

4. Copy your completed translations into `scripts/i18n/agent-names-{lang}.json`.

5. Run the check tool to verify coverage:

   ```bash
   python scripts/i18n/check-i18n.py --lang ja
   ```

## Adding more translations to an existing language

1. Check what's missing:

   ```bash
   python scripts/i18n/check-i18n.py --lang zh
   ```

   This lists untranslated agents grouped by category.

2. Create a template for the missing entries only:

   ```bash
   python scripts/i18n/check-i18n.py --lang zh --template > new-entries.json
   ```

3. Fill in the translations and merge them into `scripts/i18n/agent-names-zh.json`.

4. Re-run the check to confirm coverage improved:

   ```bash
   python scripts/i18n/check-i18n.py --lang zh
   ```

## Running localization after translating

After adding translations, apply them to installed agents:

```bash
# Default: patches ~/.github/agents and ~/.copilot/agents
python scripts/i18n/localize-agents.py

# Preview first (dry-run)
python scripts/i18n/localize-agents.py --dry-run

# Process the repo source files instead
python scripts/i18n/localize-agents.py --source

# Custom target directories
python scripts/i18n/localize-agents.py ~/my-agents

# Use a different language
python scripts/i18n/localize-agents.py --lang ja
```

## CI validation

The CI pipeline (`lint-agents.yml`) runs `check-i18n.py --strict` to enforce:

- No agents with invalid UTF-8 encoding
- No orphaned mapping entries (entries with no matching agent)

## Editing tips

- Keep descriptions to one sentence (10--500 characters).
- Use the agent's English `name` as it appears in the YAML frontmatter (the exact text, including punctuation).
- If an agent is renamed, update both the key and the translated values.
- Run `python scripts/i18n/check-i18n.py --lang <lang>` as a quick sanity check during editing.
- The JSON file must be valid UTF-8. The check tool validates encoding for all agent files.
- After adding new translations, the `localize-agents.py` script will pick them up on the next run without any additional configuration.
