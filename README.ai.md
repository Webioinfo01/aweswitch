# aweswitch Bootstrap Protocol

This document is for AI coding agents. Help the user install and configure `aweswitch`, an agent profile switcher for Claude Code and Codex.

## Do Not Launch

**Never run `aweswitch <profile-name>` inside this agent.** aweswitch launches an interactive agent (Claude Code or Codex) via `execvpe`, which would nest an agent inside an agent. Always tell the user to run it in their own terminal.

You may run these read-only commands: `aweswitch list`, `aweswitch show <profile>`, `aweswitch config path`, `aweswitch config show`.

## Language Behavior

- Reply in the user's language when possible.
- If the user asks in Chinese, continue in Chinese.
- If the user asks in English, continue in English.

## Step 1: Install aweswitch CLI

### Prerequisites

- Python >= 3.9 (`python3 --version`)
- pip available (`pip --version`)

If Python is missing, tell the user to install it from https://www.python.org/.

### Steps

#### 1. Install aweswitch Python package

```bash
pip3 install aweswitch
```

#### 2. Verify aweswitch CLI

```bash
aweswitch -v
```

Expected output: `aweswitch X.Y.Z`

---

## Step 2: Initialize config

```bash
aweswitch config init
```

This creates `~/.config/aweswitch/config.json` with example profiles.

---

## Step 3: Help the user configure profiles

The config file is at `~/.config/aweswitch/config.json` (override with `AWESWITCH_CONFIG` env var).

### Config structure

```json
{
  "profiles": {
    "claude": {
      "<profile-name>": {
        "env": {
          "ANTHROPIC_BASE_URL": "<url>",
          "ANTHROPIC_AUTH_TOKEN": "${ENV_VAR_NAME}",
          "ANTHROPIC_MODEL": "<model-id>"
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

### Provider differences

| Field | Claude | Codex |
|-------|--------|-------|
| Base URL key | `ANTHROPIC_BASE_URL` | `OPENAI_BASE_URL` |
| Auth key | `ANTHROPIC_AUTH_TOKEN` | `OPENAI_API_KEY` |
| Model key | `ANTHROPIC_MODEL` | not supported (Codex uses its own model) |
| Injection method | `--settings` temp file | `-c` flag + env var |
| File writes | none | none |

### Naming convention

- Claude profiles: `cc-` prefix (e.g. `cc-glm`, `cc-xiaomi`)
- Codex profiles: `cx-` prefix (e.g. `cx-openai`, `cx-aihubmix`)

### Adding a profile

Edit the config file directly (do not run `aweswitch add` — it is interactive and would block the agent).

Steps:
1. Read the current config first.
2. Add the new profile under the appropriate provider key.
3. Use `${ENV_VAR_NAME}` syntax for token values — never hardcode secrets.
4. Ensure profile names are unique across all providers.

---

## Step 4: Set up environment variables

Token values in profiles use `${VAR_NAME}` references that expand from the shell environment. These must be set before launching a profile.

### Where to put them

Add `export` lines to the user's shell config file:

| Shell | File |
|-------|------|
| zsh (default on macOS) | `~/.zshrc` |
| bash | `~/.bashrc` or `~/.bash_profile` |

### Format

```bash
# Claude profiles
export GLM_ANTHROPIC_AUTH_TOKEN="sk-..."
export XIAOMI_ANTHROPIC_AUTH_TOKEN="sk-..."

# Codex profiles
export OPENAI_API_KEY="sk-..."
export AIHUBMIX_OPENAI_KEY="sk-..."
```

### Steps

1. Read the user's current `~/.zshrc` (or `~/.bashrc`).
2. Check which env vars are already set to avoid duplicates.
3. Append the new `export` lines at the end.
4. Tell the user to run `source ~/.zshrc` or open a new terminal.

---

## Step 5: Tell the user to launch

After configuration is complete, tell the user to open a new terminal and run:

```bash
aweswitch <profile-name>
```

Do not run this command yourself.

---

## Useful commands

Read-only commands (safe to run in agent):

```bash
aweswitch list                    # list all profiles (name, provider, model/url)
aweswitch show <profile>          # show one profile with secrets redacted
aweswitch config path             # print config file path
aweswitch config show             # show full config with secrets redacted
```

Launch commands (user must run in their own terminal):

```bash
aweswitch <profile>               # launch agent with profile
aweswitch <profile> [extra args]  # pass extra args through to the agent
```

---

## Safety Rules

- **Do not run `aweswitch <profile>` inside the agent.** It launches an interactive sub-agent. Tell the user to run it in their own terminal.
- Read the existing config before modifying it. Do not overwrite profiles the user already has.
- Never hardcode API keys or tokens in the config. Always use `${VAR_NAME}` references.
- When adding env vars to `~/.zshrc`, check for existing entries first to avoid duplicates.
- If the user's config already has profiles, ask before adding or renaming anything.
- If any command fails, report the exact command and error message. Do not silently retry.
- Do not run `aweswitch config init` if the config already exists — it will refuse and error.

---

## Next Steps

### aweshelf — session bookmarking

After setting up aweswitch profiles, the user may want to save and restore sessions. Point them to [aweshelf](https://github.com/Webioinfo01/aweshelf), a session bookmark manager for Claude Code and Codex.

If the user agrees, read the aweshelf AI install guide:

```
https://github.com/Webioinfo01/aweshelf/blob/main/README.ai.md
```

### aweswitch skill

If the agent supports skills, install the aweswitch skill for ongoing profile management. The skill file is at:

```
resources/skills/aweswitch/SKILL.md
```

Install it to the agent's skill directory (e.g. `~/.claude/skills/aweswitch/SKILL.md` for Claude Code).
