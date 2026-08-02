---
name: aweswitch
description: "Use when helping users manage aweswitch profiles — adding, editing, or switching Claude Code, Codex, and OpenCode API configurations. 中文触发词：切换profile、添加profile、配置aweswitch、API切换、provider管理。"
---

# aweswitch

This skill covers **configuring** aweswitch profiles and applying them to settings.

## Do Not Launch

**Never run `aweswitch <profile-name>` inside this agent.** It launches an interactive agent via `execvpe`, which would nest an agent inside an agent. If the user wants to launch a profile, tell them to run it in their own terminal.

## Two Modes

aweswitch has two ways to switch profiles. This agent can only help with **Apply mode** for Claude profiles.

### Launch mode — `aweswitch <profile>` (user only, not for this agent)

Launches a new session with isolated env. Each session is independent. User runs this themselves in a terminal. **Do not run or suggest running this inside the agent.**

This is the only mode available for **Codex** and **OpenCode** profiles.

### Apply mode — `aweswitch apply <profile>` (this agent can do this)

Writes profile env to `~/.claude/settings.json`. User restarts the session or uses `/model` to pick the new model. Only one profile can be active at a time. Use `aweswitch restore` to undo.

**Apply mode only works for Claude profiles.** For Codex and OpenCode profiles, tell the user to use Launch mode in their own terminal.

### When to recommend which

| User wants... | Recommend | Agent role |
|---|---|---|
| Switch models within a session via `/model` | Apply (Claude only) | Run `aweswitch apply` directly |
| A persistent default profile | Apply (Claude only) | Run `aweswitch apply` directly |
| Run multiple profiles side by side | Launch | Tell user to run in their terminal |
| Try a different API quickly | Launch | Tell user to run in their terminal |
| Use OpenCode with a profile | Launch | Tell user to run in their terminal |

### Mode availability by provider

| Provider | Apply mode (`aweswitch apply`) | Launch mode (`aweswitch <profile>`) |
|----------|-------------------------------|-------------------------------------|
| Claude | supported | supported |
| Codex | not supported | supported |
| OpenCode | not supported | supported |

You may run these read-only commands:
- `aweswitch list`
- `aweswitch show <profile>`
- `aweswitch config path`
- `aweswitch config show`

You may also run these commands (they modify files but are non-interactive):
- `aweswitch apply <profile>` — write Claude profile env to `~/.claude/settings.json`
- `aweswitch restore` — restore settings from backup
- `setx VAR_NAME "value"` (Windows only) — persist a user environment variable so both cmd and PowerShell see it

**Note:** `aweswitch apply` only works for Claude profiles. Do not attempt to run `aweswitch apply` for Codex or OpenCode profiles.

## Intent Router

