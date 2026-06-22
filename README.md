<div align="center">
  <img src="logo/hero.png" alt="aweswitch" width="860">
  <h1>aweswitch: Agent Profile Switcher</h1>
  <p><strong>A tiny local launcher for switching AI agent runtime profiles.</strong></p>
  <p>Start different agent sessions with different API endpoints, tokens, and models without rewriting global agent config.</p>
  <p>
    <strong>English</strong> ·
    <a href="./README_cn.md">简体中文</a> ·
    <a href="https://we.webioinfo.top/">Webioinfo</a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/version-0.2.1-7C3AED?style=flat-square" alt="Version">
    <img src="https://img.shields.io/badge/python-%E2%89%A53.9-0EA5E9?style=flat-square" alt="Python">
    <img src="https://img.shields.io/badge/license-MPL--2.0-22C55E?style=flat-square" alt="License">
  </p>
  <p>
    <img src="https://img.shields.io/badge/status-alpha-c96a3d?style=flat-square" alt="Status">
    <img src="https://img.shields.io/badge/provider-Claude_Code_%7C_Codex-7C3AED?style=flat-square" alt="Provider">
    <img src="https://img.shields.io/badge/install-pip-22C55E?style=flat-square" alt="pip install">
    <img src="https://img.shields.io/badge/platform-local_CLI-334155?style=flat-square" alt="Local CLI">
    <img src="https://img.shields.io/pepy/dt/aweswitch?style=flat-square" alt="PyPI downloads">
    <img src="https://img.shields.io/github/stars/mugpeng/aweswitch?style=flat-square" alt="GitHub stars">
  </p>
</div>

> Two ways to switch agent profiles: launch isolated sessions, or apply to settings for in-session `/model` switching.

`aweswitch` reads profiles from `~/.config/aweswitch/config.json` and offers two modes:

- **Launch mode** (`aweswitch <profile>`) — starts a new agent session with isolated env. Each session gets its own API endpoint, token, and model. Multiple profiles can run in different terminals simultaneously. Env is frozen at launch.
- **Apply mode** (`aweswitch apply <profile>`) — writes profile env to `~/.claude/settings.json`. Start claude first, then in a new terminal run `aweswitch apply <profile>` (or ask the aweswitch skill to do it). Restart the session or use `/model` to pick the new model. Only one profile can be active at a time.

Today it supports Claude Code and Codex profiles. Support for Hermes, OpenCode, and other agents is planned.

## Support Tools

aweswitch is powered by two companion tools:

