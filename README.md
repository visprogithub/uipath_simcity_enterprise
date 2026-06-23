# Light Enterprise Brand Kit

A repo-ready, agent-friendly brand kit for Claude Code, Codex, and other coding agents.

This version is intentionally lighter, softer, and more inclusive than a typical dark enterprise system. It keeps enterprise credibility, but avoids the heavy, masculine feel of navy-heavy palettes.

## Best use

Use this as a shared `/.brand/` folder in any repo that needs consistent UI direction.

Recommended structure:

- `BRAND.md`. Overall design system rules.
- `THEMES.md`. Theme catalog and selection guide.
- `CLAUDE.md`. Claude Code instructions with a built-in theme picking workflow.
- `AGENTS.md`. Generic coding agent contract.
- `prompts/theme-picker.md`. Reusable prompt that asks the human to choose a theme.
- `prompts/implementation-prompt.md`. Reusable build prompt for agents.
- `tokens/design-tokens.json`. Machine-readable tokens for all themes.
- `tokens/theme-map.css`. CSS variables for all themes.
- `guides/`. Layout, component, motion, and accessibility rules.
- `skills/theme-selector-skill.md`. A skill-style instruction file you can drop into an agent context.

## Included themes

1. Blush & Rose
2. Lavender & Sage
3. Sky & Sand
4. Peach & Mint
5. Soft Neutrals

## Recommended default

Use **Lavender & Sage** as the default if no preference is given. It feels modern, light, calm, and polished, while still reading as enterprise.

## Setup options

### Option 1. Best overall. Multi-document folder

Put the whole kit into `/.brand/` and reference it from the root `CLAUDE.md` and `AGENTS.md`.

### Option 2. Lightweight. Just the prompt files

If you want minimal overhead, use:

- `CLAUDE.md`
- `BRAND.md`
- `THEMES.md`
- `prompts/theme-picker.md`

### Option 3. Skill-style setup

If your workflow supports skills or reusable agent capabilities, use `skills/theme-selector-skill.md` as the behavior contract, but still keep the docs folder as the source of truth.

## Suggested repo root files

Root `CLAUDE.md`:

```md
Before making UI changes, read:
- .brand/CLAUDE.md
- .brand/BRAND.md
- .brand/THEMES.md
- .brand/guides/layout.md
- .brand/guides/components.md
- .brand/guides/motion.md
- .brand/guides/accessibility.md
- .brand/tokens/design-tokens.json
```

Root `AGENTS.md`:

```md
All UI work must follow `.brand/AGENTS.md`, `.brand/BRAND.md`, `.brand/THEMES.md`, and `.brand/tokens/design-tokens.json`.
```