| User intent | Domain | Approach |
|---|---|---|
| "Add a new profile", "add a codex provider" | Add Profile | Edit config file. |
| "Add an opencode profile" | Add Profile | Edit config file; use `opencode` provider group. |
| "List profiles", "what profiles do I have" | Browse | `aweswitch list` |
| "Show profile X", "what's in profile X" | Inspect | `aweswitch show <profile>` |
| "Edit profile X", "change the API key" | Edit | Edit config file directly. |
| "Delete profile X" | Remove | Edit config file directly. |
| "Set up API key for X" | Env Vars | Edit `~/.zshrc` or `~/.bashrc`; on Windows run `setx`. |
| "Where is the config?" | Config Path | `aweswitch config path` |
| "Show all config" | Config Show | `aweswitch config show` |
| "Switch to profile X", "launch profile X" | Launch | Tell user to run `aweswitch <profile>` in their terminal. |
| "Launch opencode profile" | Launch | Tell user to run `aweswitch oc-<name> [model]` in their terminal. |
| "Use /model to switch", "在session里切换模型" | Apply | `aweswitch apply <profile>` (Claude only). |
| "Apply profile X to settings", "写入settings" | Apply | `aweswitch apply <profile>` (Claude only). |
| "Restore settings from backup", "恢复settings" | Restore | `aweswitch restore` |
| "Run two profiles at the same time" | Launch | Explain: use Launch mode, different terminals. Apply mode can't do this. |
| "Switch without restarting" | Apply | Explain: use Apply mode, then `/model` in session (Claude only). |

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
    },
    "opencode": {
      "<profile-name>": {
        "env": {
          "OPENCODE_BASE_URL": "<url>",
          "OPENCODE_API_KEY": "${ENV_VAR_NAME}",
          "OPENCODE_NAME": "<display-name>",
          "OPENCODE_MODEL": "<model-id-or-list>"
        }
      }
    }
  }
}
```

### Provider fields

| Field | Claude | Codex | OpenCode |
|-------|--------|-------|----------|
| Base URL | `ANTHROPIC_BASE_URL` | `OPENAI_BASE_URL` | `OPENCODE_BASE_URL` |
| Auth token | `ANTHROPIC_AUTH_TOKEN` | `OPENAI_API_KEY` | `OPENCODE_API_KEY` |
| Model | `ANTHROPIC_MODEL` | not applicable | `OPENCODE_MODEL` (list/dict/string) |
| Injection | `--settings` temp file | `-c` flag + env var | writes to `~/.config/opencode/opencode.json` via `{env:VAR}` |

### Naming convention

- Claude profiles: `cc-` prefix (e.g. `cc-glm`, `cc-xiaomi`)
- Codex profiles: `cx-` prefix (e.g. `cx-openai`)
- OpenCode profiles: `oc-` prefix (e.g. `oc-glm`, `oc-mimo`)

### Token references

Token values use `${VAR_NAME}` syntax in the aweswitch config. They expand from:
1. Shell environment variables (primary)
2. `~/.claude/settings.json` env section (Claude only, fallback)

**OpenCode auth key:** aweswitch writes the API key to `~/.config/opencode/opencode.json` using `{env:VAR_NAME}` syntax, so the actual key is never stored on disk. The `${VAR_NAME}` reference in the aweswitch config still expands from the shell env at launch time.

Never hardcode secrets. Always use `${VAR_NAME}` references in the aweswitch config.

## Workflows

### Add a Profile

1. Read the config file
2. Add the new profile under the appropriate provider key (`claude`, `codex`, or `opencode`)
3. Use `${ENV_VAR_NAME}` for token values
4. Ensure profile name is unique across all providers
5. Validate the JSON is well-formed

#### OpenCode profile fields

- `OPENCODE_BASE_URL` — provider API endpoint
- `OPENCODE_API_KEY` — token env var name (use `${VAR}` reference)
- `OPENCODE_NAME` — optional display name (defaults to profile name)
- `OPENCODE_MODEL` — models as comma-separated string, list, or dict mapping

```json
{
  "profiles": {
    "opencode": {
      "oc-glm": {
        "env": {
          "OPENCODE_BASE_URL": "https://open.bigmodel.cn/api/coding/paas/v4",
          "OPENCODE_API_KEY": "${GLM_ANTHROPIC_AUTH_TOKEN}",
          "OPENCODE_NAME": "Zhipu GLM",
          "OPENCODE_MODEL": ["glm-5.1", "glm-5.2"]
        }
      }
    }
  }
}
```

### Edit a Profile

1. Read the config file
2. Locate the profile by name under its provider (`claude`, `codex`, or `opencode`)
3. Modify the target fields
4. Write back the file, preserving JSON formatting (2-space indent)

### Delete a Profile

1. Read the config file
2. Remove the profile entry from its provider group
3. If the provider group becomes empty, optionally remove it too
4. Write back the file

### Set Up Environment Variables

Token values reference shell variables that must be defined before launching a profile.

Where to persist them:

| Platform | Target | Scope |
|----------|--------|-------|
| macOS (zsh) | `~/.zshrc` | all zsh shells |
| bash | `~/.bashrc` or `~/.bash_profile` | all bash shells |
| Windows | `setx` (writes user environment variables) | **cmd and PowerShell both** |
| Windows (PowerShell only) | `$PROFILE` (default: `~\Documents\PowerShell\Microsoft.PowerShell_profile.ps1`) | PowerShell only |

On Windows, prefer `setx` — it persists to the user environment (the same
place as the System Properties GUI), so both cmd and PowerShell pick it up.
Use `$PROFILE` only if the user explicitly wants PowerShell-only scope.

Steps:

1. Read the current values (shell config file, or `setx`-backed env on Windows)
2. Check which env vars are already set (avoid duplicates)
3. Set the env vars using the platform-appropriate method:
   - bash/zsh: append `export VAR_NAME="value"` to the shell config file
   - Windows: run `setx VAR_NAME "value"` (no `/M` — that requires admin and sets machine scope)
   - PowerShell-only alternative: append `$env:VAR_NAME = "value"` to `$PROFILE`
4. Tell the user to reload:
   - bash/zsh: `source ~/.zshrc` (or `~/.bashrc`), or open a new terminal
   - Windows (`setx`): open a new terminal — `setx` does not affect the current one
   - PowerShell (`$PROFILE`): `. $PROFILE`, or open a new PowerShell window

Example (bash/zsh):

```bash
# Claude / OpenCode profiles
export GLM_ANTHROPIC_AUTH_TOKEN="sk-..."
export XIAOMI_ANTHROPIC_AUTH_TOKEN="sk-..."

