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
    <img src="https://img.shields.io/badge/version-0.1.4-7C3AED?style=flat-square" alt="Version">
    <img src="https://img.shields.io/badge/python-%E2%89%A53.9-0EA5E9?style=flat-square" alt="Python">
    <img src="https://img.shields.io/badge/license-MPL--2.0-22C55E?style=flat-square" alt="License">
  </p>
  <p>
    <img src="https://img.shields.io/badge/status-alpha-c96a3d?style=flat-square" alt="Status">
    <img src="https://img.shields.io/badge/provider-Claude_Code-7C3AED?style=flat-square" alt="Claude Code">
    <img src="https://img.shields.io/badge/install-pip-22C55E?style=flat-square" alt="pip install">
    <img src="https://img.shields.io/badge/platform-local_CLI-334155?style=flat-square" alt="Local CLI">
    <img src="https://img.shields.io/pepy/dt/aweswitch?style=flat-square" alt="PyPI downloads">
    <img src="https://img.shields.io/github/stars/mugpeng/aweswitch?style=flat-square" alt="GitHub stars">
  </p>
</div>

> Run different agent profiles side by side without breaking sessions that are already open.

`aweswitch` reads profiles from `~/.config/aweswitch/config.json`, expands environment references, prepares provider-specific runtime arguments, and then starts the selected agent. Each launch gets its own API endpoint, token, and model through runtime arguments instead of mutating global agent settings.

It is intentionally small. The project is positioned as an agent profile switcher, but today it supports Claude Code profiles only. Codex and Hermes profile groups may appear in the config shape later, but they are not executable yet.

## Install

Install from PyPI:

```bash
pip3 install aweswitch
aweswitch --help
```

Create the default config:

```bash
aweswitch config init
```

Then open the config and align it with your real Claude Code providers, models, and token variable names:

```bash
aweswitch config edit
```

The default config shape groups profiles under their provider. This is a reference config you can adapt:

```json
{
  "profiles": {
    "claude": {
      "cc-glm": {
        "env": {
          "ANTHROPIC_BASE_URL": "https://open.bigmodel.cn/api/anthropic",
          "ANTHROPIC_AUTH_TOKEN": "${GLM_ANTHROPIC_AUTH_TOKEN}",
          "ANTHROPIC_MODEL": "glm-5.1"
        }
      },
      "cc-gemini": {
        "env": {
          "ANTHROPIC_BASE_URL": "https://openclaw.chatgo.best",
          "ANTHROPIC_AUTH_TOKEN": "${GEMINI_ANTHROPIC_AUTH_TOKEN}",
          "ANTHROPIC_MODEL": "gemini-3.1-pro-preview"
        }
      },
      "cc-xiaomi": {
        "env": {
          "ANTHROPIC_BASE_URL": "https://token-plan-sgp.xiaomimimo.com/anthropic",
          "ANTHROPIC_AUTH_TOKEN": "${XIAOMI_ANTHROPIC_AUTH_TOKEN}",
          "ANTHROPIC_MODEL": "mimo-v2.5-pro"
        }
      }
    }
  }
}
```

Configure the token variables referenced by your profiles:

```bash
export GLM_ANTHROPIC_AUTH_TOKEN="..."
export GEMINI_ANTHROPIC_AUTH_TOKEN="..."
export XIAOMI_ANTHROPIC_AUTH_TOKEN="..."
```

Put long-lived variables in `~/.zshrc` if you want them available in every shell.

Verify the configured profiles:

```bash
aweswitch list
aweswitch show cc-glm
```

Run a profile:

```bash
aweswitch cc-glm
```

Pass extra arguments through to Claude Code:

```bash
aweswitch cc-glm --dangerously-skip-permissions
```

Useful config commands:

```bash
aweswitch config path
aweswitch config show
aweswitch config edit
```

## FAQ

### Why aweswitch, and who is it for?

`aweswitch` is for people who use AI coding agents with more than one runtime endpoint, model, or token source and want a repeatable local command instead of editing settings by hand.

- **One local config file** at `~/.config/aweswitch/config.json`
- **Named agent profiles** such as `cc-glm`, `cc-gemini`, or `cc-xiaomi`
- **Side-by-side sessions** where different terminals can launch different API/model combinations
- **Runtime-only injection** through provider-specific arguments
- **No mutation of global agent config**, so already-open agent sessions keep working with the settings they started with
- **Token references** through shell variables or `~/.claude/settings.json`
- **Readable JSON** with provider grouping under `profiles.claude`

### Where does aweswitch store profiles?

By default, profiles live in:

```bash
~/.config/aweswitch/config.json
```

You can override that path with `AWESWITCH_CONFIG`.

### Does aweswitch modify Claude settings?

No. It reads your aweswitch config and launches Claude Code with runtime settings for that process only. Switching profiles does not rewrite the global API endpoint or model, so it does not disturb agent sessions that are already running.

### Does aweswitch support Codex or Hermes?

Not yet. The config format groups profiles by provider so future support can fit naturally, but the executable provider set is currently Claude Code only.

## Similar Tools

### [cc-switch](https://github.com/farion1231/cc-switch)

`cc-switch` is an adjacent Claude Code switching tool. It is useful reference material for the same problem space: making Claude Code provider/model switching easier from the command line.

The key difference is that `aweswitch` avoids global config mutation. Many switching tools work by changing the agent's shared API/model settings; that can make already-open agent sessions unreliable because the global API endpoint changed underneath them. `aweswitch` keeps profiles in its own JSON file and injects settings only when launching a new process, so each session keeps the API and model it started with.

`aweswitch` currently takes a smaller Python-package approach: local JSON profiles, runtime-only Claude Code `--settings`, secret redaction for inspection commands, and provider grouping that leaves room for future agent support.

## Profile Rules

- Profiles are grouped under `profiles.<provider>.<profileName>`.
- `claude` is the only supported provider right now.
- Profile names must be unique across all provider groups.
- Claude profiles pass `env` through runtime `--settings '{"env": ...}'`.
- Set the Claude model with `env.ANTHROPIC_MODEL`.
- `env` values only apply to the launched process.
- `${VAR_NAME}` values are expanded from the current shell environment.
- Claude token values can also expand from `~/.claude/settings.json` when they are missing from the shell.
- `show` and `config show` redact keys matching token, key, secret, password, or auth.

## Claude Model Overrides

For Claude profiles, `ANTHROPIC_MODEL` is the primary model setting.

`ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, and `ANTHROPIC_DEFAULT_OPUS_MODEL` are not configured by default.

If you want Claude Code to use a lighter model for lightweight or background tasks, add `ANTHROPIC_DEFAULT_HAIKU_MODEL` to the profile:

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

## Development

Run the test suite:

```bash
python3 tests/test_aweswitch.py
```

Run the syntax check:

```bash
python3 -m py_compile src/aweswitch/cli.py tests/test_aweswitch.py
```

Install the local checkout in editable mode:

```bash
pip3 install -e .
```

Build a local package:

```bash
pip3 install build
python3 -m build
```

Install a built wheel locally:

```bash
pip3 install dist/aweswitch-0.1.4-py3-none-any.whl
```

Project docs:

- [Contributing](./docs/CONTRIBUTING.md)
- [Changelog](./docs/CHANGELOG.md)
