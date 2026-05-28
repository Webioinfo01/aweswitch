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
    <img src="https://img.shields.io/badge/version-0.1.3-7C3AED?style=flat-square" alt="Version">
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

> 让不同 agent profile 并行运行，同时不影响已经打开的会话。

`aweswitch` 从 `~/.config/aweswitch/config.json` 读取 profile，展开环境变量引用，准备 provider 对应的运行时参数，然后启动所选 agent。每次启动都会拿到自己的 API endpoint、token 和模型；这些配置通过运行时参数注入，而不是改写全局 agent settings。

它刻意保持小而直接。项目定位是 agent profile switcher，但目前只支持 Claude Code profile。配置格式为以后加入 Codex 或 Hermes 预留了 provider 分组，但这些 provider 现在还不能执行。

## 安装

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
    }
  }
}
```

配置 profile 引用的 token 环境变量：

```bash
export GLM_ANTHROPIC_AUTH_TOKEN="..."
export GEMINI_ANTHROPIC_AUTH_TOKEN="..."
export XIAOMI_ANTHROPIC_AUTH_TOKEN="..."
```

如果希望每次打开终端都可用，可以把这些变量放进 `~/.zshrc`。

验证配置后的 profile：

```bash
aweswitch list
aweswitch show cc-glm
```

启动 profile：

```bash
aweswitch cc-glm
```

额外参数会透传给 Claude Code：

```bash
aweswitch cc-glm --dangerously-skip-permissions
```

常用配置命令：

```bash
aweswitch config path
aweswitch config show
aweswitch config edit
```

## FAQ

### aweswitch 解决什么问题，适合谁？

`aweswitch` 适合同时使用多个 AI coding agent 运行时端点、模型或 token 来源的人。它提供一个可重复的本地命令，避免你来回手改 settings。

- **一个本地配置文件**：`~/.config/aweswitch/config.json`
- **命名 agent profile**：例如 `cc-glm`、`cc-gemini`、`cc-xiaomi`
- **并行会话**：不同终端可以启动不同 API/model 组合
- **只在运行时注入配置**：通过 provider 对应的运行参数
- **不修改全局 agent 配置**：已经打开的 agent 会话继续使用启动时的配置
- **token 引用**：来自 shell 环境变量或 `~/.claude/settings.json`
- **可读 JSON**：profile 按 `profiles.claude` 分组

### aweswitch 把 profile 存在哪里？

默认路径：

```bash
~/.config/aweswitch/config.json
```

你可以用 `AWESWITCH_CONFIG` 覆盖这个路径。

### aweswitch 会修改 Claude settings 吗？

不会。它只读取 aweswitch 自己的配置，并为当前启动的 Claude Code 进程传入运行时 settings。切换 profile 不会改写全局 API endpoint 或模型，因此不会影响已经运行中的 agent 会话。

### aweswitch 支持 Codex 或 Hermes 吗？

暂时不支持。配置格式已经按 provider 分组，后续可以自然扩展，但目前可执行 provider 只有 Claude Code。

## 同类工具

### [cc-switch](https://github.com/farion1231/cc-switch)

`cc-switch` 是相邻方向的 Claude Code 切换工具。它是同一问题空间里的有用参考：让 Claude Code 的 provider/model 切换更容易通过命令行完成。

关键区别是 `aweswitch` 不改写全局配置。很多切换工具通过修改 agent 共享的 API/model settings 来完成切换；这样一来，之前已经打开的 agent 会话可能会因为底层全局 API 变化而不可用。`aweswitch` 把 profile 放在自己的 JSON 文件里，只在启动新进程时注入运行时 settings，所以每个会话都保留它启动时的 API 和模型。

`aweswitch` 目前采用更小的 Python package 路线：本地 JSON profile 文件、只通过 Claude Code 运行时 `--settings` 注入、检查命令隐藏敏感字段，并保留 provider 分组以便未来支持更多 agent。

## Profile 规则

- Profile 放在 `profiles.<provider>.<profileName>` 下。
- 目前只支持 `claude` provider。
- 所有 provider 分组下的 profile 名必须全局唯一。
- Claude profile 会通过运行时 `--settings '{"env": ...}'` 传入 `env`。
- Claude 模型通过 `env.ANTHROPIC_MODEL` 配置。
- `env` 只作用于本次启动的子进程。
- `${VAR_NAME}` 会从当前 shell 环境变量中展开。
- Claude token 在 shell 中不存在时，也可以从 `~/.claude/settings.json` 中展开。
- `show` 和 `config show` 会隐藏 token、key、secret、password、auth 这类敏感字段。

## Claude 模型覆盖

对于 Claude profile，`ANTHROPIC_MODEL` 是主模型配置。

`ANTHROPIC_DEFAULT_HAIKU_MODEL`、`ANTHROPIC_DEFAULT_SONNET_MODEL`、`ANTHROPIC_DEFAULT_OPUS_MODEL` 默认都不配置。

如果你希望 Claude Code 对轻量任务或后台任务使用更轻的模型，可以给 profile 增加 `ANTHROPIC_DEFAULT_HAIKU_MODEL`：

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

## 开发

运行测试：

```bash
python3 tests/test_aweswitch.py
```

运行语法检查：

```bash
python3 -m py_compile src/aweswitch/cli.py tests/test_aweswitch.py
```

安装当前仓库的 editable 版本：

```bash
pip3 install -e .
```

构建本地安装包：

```bash
pip3 install build
python3 -m build
```

本地安装构建出的 wheel：

```bash
pip3 install dist/aweswitch-0.1.3-py3-none-any.whl
```

项目文档：

- [贡献指南](./docs/CONTRIBUTING.md)
- [更新日志](./docs/CHANGELOG.md)