# Codex profiles
export OPENAI_API_KEY="sk-..."
```

Example (Windows — works in both cmd and PowerShell):

```bat
setx GLM_ANTHROPIC_AUTH_TOKEN "sk-..."
setx XIAOMI_ANTHROPIC_AUTH_TOKEN "sk-..."
setx OPENAI_API_KEY "sk-..."
```

PowerShell equivalent of `setx` (same user-scope target):

```powershell
[Environment]::SetEnvironmentVariable("GLM_ANTHROPIC_AUTH_TOKEN", "sk-...", "User")
```

Example (PowerShell-only scope, via `$PROFILE`):

```powershell
# Claude / OpenCode profiles
$env:GLM_ANTHROPIC_AUTH_TOKEN = "sk-..."
$env:XIAOMI_ANTHROPIC_AUTH_TOKEN = "sk-..."

# Codex profiles
$env:OPENAI_API_KEY = "sk-..."
```

To read back or remove a Windows user env var:

```powershell
[Environment]::GetEnvironmentVariable("GLM_ANTHROPIC_AUTH_TOKEN", "User")   # read
[Environment]::SetEnvironmentVariable("GLM_ANTHROPIC_AUTH_TOKEN", $null, "User")   # remove
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

## Provider Limitations

### Codex

Codex profiles only switch the API source (base URL + API key), not the model. Codex works best with OpenAI's own models — using third-party providers as a relay is the common use case. Apply mode is not available for Codex; use Launch mode only.

### OpenCode

OpenCode profiles require the model to be specified as a positional argument: `aweswitch <profile> <model>`. If no model is given, the first model in `OPENCODE_MODEL` is used. Apply mode is not available for OpenCode; use Launch mode only. The first launch writes the provider entry to `~/.config/opencode/opencode.json`; subsequent launches reuse and extend it.

## Core Rules

1. **Do not run `aweswitch <profile>` inside the agent.** It launches an interactive sub-agent. Tell the user to run it in their own terminal.
2. **Default to apply mode for Claude profiles.** Run `aweswitch apply <profile>` for the user. For Codex and OpenCode profiles, tell the user to use Launch mode in their own terminal.
3. Always read the config file before editing. Never overwrite existing profiles without checking.
4. Never hardcode API keys or tokens. Use `${VAR_NAME}` references.
5. Profile names must be unique across all provider groups. Check before adding.
6. Check for existing values before setting env vars, to avoid duplicates. Where they live depends on the platform: `~/.zshrc` (macOS zsh), `~/.bashrc` or `~/.bash_profile` (bash), or the user environment via `setx` on Windows (`$PROFILE` if the user wants PowerShell-only scope).
7. Use `aweswitch list` and `aweswitch show` to verify changes after editing.
8. If the config file does not exist, run `aweswitch config init` first.
9. Do not run `config init` if the config already exists — it will error.
