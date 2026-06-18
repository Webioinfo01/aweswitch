<div align="center">
  <img src="logo/hero.png" alt="aweswitch" width="860">
  <h1>aweswitch: Agent Profile Switcher</h1>
  <p><strong>一个很小的本地启动器，用来切换 AI agent 运行时 profile。</strong></p>
  <p>用不同 API、token 和模型启动不同 agent 会话，同时不改写全局 agent 配置。</p>
  <p>
    <a href="./README.md">English</a> ·
    <strong>简体中文</strong> ·
    <a href="https://we.webioinfo.top/">Webioinfo</a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/version-0.2.0-7C3AED?style=flat-square" alt="Version">
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

> 让不同 agent profile 并行运行，同时不影响已经打开的会话。

`aweswitch` 从 `~/.config/aweswitch/config.json` 读取 profile，展开环境变量引用，准备 provider 对应的运行时参数，然后启动所选 agent。每次启动都会拿到自己的 API endpoint、token 和模型；这些配置通过运行时参数注入，而不是改写全局 agent settings。

它刻意保持小而直接。项目定位是 agent profile switcher，目前支持 Claude Code 和 Codex profile。配置格式为以后加入 Hermes 预留了 provider 分组，但 Hermes 现在还不能执行。

## 支持工具

aweswitch 由两个配套工具驱动：

