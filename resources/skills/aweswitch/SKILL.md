---
name: aweswitch
description: "Use when helping users manage aweswitch profiles — adding, editing, or switching Claude Code and Codex API configurations. 中文触发词：切换profile、添加profile、配置aweswitch、API切换、provider管理。"
---

# aweswitch

This skill covers **configuring** aweswitch profiles and applying them to settings.

## Do Not Launch

**Never run `aweswitch <profile-name>` inside this agent.** It launches an interactive agent via `execvpe`, which would nest an agent inside an agent. If the user wants to launch a profile, tell them to run it in their own terminal.

## Two Modes

aweswitch has two ways to switch profiles. This agent can only help with **Apply mode**.

### Launch mode — `aweswitch <profile>` (user only, not for this agent)

Launches a new session with isolated env. Each session is independent. User runs this themselves in a terminal. **Do not run or suggest running this inside the agent.**

### Apply mode — `aweswitch apply <profile>` (this agent can do this)

Writes profile env to `~/.claude/settings.json`. User restarts the session or uses `/model` to pick the new model. Only one profile can be active at a time. Use `aweswitch restore` to undo.

### When to recommend which

| User wants... | Recommend | Agent role |
|---|---|---|
| Switch models within a session via `/model` | Apply | Run `aweswitch apply` directly |
| A persistent default profile | Apply | Run `aweswitch apply` directly |
| Run multiple profiles side by side | Launch | Tell user to run in their terminal |
| Try a different API quickly | Launch | Tell user to run in their terminal |

### Modes don't interact

- `aweswitch <profile>` does NOT read or modify settings.json.
- `aweswitch apply <profile>` does NOT affect running sessions.

You may run these read-only commands:
- `aweswitch list`
- `aweswitch show <profile>`
- `aweswitch config path`
- `aweswitch config show`

You may also run these commands (they modify files but are non-interactive):
- `aweswitch apply <profile>` — write profile env to `~/.claude/settings.json`
- `aweswitch restore` — restore settings from backup

## Intent Router

| User intent | Domain | Approach |
|---|---|---|
| "Add a new profile", "add a codex provider" | Add Profile | Edit config file. |
| "List profiles", "what profiles do I have" | Browse | `aweswitch list` |
| "Show profile X", "what's in profile X" | Inspect | `aweswitch show <profile>` |
| "Edit profile X", "change the API key" | Edit | Edit config file directly. |
| "Delete profile X" | Remove | Edit config file directly. |
| "Set up API key for X" | Env Vars | Edit `~/.zshrc` or `~/.bashrc`. |
| "Where is the config?" | Config Path | `aweswitch config path` |
| "Show all config" | Config Show | `aweswitch config show` |
| "Switch to profile X", "launch profile X" | Launch | Tell user to run `aweswitch <profile>` in their terminal. |
| "Use /model to switch", "在session里切换模型" | Apply | `aweswitch apply <profile>`, then restart session or use `/model`. |
| "Apply profile X to settings", "写入settings" | Apply | `aweswitch apply <profile>` |
| "Restore settings from backup", "恢复settings" | Restore | `aweswitch restore` |
| "Run two profiles at the same time" | Launch | Explain: use Launch mode, different terminals. Apply mode can't do this. |
| "Switch without restarting" | Apply | Explain: use Apply mode, then `/model` in session. |

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

### Add a Profile

1. Read the config file
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

### Apply a Profile

After configuration is done, apply the profile for the user:

```bash
aweswitch apply <profile-name>
```

Then tell the user to restart their session or use `/model` to pick the new model.

To undo:

```bash
aweswitch restore
```

If the user wants to run multiple profiles in separate terminals instead, tell them to run `aweswitch <profile-name>` in their own terminal. Do not run it yourself.

## Codex Limitations

Codex profiles only switch the API source (base URL + API key), not the model. Codex works best with OpenAI's own models — using third-party providers as a relay is the common use case.

## Core Rules

1. **Do not run `aweswitch <profile>` inside the agent.** It launches an interactive sub-agent. Tell the user to run it in their own terminal.
2. **Default to apply mode.** Run `aweswitch apply <profile>` for the user. Only mention launch mode if they specifically need multiple simultaneous sessions.
3. Always read the config file before editing. Never overwrite existing profiles without checking.
4. Never hardcode API keys or tokens. Use `${VAR_NAME}` references.
5. Profile names must be unique across all provider groups. Check before adding.
6. When editing `~/.zshrc`, check for existing entries to avoid duplicates.
7. Use `aweswitch list` and `aweswitch show` to verify changes after editing.
8. If the config file does not exist, run `aweswitch config init` first.
9. Do not run `config init` if the config already exists — it will error.
