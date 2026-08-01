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

## Step 2: Install aweswitch skill

Install the skill so the agent can help manage profiles in this and future sessions. Choose one of the following options.

### Option A: Via aweskill (recommended if aweskill is available)

Use this option if the user already has aweskill installed, or is willing to install it. This gives full skill management — install, update, projection, backup.

#### Prerequisites

- Node.js >= 20 (`node --version`) — required by aweskill
- npm available (`npm --version`)

If Node.js is missing, tell the user to install it from https://nodejs.org/.

#### Steps

##### A1. Install aweskill (if not already installed)

```bash
npm install -g aweskill
```

##### A2. Initialize the aweskill central store (if not already done)

```bash
aweskill store init
```

##### A3. Install aweswitch skill from GitHub

```bash
aweskill install Webioinfo01/aweswitch
```

##### A4. Identify the current agent

```bash
aweskill agent supported
```

Look for lines marked with `✓`. Common agent ids: `claude-code`, `cursor`, `codex`, `gemini-cli`, `windsurf`, `opencode`, `qwen-code`.

If you cannot determine the agent id, ask the user.

##### A5. Project aweswitch skill to this agent

```bash
aweskill agent add skill aweswitch --global --agent <agent-id>
```

##### A6. Verify

```bash
aweskill agent list --global --agent <agent-id>
```

Expected: `aweswitch` shows as `linked`.

---

### Option B: Direct copy (no aweskill needed)

Use this option if the user does not have aweskill and does not want to install Node.js. This copies the SKILL.md file directly into the agent's skill directory.

#### Prerequisites

- `curl` or `wget` available

#### Steps

##### B1. Identify the current agent's skill directory

Determine which agent is running and its global skill directory:

| Agent | Skill directory |
|---|---|
| Claude Code | `~/.claude/skills/aweswitch/` |
| Codex | `~/.codex/skills/aweswitch/` |
| Cursor | `.cursor/skills/aweswitch/` (project-level) |
| Gemini CLI | `~/.gemini/skills/aweswitch/` |
| Windsurf | `~/.windsurf/skills/aweswitch/` |
| OpenCode | `~/.opencode/skills/aweswitch/` |
| Qwen Code | `~/.qwen/skills/aweswitch/` |

If the agent is not in this list, ask the user where to place the skill file.

##### B2. Download and place SKILL.md

```bash
mkdir -p <skill-directory>
curl -fsSL https://raw.githubusercontent.com/Webioinfo01/aweswitch/main/resources/skills/aweswitch/SKILL.md -o <skill-directory>/SKILL.md
```

Replace `<skill-directory>` with the path from step B1.

---

## Step 3: Initialize config

```bash
aweswitch config init
```

This creates `~/.config/aweswitch/config.json` with example profiles.

---

## Step 4: Help the user configure profiles

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

## Step 5: Set up environment variables

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

## Step 6: Tell the user to switch profiles

aweswitch has two modes. Ask the user which one they prefer.

### Option A: Launch mode — isolated sessions

Each `aweswitch <profile>` call launches a new claude session with its own env. Multiple profiles can run in different terminals simultaneously. Env is frozen at launch.

```bash
aweswitch <profile-name>
```

Do not run this command yourself — tell the user to run it in their terminal.

### Option B: Apply mode — persistent default

Write the profile's env to `~/.claude/settings.json`. All new claude sessions use this profile. The user can switch models within a session via `/model`.

```bash
aweswitch apply <profile-name>
```

Then restart the session or use `/model` to pick the new model.

To undo:

```bash
aweswitch restore
```

### When to recommend which

| Scenario | Recommend |
|---|---|
| User wants to run multiple profiles side by side | Launch |
| User wants to switch models within a session via `/model` | Apply |
| User wants to try a different API quickly | Launch |
| User wants a persistent default profile | Apply |

### Important: modes don't interact

- `aweswitch cc-glm` does NOT read or modify settings.json.
- `aweswitch apply cc-glm` does NOT affect running sessions.
- Applying a new profile does not change the env of a session started with `aweswitch <profile>`.

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
aweswitch <profile>               # launch agent with profile (launch mode)
aweswitch <profile> [extra args]  # pass extra args through to the agent
```

Apply commands (safe to run in agent):

```bash
aweswitch apply <profile>         # write profile env to settings.json (apply mode)
aweswitch restore                 # restore settings.json from backup
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

## Final Step

After setup, tell the user to invoke skills (`/` in Claude Code, `$` in Codex, or the equivalent in other agents) and check if `aweswitch` appears in the list. If it does, the skill is ready to use immediately. If not, the user should restart the agent.

> aweswitch is installed and configured. Invoke skills (type `/` or `$` depending on your agent) and look for `aweswitch` — if it appears, you're good to go. If not, restart the agent. Then you can ask me things like:
>
> - "Add a new codex profile for AiHubMix."
> - "Show my aweswitch config."
> - "Set up OPENAI_API_KEY in my zshrc."

If the user is speaking Chinese, use this version instead:

> aweswitch 已安装并配置完成。请调用 skills（输入 `/` 或 `$`，取决于你的 agent），看看列表中是否出现了 `aweswitch`。如果出现了，说明已就绪可以直接使用。如果没有，请重启 agent 后再试。然后你可以继续问我，例如：
>
> - "添加一个 AiHubMix 的 codex profile。"
> - "看看我的 aweswitch 配置。"
> - "在 zshrc 里配置 OPENAI_API_KEY。"

---

## Next Steps

### aweshelf — session bookmarking

After setting up aweswitch profiles, the user may want to save and restore sessions. Point them to [aweshelf](https://github.com/Webioinfo01/aweshelf), a session bookmark manager for Claude Code and Codex.

If the user agrees, read the aweshelf AI install guide:

```
https://github.com/Webioinfo01/aweshelf/blob/main/README.ai.md
```
