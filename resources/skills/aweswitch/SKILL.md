---
name: aweswitch
description: "Use when helping users manage aweswitch profiles — adding, editing, or switching Claude Code, Codex, and OpenCode API configurations, plus official-login accounts (Claude Code / Codex OAuth). 中文触发词：切换profile、添加profile、配置aweswitch、API切换、provider管理、官方帐号、多帐号切换、account管理。"
---

# aweswitch

This skill covers **configuring** aweswitch profiles and applying them to settings.

## Do Not Launch

**Never run `aweswitch <profile-name>` inside this agent.** It launches an interactive agent via `execvpe`, which would nest an agent inside an agent. If the user wants to launch a profile, tell them to run it in their own terminal.

## Two Modes

aweswitch has two ways to switch profiles. This agent can only help with **Apply mode**; launches must be run by the user.

### Launch mode — `aweswitch <profile>` (user only, not for this agent)

Launches a new session with isolated env. Each session is independent. User runs this themselves in a terminal. **Do not run or suggest running this inside the agent.**

### Apply mode — `aweswitch apply [profiles...]` (this agent can do this)

Writes profiles into each agent's own config as the persistent default:

- Claude → env in `~/.claude/settings.json` (undo with `aweswitch config restore`)
- Codex → provider + model in `~/.codex/config.toml` (first apply creates a `.toml.bak` backup; the API key stays in the environment via `env_key`)
- OpenCode → provider entry + full model list upserted into `~/.config/opencode/opencode.json` (overwritten if the provider exists, added if missing); `aweswitch apply --opencode` does every OpenCode profile. After renaming/deleting an opencode profile, apply warns about its leftover provider entry (old sessions stay pinned to those model IDs); `aweswitch apply --opencode --prune-orphans` removes it. Hand-written provider entries are never touched.

At most one Claude and one Codex profile per call (each holds a single active default); OpenCode profiles coexist and accept bulk.

### When to recommend which

| User wants... | Recommend | Agent role |
|---|---|---|
| Switch models within a session via `/model` | Apply | Run `aweswitch apply <cc-profile>` directly |
| A persistent default profile | Apply | Run `aweswitch apply <profile>` directly |
| Push edited opencode profiles into opencode.json | Apply | Run `aweswitch apply [oc-profiles...]` directly |
| Run multiple profiles side by side | Launch | Tell user to run in their terminal |
| Try a different API quickly | Launch | Tell user to run in their terminal |
| Use OpenCode with a profile in a fresh session | Launch | Tell user to run in their terminal |

### Mode availability by provider

| Provider | Apply mode (`aweswitch apply`) | Launch mode (`aweswitch <profile>`) |
|----------|-------------------------------|-------------------------------------|
| Claude | supported | supported |
| Codex | supported | supported |
| OpenCode | supported (coexist; bulk supported) | supported |
| Official accounts (claude/codex) | not supported | supported |

You may run these read-only commands:
- `aweswitch list`
- `aweswitch show <profile>`
- `aweswitch config path`
- `aweswitch config show`

You may also run these commands (they modify files but are non-interactive):
- `aweswitch apply [profiles...]` — write profiles into each agent's own config (claude settings.json / codex config.toml / opencode opencode.json; `--opencode` = all opencode profiles)
- `aweswitch config restore [file]` — restore Claude settings from the default or an explicit backup
- `setx VAR_NAME "value"` (Windows only) — persist a user environment variable so both cmd and PowerShell see it

**Note:** accounts are launch-only; `aweswitch apply` rejects them.

## Intent Router

