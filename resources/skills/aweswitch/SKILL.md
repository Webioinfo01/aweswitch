---
name: aweswitch
description: "Use when helping users manage aweswitch profiles — adding, editing, or switching Claude Code and Codex API configurations. 中文触发词：切换profile、添加profile、配置aweswitch、API切换、provider管理。"
---

# aweswitch

Use `aweswitch` CLI directly. Edit config files only when the CLI cannot handle the task.

## Intent Router

| User intent | Domain | Approach |
|---|---|---|
| "Add a new profile", "add a codex provider" | Add Profile | Interactive: `aweswitch add`. Bulk/custom: edit config file. |
| "Switch to profile X" | Launch | `aweswitch <profile-name>` |
| "List profiles", "what profiles do I have" | Browse | `aweswitch list` |
| "Show profile X", "what's in profile X" | Inspect | `aweswitch show <profile>` |
| "Edit profile X", "change the API key" | Edit | Edit config file directly. |
| "Delete profile X" | Remove | Edit config file directly. |
| "Set up API key for X" | Env Vars | Edit `~/.zshrc` or `~/.bashrc`. |
| "Where is the config?" | Config Path | `aweswitch config path` |
| "Show all config" | Config Show | `aweswitch config show` |
| "Open config in editor" | Config Edit | `aweswitch config edit` |

## Config Location

Default: `~/.config/aweswitch/config.json`
Override: `AWESWITCH_CONFIG` env var.

Always read the config file before modifying it.

## Config Structure

```json
{
  "profiles": {
    "claude": {
      "<profile-name>": {
        "env": {
          "ANTHROPIC_BASE_URL": "<url>",
          "ANTHROPIC_AUTH_TOKEN": "${ENV_VAR_NAME}",
          "ANTHROPIC_MODEL": "<model-id>",
          "ANTHROPIC_DEFAULT_HAIKU_MODEL": "<optional>",
          "ANTHROPIC_DEFAULT_SONNET_MODEL": "<optional>"
        }
      }
    },
    "codex": {
      "<profile-name>": {
        "env": {
          "OPENAI_BASE_URL": "<url>",
          "OPENAI_API_KEY": "${ENV_VAR_NAME}"
        }
      }
    }
  }
}
```

### Provider fields

| Field | Claude | Codex |
|-------|--------|-------|
| Base URL | `ANTHROPIC_BASE_URL` | `OPENAI_BASE_URL` |
| Auth token | `ANTHROPIC_AUTH_TOKEN` | `OPENAI_API_KEY` |
| Model | `ANTHROPIC_MODEL` | not applicable |
| Injection | `--settings` temp file | `-c` flag + env var |

### Naming convention

- Claude profiles: `cc-` prefix (e.g. `cc-glm`, `cc-xiaomi`)
- Codex profiles: `cx-` prefix (e.g. `cx-openai`, `cx-aihubmix`)

### Token references

Token values use `${VAR_NAME}` syntax. They expand from:
1. Shell environment variables (primary)
2. `~/.claude/settings.json` env section (Claude only, fallback)

Never hardcode secrets. Always use `${VAR_NAME}` references.

## Workflows

### Add a Profile (interactive)

```bash
aweswitch add
```

Prompts for provider (claude/codex), profile name, and provider-specific fields.

### Add a Profile (edit config)

1. Read the config file: `cat ~/.config/aweswitch/config.json`
2. Add the new profile under the appropriate provider key (`claude` or `codex`)
3. Use `${ENV_VAR_NAME}` for token values
4. Ensure profile name is unique across all providers
5. Validate the JSON is well-formed

### Edit a Profile

1. Read the config file
2. Locate the profile by name under its provider
3. Modify the target fields
4. Write back the file, preserving JSON formatting (2-space indent)

### Delete a Profile

1. Read the config file
2. Remove the profile entry from its provider group
3. If the provider group becomes empty, optionally remove it too
4. Write back the file

### Set Up Environment Variables

Token values reference shell variables that must be defined before launching a profile.

Shell config file location:

| Shell | File |
|-------|------|
| zsh (macOS default) | `~/.zshrc` |
| bash | `~/.bashrc` or `~/.bash_profile` |

Steps:

1. Read the shell config file
2. Check which env vars are already set (avoid duplicates)
3. Append `export VAR_NAME="value"` lines
4. Tell the user to run `source ~/.zshrc` or open a new terminal

Example:

```bash
# Claude profiles
export GLM_ANTHROPIC_AUTH_TOKEN="sk-..."
export XIAOMI_ANTHROPIC_AUTH_TOKEN="sk-..."

# Codex profiles
export OPENAI_API_KEY="sk-..."
```

### Verify Configuration

```bash
aweswitch list           # all profiles with provider and model/url
aweswitch show <name>    # one profile, secrets redacted
aweswitch config show    # full config, secrets redacted
```

### Launch a Profile

```bash
aweswitch <profile-name>                   # basic launch
aweswitch <profile-name> --extra-arg       # pass args to agent
aweswitch <profile-name> -c category -t title  # with aweshelf bookmark
```

## Codex Limitations

Codex profiles only switch the API source (base URL + API key), not the model. Codex works best with OpenAI's own models — using third-party providers as a relay is the common use case.

## Core Rules

1. Always read the config file before editing. Never overwrite existing profiles without checking.
2. Never hardcode API keys or tokens. Use `${VAR_NAME}` references.
3. Profile names must be unique across all provider groups. Check before adding.
4. When editing `~/.zshrc`, check for existing entries to avoid duplicates.
5. Use `aweswitch list` and `aweswitch show` to verify changes after editing.
6. If the config file does not exist, run `aweswitch config init` first.
7. Do not run `config init` if the config already exists — it will error.