- **[aweskill](https://github.com/Webioinfo01/aweskill)** — CLI skill package manager for AI agents. Handles skill installation, updates, and projection across 47+ coding agents.
- **[aweshelf](https://github.com/Webioinfo01/aweshelf)** — Session bookmark manager for Claude Code and Codex. Bookmark, categorize, and restore sessions with aweswitch profiles.

aweswitch manages how you **launch** sessions; aweshelf manages how you **remember** them. Use `aweswitch -c` to auto-bookmark at launch, and `aweshelf resume` to restore with the same profile later.

## Install & Usage

### Let AI agent install and configure

If you are in Claude Code, Codex, Cursor, or other coding agents, tell it:

```text
Read https://github.com/Webioinfo01/aweswitch/blob/main/README.ai.md and follow it to install and configure aweswitch.
```

The agent will install aweswitch, set up config, add profiles, and apply the profile to your settings. For ongoing management, it can also install the aweswitch skill via [aweskill](https://aweskill.webioinfo.top/).

**What you can say after setup:**

> "Apply cc-glm to my settings so I can use /model to switch."
> "List all aweswitch profiles."
> "Add a new codex profile for AiHubMix."
> "Change the model in cc-glm to glm-5.2."

The agent can run `aweswitch apply` and `aweswitch restore` directly, but will never run `aweswitch <profile>` (launch mode) — that would nest an agent inside an agent. To launch a profile, run it in your own terminal:

```bash
aweswitch cc-glm
```

### Manual setup

Install from PyPI:

```bash
pip3 install aweswitch
```

Create the default config and edit it:

```bash
aweswitch config init
aweswitch config edit
```

Or add a profile interactively:

```bash
aweswitch add
```

Configure the token variables referenced by your profiles:

```bash
# Claude profiles
export GLM_ANTHROPIC_AUTH_TOKEN="..."
export GEMINI_ANTHROPIC_AUTH_TOKEN="..."
export XIAOMI_ANTHROPIC_AUTH_TOKEN="..."

# Codex profiles
export OPENAI_API_KEY="..."
export AIHUBMIX_OPENAI_KEY="..."
```

Put long-lived variables in `~/.zshrc` if you want them available in every shell.

Verify:

```bash
aweswitch list
aweswitch show cc-glm
```

### Launch mode — isolated sessions

Each call launches a new agent session with its own env. Multiple profiles can run in different terminals.

```bash
aweswitch cc-glm                      # launch Claude Code profile
aweswitch cx-openai                   # launch Codex profile
aweswitch cc-glm --dangerously-skip-permissions   # pass extra args
aweswitch cc-glm -c backend -t "Fix auth bug"     # auto-bookmark with aweshelf
```

### Apply mode — persistent default (Claude only)

Write profile env to `~/.claude/settings.json`. Start claude first, then in a new terminal:

```bash
aweswitch apply cc-glm                # write profile to settings.json
aweswitch apply cc-glm --force        # overwrite existing backup
aweswitch restore                      # restore settings from backup
```

Restart the session or use `/model` to pick the new model.

### When to use which mode

| Scenario | Mode |
|---|---|
| Run multiple profiles side by side | Launch |
| Switch models within a session via `/model` | Apply |
| Try a different API quickly | Launch |
| Set a persistent default profile | Apply |

> **Note:** the two modes don't interact. `aweswitch cc-glm` does not read or modify settings.json. `aweswitch apply cc-glm` does not affect running sessions.

### Config management

```bash
aweswitch add                         # add profile interactively
aweswitch list                        # list all profiles
aweswitch show cc-glm                 # inspect one profile (secrets redacted)
aweswitch config show                 # full config (secrets redacted)
aweswitch config edit                 # open config in editor
```

See [aweshelf Integration](#aweshelf-integration) for auto-bookmarking at launch.

## Self-Update

aweswitch checks PyPI for newer versions in the background on each run. If an update is available, a reminder is printed to stderr after the session ends.

To update manually:

```bash
aweswitch self-update
```

To check without updating:

```bash
aweswitch self-update --check
```

To disable the background check:

```bash
export AWESWITCH_NO_UPDATE_CHECK=1
```

## aweshelf Integration

[aweshelf](https://github.com/Webioinfo01/aweshelf) is a session bookmark manager for Claude Code and Codex CLI. It lets you save, tag, search, and resume past coding sessions.

aweswitch integrates with aweshelf so you can bookmark a session at launch time, without a separate step:

```bash
aweswitch cc-glm -c backend -t "Fix auth bug"
```

### Options

| Flag | Description |
|------|-------------|
| `-c`, `--category` | Category to tag the bookmark with (e.g. `backend`, `research`, `infra`). |
| `-t`, `--title` | Custom bookmark title. If omitted, aweshelf uses the session's first message. |

Both options require aweshelf to be installed. If aweshelf is not found, they are ignored with a warning printed to stderr. Claude Code launches normally regardless.

> **Note**: launching multiple `aweswitch -c` sessions simultaneously in the same project may result in incorrect bookmark assignment. Sequential launches are safe — as long as the previous session's JSONL file has been created before starting the next one (typically a few seconds). See [CONTRIBUTING.md](./docs/CONTRIBUTING.md#known-limitation-concurrent-launch-race-condition) for details.

### Install aweshelf

```bash
pip3 install aweshelf
```

### What aweshelf does on its own

Even without aweswitch's `-c`/`-t` flags, aweshelf is useful independently:

```bash
aweshelf bookmark               # bookmark a session interactively
aweshelf bookmark --current     # bookmark the most recent session in this project
aweshelf list                   # list all bookmarks
aweshelf search "auth"          # full-text search across bookmarks
aweshelf resume BOOKMARK_ID     # resume a saved session
aweshelf browse                 # interactive TUI browser
```

See the [aweshelf README](https://github.com/Webioinfo01/aweshelf) for full documentation.

## FAQ

### Why aweswitch, and who is it for?

`aweswitch` is for people who use AI coding agents with more than one runtime endpoint, model, or token source and want a repeatable local command instead of editing settings by hand.

- **One local config file** at `~/.config/aweswitch/config.json`
- **Named agent profiles** such as `cc-glm`, `cc-gemini`, `cc-xiaomi`, or `cx-openai`
- **Side-by-side sessions** where different terminals can launch different API/model combinations
- **Runtime-only injection** through provider-specific arguments
- **No mutation of global agent config**, so already-open agent sessions keep working with the settings they started with
- **Token references** through shell variables or `~/.claude/settings.json`
- **Readable JSON** with provider grouping under `profiles.claude` and `profiles.codex`

### Where does aweswitch store profiles?

By default, profiles live in:

```bash
~/.config/aweswitch/config.json
```

You can override that path with `AWESWITCH_CONFIG`.

### Does aweswitch modify Claude settings?

In **launch mode**, no — it reads your aweswitch config and launches Claude Code with runtime settings for that process only. Already-running sessions are unaffected.

In **apply mode**, yes — `aweswitch apply <profile>` writes the profile's env to `~/.claude/settings.json`. A backup is created on first apply. Use `aweswitch restore` to undo.

### Does aweswitch support Codex?

Yes. Codex profiles use `OPENAI_BASE_URL` and `OPENAI_API_KEY` in their `env` block. aweswitch injects the base URL via Codex's `-c` config overrides and the API key via environment variable, so no files are written to `~/.codex/`.

### Does aweswitch support Hermes?

Not yet. The config format groups profiles by provider so future support can fit naturally.

## Similar Tools

### [cc-switch](https://github.com/farion1231/cc-switch)

`cc-switch` is an adjacent Claude Code switching tool. It is useful reference material for the same problem space: making Claude Code provider/model switching easier from the command line.

The key difference is that `aweswitch` avoids global config mutation. Many switching tools work by changing the agent's shared API/model settings; that can make already-open agent sessions unreliable because the global API endpoint changed underneath them. `aweswitch` keeps profiles in its own JSON file and injects settings only when launching a new process, so each session keeps the API and model it started with.

`aweswitch` currently takes a smaller Python-package approach: local JSON profiles, runtime-only injection (Claude Code `--settings`, Codex `-c` flags and env vars), secret redaction for inspection commands, and provider grouping that leaves room for future agent support.

## Profile Rules

- Profiles are grouped under `profiles.<provider>.<profileName>`.
- Supported providers: `claude`, `codex`.
- Profile names must be unique across all provider groups.
- `env` values only apply to the launched process.
- `${VAR_NAME}` values are expanded from the current shell environment.
- `show` and `config show` redact keys matching token, key, secret, password, or auth.

### Claude Profiles

- Pass `env` through runtime `--settings '{"env": ...}'`.
- Set the model with `env.ANTHROPIC_MODEL`.
- Token values can also expand from `~/.claude/settings.json` when they are missing from the shell.

`ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, and `ANTHROPIC_DEFAULT_OPUS_MODEL` are not configured by default. If you want Claude Code to use a lighter model for lightweight or background tasks, add `ANTHROPIC_DEFAULT_HAIKU_MODEL` to the profile:

```json
{
  "profiles": {
    "claude": {
      "cc-xiaomi": {
        "env": {
          "ANTHROPIC_BASE_URL": "https://token-plan-sgp.xiaomimimo.com/anthropic",
          "ANTHROPIC_AUTH_TOKEN": "${XIAOMI_ANTHROPIC_AUTH_TOKEN}",
          "ANTHROPIC_MODEL": "mimo-v2.5-pro",
          "ANTHROPIC_DEFAULT_HAIKU_MODEL": "mimo-v2.5"
        }
      }
    }
  }
}
```

This keeps the main model on `mimo-v2.5-pro` while allowing Claude Code to use `mimo-v2.5` for lighter work.

### Codex Profiles

- Requires `OPENAI_BASE_URL` and `OPENAI_API_KEY` in `env`.
- Base URL is injected via `-c model_providers.custom.base_url=...` (no file writes).
- API key is injected via environment variable (no writes to `~/.codex/auth.json`).
- Extra arguments are passed through to the `codex` CLI.

Codex profiles only switch the API source (base URL + API key), not the model. In practice, Codex works best with OpenAI's own models — using third-party providers as a relay is the common use case, while switching to entirely different model providers tends to give a poor experience.

```json
{
  "profiles": {
    "codex": {
      "cx-aihubmix": {
        "env": {
          "OPENAI_BASE_URL": "https://aihubmix.com/v1",
          "OPENAI_API_KEY": "${AIHUBMIX_OPENAI_KEY}"
        }
      }
    }
  }
}
```

aweswitch does not write to `~/.codex/`. The base URL is passed via Codex's `-c` flag and the API key via environment variable. This keeps your global Codex config untouched.

To add a Codex profile interactively:

```bash
aweswitch add
# Provider: codex
# Profile name: cx-myprovider
# OPENAI_BASE_URL: https://myprovider.com/v1
# OPENAI_API_KEY env var name: MY_PROVIDER_KEY
```

## Development

See [Contributing](./docs/CONTRIBUTING.md) for setup, testing, branching, and release workflow.

- [Contributing](./docs/CONTRIBUTING.md)
- [Changelog](./docs/CHANGELOG.md)