| User intent | Domain | Approach |
|---|---|---|
| "Add a new profile", "add a codex provider" | Add Profile | Edit config file. |
| "Add an opencode profile" | Add Profile | Edit config file; use `opencode` provider group. |
| "Save my official login", "添加官方帐号" | Add Account | Run `aweswitch account add <provider> <name>` (imports current login), or tell user to run `account login`. The interactive `aweswitch add` → `official` covers both paths for the user. |
| "Log in another official account", "再登一个帐号" | Login Account | Tell user to run `aweswitch account login <provider> <name>` in their terminal (interactive). |
| "Sync account tokens", "刷新帐号凭证" | Sync Account | Run `aweswitch account sync <provider> <name>`. |
| "Delete account X", "删除帐号" | Remove Account | Run `aweswitch account remove <provider> <name> [--purge]`. |
| "List profiles", "what profiles do I have" | Browse | `aweswitch list` |
| "Show profile X", "what's in profile X" | Inspect | `aweswitch show <profile>` |
| "Edit profile X", "change the API key" | Edit | Edit config file directly. |
| "Delete profile X" | Remove | Edit config file directly. |
| "Set up API key for X" | Env Vars | Edit `~/.zshrc` or `~/.bashrc`; on Windows run `setx`. |
| "Where is the config?" | Config Path | `aweswitch config path` |
| "Show all config" | Config Show | `aweswitch config show` |
| "Switch to profile X", "launch profile X" | Launch | Tell user to run `aweswitch <profile>` in their terminal. |
| "Launch opencode profile" | Launch | Tell user to run `aweswitch oc-<name> [model]` in their terminal. |
| "Launch codex profile" | Launch | Tell user to run `aweswitch cx-<name> [model]` in their terminal. |
| "Use /model to switch", "在session里切换模型" | Apply | `aweswitch apply <cc-profile>` (Claude). |
| "Apply profile X to settings", "写入settings" | Apply | `aweswitch apply <profile>` (per-provider: claude→settings.json, codex→config.toml, opencode→opencode.json). |
| "Sync opencode profiles", "同步opencode配置" | Apply OpenCode | Run `aweswitch apply [oc-profiles...]` after editing opencode profiles (`--opencode` = all). |
| "Old session errors after profile rename", "改名的旧session报错" | Prune Orphan | Run `aweswitch apply --opencode --prune-orphans` to drop the leftover provider; tell user to switch models inside old sessions (Tab). |
| "Restore settings from backup", "恢复settings" | Restore | `aweswitch config restore [file]` |
| "Run two profiles at the same time" | Launch | Explain: use Launch mode, different terminals. Apply mode can't do this. |
| "Switch without restarting" | Apply | Explain: use Apply mode, then `/model` in session (Claude only). |

## Config Location

Default: `~/.config/aweswitch/config.json`
Override: `AWESWITCH_CONFIG` env var.

Always read the config file before modifying it.

## Config Structure

Profiles split by kind first, then by provider. `api` holds env-based profiles; `accounts` holds official-login credential blobs (opaque, never edit them by hand).

```json
{
  "profiles": {
    "api": {
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
            "OPENAI_API_KEY": "${ENV_VAR_NAME}",
            "OPENAI_MODEL": "<model-id-or-list>"
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
    },
    "accounts": {
      "claude": {
        "<account-name>": { "credentials": "<opaque credential blob>" }
      },
      "codex": {
        "<account-name>": { "auth": "<opaque credential blob>" }
      }
    }
  }
}
```

Names must be unique across the whole `profiles` tree (api and accounts). Pre-0.4 configs (providers directly under `profiles`) are migrated automatically on first load — if you see one, just run any aweswitch command once and it will be rewritten with a `.json.bak` backup.

### Provider fields

| Field | Claude | Codex | OpenCode |
|-------|--------|-------|----------|
| Base URL | `ANTHROPIC_BASE_URL` | `OPENAI_BASE_URL` | `OPENCODE_BASE_URL` |
| Auth token | `ANTHROPIC_AUTH_TOKEN` | `OPENAI_API_KEY` | `OPENCODE_API_KEY` |
| Model | `ANTHROPIC_MODEL` | `OPENAI_MODEL` (list/dict/string, optional) | `OPENCODE_MODEL` (list/dict/string) |
| Injection | `--settings` temp file | `-c` flag + env var | writes to `~/.config/opencode/opencode.json` via `{env:VAR}` |

### Naming convention

- Claude profiles: `cc-` prefix (e.g. `cc-glm`, `cc-xiaomi`)
- Codex profiles: `cx-` prefix (e.g. `cx-openai`)
- OpenCode profiles: `oc-` prefix (e.g. `oc-glm`, `oc-mimo`)
- Claude official accounts: `cco-` prefix (e.g. `cco-team-a`) — convention, not enforced
- Codex official accounts: `cxo-` prefix (e.g. `cxo-work`) — convention, not enforced

### Token references

Token values use `${VAR_NAME}` syntax in the aweswitch config. They expand from:
1. Shell environment variables (primary)
2. `~/.claude/settings.json` env section (Claude only, fallback)

**OpenCode auth key:** aweswitch writes the API key to `~/.config/opencode/opencode.json` using `{env:VAR_NAME}` syntax, so the actual key is never stored on disk. The `${VAR_NAME}` reference in the aweswitch config still expands from the shell env at launch time.

