# In-Place Profile Switch (`aweswitch apply`)

Date: 2026-06-22

## Problem

1. **aweswitch 自动启动 cc**：`aweswitch <profile>` 用 `os.execvpe` 替换当前 shell 进程为 claude 进程，用户无法 `--resume` 之前的对话。
2. **优先级冲突**：aweswitch 通过 `--settings` 传临时文件，但 settings.json 里的硬编码字段（如 `api_key`、`model`）优先级更高，导致 profile 配置被覆盖，切换失败。

## Solution

新增 `aweswitch apply <profile>` 子命令：直接合并 profile 的 env 字段到 `~/.claude/settings.json`，只修改 profile 里定义的 key，其余字段（permissions、model 等）不动。

## Changes

### CLI (`src/aweswitch/cli.py`)

- 新增 `merge_env_into_settings()` 函数：读取 settings.json，用 profile env 覆盖对应 key，写回文件，返回变更列表。
- 新增 `apply` 子命令：解析 profile → 展开 `${ENV_VAR}` → 调用 `merge_env_into_settings` → 输出变更摘要。
- 仅支持 claude provider（codex 无法通过 settings.json 切换）。
- 幂等：重复 apply 同一 profile 输出 "No changes"。

### Skill (`~/.claude/skills/aweswitch/SKILL.md`)

- Intent Router 新增 "Switch to profile X" → `aweswitch apply <profile>`。
- 新增 "Apply Profile (In-Place Switch)" workflow。
- Core Rules 增加 `apply` 安全说明。
- 允许在 agent 内运行 `aweswitch apply`（不启动交互式子进程）。

## Usage

```bash
# 终端里直接切 profile
aweswitch apply cc-xiaomi

# 在 cc 里通过 skill 切
/aweswitch apply cc-xiaomi
```

## Notes

- cc 当前 session 是否热加载 settings.json 取决于 cc 内部实现（未验证）。如果不行，需要用 `claude --resume <id>` 重启续上。
- `apply` 不会备份 settings.json——如果需要回滚，手动改回或重新 apply 另一个 profile。