- **[aweskill](https://github.com/Webioinfo01/aweskill)** — 面向 AI agent 的 CLI skill 包管理器。负责 skill 的安装、更新和投影，支持 47+ 编程 agent。
- **[aweshelf](https://github.com/Webioinfo01/aweshelf)** — Claude Code 和 Codex 的会话 bookmark 管理器。可以保存、分类和恢复会话，支持 aweswitch profile。

aweswitch 管**启动**会话，aweshelf 管**记住**会话。用 `aweswitch -c` 在启动时自动 bookmark，用 `aweshelf resume` 恢复时会带上相同的 profile。

## 安装

### 让 AI agent 安装

如果你在 Claude Code、Codex、Cursor 等 coding agent 中工作，直接告诉它：

```text
Read https://github.com/Webioinfo01/aweswitch/blob/main/README.ai.md and follow it to install and configure aweswitch.
```

Agent 会安装 `aweswitch` CLI、初始化配置，并帮你添加 profile。后续 profile 管理也可以通过 [aweskill](https://aweskill.webioinfo.top/) 安装 aweswitch skill。

### pip

从 PyPI 安装：

```bash
pip3 install aweswitch
aweswitch --help
```

创建默认配置：

```bash
aweswitch config init
```

然后打开配置文件，把 provider、模型和 token 环境变量名对齐到你的真实服务：

```bash
aweswitch config edit
```

或者用交互方式添加新 profile：

```bash
aweswitch add
```

依次提示选择 provider（claude 或 codex）、profile 名称，以及 provider 对应的字段。

默认配置格式按 provider 分组。下面是一份可按需修改的参考配置：

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
    },
    "codex": {
      "cx-openai": {
        "env": {
          "OPENAI_BASE_URL": "https://api.openai.com",
          "OPENAI_API_KEY": "${OPENAI_API_KEY}"
        }
      },
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

配置 profile 引用的 token 环境变量：

```bash
# Claude profiles
export GLM_ANTHROPIC_AUTH_TOKEN="..."
export GEMINI_ANTHROPIC_AUTH_TOKEN="..."
export XIAOMI_ANTHROPIC_AUTH_TOKEN="..."

# Codex profiles
export OPENAI_API_KEY="..."
export AIHUBMIX_OPENAI_KEY="..."
```

如果希望每次打开终端都可用，可以把这些变量放进 `~/.zshrc`。

验证配置后的 profile：

```bash
aweswitch list
aweswitch show cc-glm
```

启动 profile：

```bash
aweswitch cc-glm       # Claude Code
aweswitch cx-openai    # Codex
```

额外参数会透传给 agent：

```bash
aweswitch cc-glm --dangerously-skip-permissions
aweswitch cx-openai --model o3
```

通过 [aweshelf](https://github.com/Webioinfo01/aweshelf) 自动 bookmark 会话：

```bash
aweswitch cc-glm -c backend -t "Fix auth bug"
```

详见 [aweshelf 集成](#aweshelf-集成)。

常用配置命令：

```bash
aweswitch config path
aweswitch config show
aweswitch config edit
```

## 自动更新

aweswitch 每次运行时会在后台检查 PyPI 是否有新版本。如果有更新，会在会话结束后在 stderr 输出提醒。

手动更新：

```bash
aweswitch self-update
```

仅检查不更新：

```bash
aweswitch self-update --check
```

禁用后台检查：

```bash
export AWESWITCH_NO_UPDATE_CHECK=1
```

## aweshelf 集成

[aweshelf](https://github.com/Webioinfo01/aweshelf) 是 Claude Code 和 Codex CLI 的会话 bookmark 管理器，可以保存、标记、搜索和恢复历史 coding 会话。

aweswitch 与 aweshelf 集成，支持在启动会话时自动完成 bookmark，无需额外操作：

```bash
aweswitch cc-glm -c backend -t "Fix auth bug"
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `-c`, `--category` | bookmark 的分类标签（如 `backend`、`research`、`infra`）。 |
| `-t`, `--title` | 自定义 bookmark 标题。不传时 aweshelf 用会话的第一条消息作为标题。 |

两个参数都需要 aweshelf 已安装。如果 aweshelf 未找到，参数会被忽略并输出警告到 stderr。Claude Code 不受影响，正常启动。

> **注意**：在同一项目目录下同时启动多个 `aweswitch -c` 会话可能导致 bookmark 标记错误。顺序启动是安全的——只要前一个会话的 JSONL 文件已创建（通常几秒内），再启动下一个就不会有问题。详见 [CONTRIBUTING.md](./docs/CONTRIBUTING.md#known-limitation-concurrent-launch-race-condition)。

### 安装 aweshelf

```bash
pip3 install aweshelf
```



即使不使用 aweswitch 的 `-c`/`-t` 参数，aweshelf 也可以独立使用：

```bash
aweshelf bookmark               # 交互式 bookmark 会话
aweshelf bookmark --current     # bookmark 当前项目最近的会话
aweshelf list                   # 列出所有 bookmark
aweshelf search "auth"          # 全文搜索 bookmark
aweshelf resume BOOKMARK_ID     # 恢复已保存的会话
aweshelf browse                 # 交互式 TUI 浏览器
```

完整文档见 [aweshelf README](https://github.com/Webioinfo01/aweshelf)。

## FAQ

### aweswitch 解决什么问题，适合谁？

`aweswitch` 适合同时使用多个 AI coding agent 运行时端点、模型或 token 来源的人。它提供一个可重复的本地命令，避免你来回手改 settings。

- **一个本地配置文件**：`~/.config/aweswitch/config.json`
- **命名 agent profile**：例如 `cc-glm`、`cc-gemini`、`cc-xiaomi`、`cx-openai`
- **并行会话**：不同终端可以启动不同 API/model 组合
- **只在运行时注入配置**：通过 provider 对应的运行参数
- **不修改全局 agent 配置**：已经打开的 agent 会话继续使用启动时的配置
- **token 引用**：来自 shell 环境变量或 `~/.claude/settings.json`
- **可读 JSON**：profile 按 `profiles.claude` 和 `profiles.codex` 分组

### aweswitch 把 profile 存在哪里？

默认路径：

```bash
~/.config/aweswitch/config.json
```

你可以用 `AWESWITCH_CONFIG` 覆盖这个路径。

### aweswitch 会修改 Claude settings 吗？

不会。它只读取 aweswitch 自己的配置，并为当前启动的 Claude Code 进程传入运行时 settings。切换 profile 不会改写全局 API endpoint 或模型，因此不会影响已经运行中的 agent 会话。

### aweswitch 支持 Codex 吗？

支持。Codex profile 在 `env` 中使用 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY`。aweswitch 通过 Codex 的 `-c` 配置覆盖注入 base URL，通过环境变量注入 API key，不会写入 `~/.codex/`。

### aweswitch 支持 Hermes 吗？

暂时不支持。配置格式已经按 provider 分组，后续可以自然扩展。

## 同类工具

### [cc-switch](https://github.com/farion1231/cc-switch)

`cc-switch` 是相邻方向的 Claude Code 切换工具。它是同一问题空间里的有用参考：让 Claude Code 的 provider/model 切换更容易通过命令行完成。

关键区别是 `aweswitch` 不改写全局配置。很多切换工具通过修改 agent 共享的 API/model settings 来完成切换；这样一来，之前已经打开的 agent 会话可能会因为底层全局 API 变化而不可用。`aweswitch` 把 profile 放在自己的 JSON 文件里，只在启动新进程时注入运行时 settings，所以每个会话都保留它启动时的 API 和模型。

`aweswitch` 目前采用更小的 Python package 路线：本地 JSON profile 文件、运行时注入（Claude Code `--settings`、Codex `-c` 参数和环境变量）、检查命令隐藏敏感字段，并保留 provider 分组以便未来支持更多 agent。

## Profile 规则

- Profile 放在 `profiles.<provider>.<profileName>` 下。
- 支持的 provider：`claude`、`codex`。
- 所有 provider 分组下的 profile 名必须全局唯一。
- `env` 只作用于本次启动的子进程。
- `${VAR_NAME}` 会从当前 shell 环境变量中展开。
- `show` 和 `config show` 会隐藏 token、key、secret、password、auth 这类敏感字段。

### Claude Profile

- 通过运行时 `--settings '{"env": ...}'` 传入 `env`。
- 模型通过 `env.ANTHROPIC_MODEL` 配置。
- token 在 shell 中不存在时，也可以从 `~/.claude/settings.json` 中展开。

`ANTHROPIC_DEFAULT_HAIKU_MODEL`、`ANTHROPIC_DEFAULT_SONNET_MODEL`、`ANTHROPIC_DEFAULT_OPUS_MODEL` 默认都不配置。如果你希望 Claude Code 对轻量任务或后台任务使用更轻的模型，可以给 profile 增加 `ANTHROPIC_DEFAULT_HAIKU_MODEL`：

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

这样主模型仍然使用 `mimo-v2.5-pro`，同时允许 Claude Code 在轻量任务中使用 `mimo-v2.5`。

### Codex Profile

- 需要 `env` 中配置 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY`。
- base URL 通过 `-c model_providers.custom.base_url=...` 注入（不写文件）。
- API key 通过环境变量注入（不写 `~/.codex/auth.json`）。
- 额外参数透传给 `codex` CLI。

Codex profile 只切换 API 源（base URL + API key），不切换模型。实际体验来看，Codex 配合 OpenAI 自身模型效果最好——常见用法是通过第三方 provider 中转，而不是换用完全不同的模型。

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

aweswitch 不会写入 `~/.codex/`。base URL 通过 Codex 的 `-c` 参数传入，API key 通过环境变量传入。你的全局 Codex 配置不会被修改。

交互式添加 Codex profile：

```bash
aweswitch add
# Provider: codex
# Profile name: cx-myprovider
# OPENAI_BASE_URL: https://myprovider.com/v1
# OPENAI_API_KEY env var name: MY_PROVIDER_KEY
```

## 开发

详见 [贡献指南](./docs/CONTRIBUTING.md)，包含环境搭建、测试、分支规范和发布流程。

- [贡献指南](./docs/CONTRIBUTING.md)
- [更新日志](./docs/CHANGELOG.md)