Never hardcode secrets. Always use `${VAR_NAME}` references in the aweswitch config.

## Workflows

### Add a Profile

1. Read the config file
2. Add the new profile under `profiles.api.<provider>` (`claude`, `codex`, or `opencode`)
3. Use `${ENV_VAR_NAME}` for token values
4. Ensure the name is unique across the whole `profiles` tree (api and accounts)
5. Validate the JSON is well-formed

#### OpenCode profile fields

- `OPENCODE_BASE_URL` — provider API endpoint
- `OPENCODE_API_KEY` — token env var name (use `${VAR}` reference)
- `OPENCODE_NAME` — optional display name (defaults to profile name)
- `OPENCODE_MODEL` — models as comma-separated string, list, or dict mapping

```json
{
  "profiles": {
    "api": {
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
aweswitch config restore
```

If the user wants to run multiple profiles in separate terminals instead, tell them to run `aweswitch <profile-name>` in their own terminal. Do not run it yourself.

### Official Accounts

Official-login accounts (Claude Code / Codex OAuth) live in `profiles.accounts.<provider>.<name>` as opaque credential blobs. Launch works like any profile: `aweswitch <account-name>` runs the CLI in a private per-account config dir (`CODEX_HOME` / `CLAUDE_CONFIG_DIR`), so several accounts run side by side.

You may run (non-interactive):

```bash
aweswitch account add <provider> <name>     # import the currently logged-in account
aweswitch account sync <provider> <name>    # copy refreshed tokens back into the config
aweswitch account remove <provider> <name> [--purge]
```

Tell the user to run themselves (interactive login flow):

```bash
aweswitch account login <provider> <name>   # codex: runs `codex login`; claude: run /login then exit
aweswitch add                               # type `official`, then pick login/import — same flows interactively
aweswitch <account-name>                    # launch the account
```

Rules:

- Never print, copy, or edit account blobs — `show`/`config show` mask them entirely by design.
- On macOS, `account add` for claude usually fails (login lives in the Keychain) — recommend `account login` instead.
- Accounts are launch-only; `apply` rejects them.
- After the CLI refreshes tokens inside an account dir, `account sync` updates the config copy.

## Provider Limitations

### Codex

Codex profiles support optional `OPENAI_MODEL` (list/dict/string) to pick a model at launch: `aweswitch cx-<name> [model]`. Without it, the profile only switches the API source (base URL + API key) and the positional argument passes through to the `codex` CLI as-is. The model and base URL are injected via `-c` flags; the API key is injected via `OPENAI_API_KEY` env var. `aweswitch apply cx-<name>` persists the provider and first model into `~/.codex/config.toml` instead (apply uses the first model in `OPENAI_MODEL`).

### OpenCode

OpenCode profiles require the model to be specified as a positional argument: `aweswitch <profile> <model>`. If no model is given, the first model in `OPENCODE_MODEL` is used. The first launch writes the provider entry to `~/.config/opencode/opencode.json`; subsequent launches reuse and extend it. Launching only adds the launched model — `aweswitch apply [oc-profiles...]` upserts the full model list (`--opencode` = all opencode profiles).

## Core Rules

1. **Do not run `aweswitch <profile>` inside the agent.** It launches an interactive sub-agent. Tell the user to run it in their own terminal.
2. **Run `aweswitch apply <profile>` for the user when they want persistent defaults** — works for all three providers (one claude/codex profile per call; opencode accepts bulk). For isolated launch sessions, tell the user to run `aweswitch <profile>` in their own terminal.
3. Always read the config file before editing. Never overwrite existing profiles without checking.
4. Never hardcode API keys or tokens. Use `${VAR_NAME}` references.
5. Profile and account names must be unique across the whole `profiles` tree. Check before adding.
6. Never print or paste account credential blobs; they are masked in all show output for a reason.
7. Check for existing values before setting env vars, to avoid duplicates. Where they live depends on the platform: `~/.zshrc` (macOS zsh), `~/.bashrc` or `~/.bash_profile` (bash), or the user environment via `setx` on Windows (`$PROFILE` if the user wants PowerShell-only scope).
8. Use `aweswitch list` and `aweswitch show` to verify changes after editing.
9. If the config file does not exist, run `aweswitch config init` first.
10. Do not run `config init` if the config already exists — it will error.
