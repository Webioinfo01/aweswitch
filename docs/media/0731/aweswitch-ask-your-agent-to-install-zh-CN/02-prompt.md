# Translation Prompt

## Task

Translate the English article at `aweswitch-ask-your-agent-to-install.md` into natural, engaging Simplified Chinese (zh-CN). The article is a soft-article (软文) for `aweswitch`, an open-source CLI tool. The voice is conversational, the structure is narrative, and the central conceit is meta: the user delegates the install of an agent tool to their own agent.

## Audience

- General readers who use AI coding agents (Claude Code, Codex, Cursor, etc.) but are not necessarily deeply technical.
- They are comfortable with terminal commands and JSON config files, but should not be assumed to know every internal detail of any specific tool.
- They appreciate clear prose, dry humor, and the occasional philosophical aside — but they will skip past anything that reads like a marketing pitch.

## Style

- **storytelling** (per EXTEND.md) — engaging narrative flow, smooth transitions, vivid phrasing.
- Match the tone of the existing 0622 Chinese translation: light, direct, confident, with first-person sections that feel like a developer's diary and second-person sections that feel like a friend walking you through a setup.
- The article uses a "Day in Practice" timeline with time-stamped entries. Preserve this structure exactly.
- Avoid stiff or translated-feeling Chinese. Sentences should breathe. The "I went to get a coffee" beat must land as wry understatement, not literal narration.

## Glossary (load-bearing terms)

| English | Chinese | Notes |
|---|---|---|
| profile | 配置（profile） | First prose use: "配置（profile）". After that, alternate freely; in code, keep `profile` as-is. |
| launch mode | 启动模式 | Established. |
| apply mode | 应用模式 | Established. |
| skill (the SKILL.md unit) | 技能 | First use: "aweswitch 技能（一份 SKILL.md）" or similar to disambiguate from generic "技能". |
| `/aweswitch` | `/aweswitch` | Slash command — keep code unchanged. |
| `aweswitch apply` | `aweswitch apply` | Keep code unchanged. |
| `aweswitch <profile>` | `aweswitch <profile>` | Keep code unchanged. |
| `os.execvpe` | `os.execvpe` | Keep as code. |
| `${VAR_NAME}` | `${VAR_NAME}` | Keep as code. |
| `{env:VAR}` | `{env:VAR}` | Keep as code. |
| `@glm`, `@step`, `@mimo` | `@glm`、`@step`、`@mimo` | Keep as code. |
| aweshelf / aweskill / awescholar | aweshelf / aweskill / awescholar | Sister products — keep English names. |
| agent-native | 对 agent 友好 / agent-native | First prose use: introduce as "agent-native（对 agent 友好）" then alternate. |
| session | 会话 | Standard. |
| bookmark | 书签 | aweshelf concept. |
| endpoint | 端点 | Standard technical term. |
| token | 令牌 | In prose: "令牌". In code/variable names: keep `token`. |
| README.ai.md | `README.ai.md` | Keep as code. |
| Python ≥ 3.9 / Node.js ≥ 20 | Python ≥ 3.9 / Node.js ≥ 20 | Keep as code. |
| `~/.zshrc`, `~/.bashrc`, `~/.claude/settings.json` | same (tilde-paths are international) | Keep as code. |
| `pip3 install` | `pip3 install` | Keep as code. |
| `which aweswitch` | `which aweswitch` | Keep as code. |

## Voice Rules

1. **Person shifts**: opening is first-person ("I"), instructional sections are second-person ("you"), A Day in Practice is first-person recounting the day's events.
2. **Dashes (`——`)** — preserve where the source uses them for parenthetical asides.
3. **Time stamps in "A Day in Practice"** — keep `7:42 AM` / `9:15 AM` English format to match the 0622/0627 convention. Translate the surrounding prose.
4. **Product / feature names** stay in English: `aweswitch`, `aweskill`, `aweshelf`, `awescholar`, `Webioinfo`, `OpenCode`, `Claude Code`, `Codex`, `Cursor`, `Qwen Code`.
5. **Code blocks** — never translate. All shell commands, JSON keys, file paths, and CLI flags remain as-is.
6. **Tables** — preserve structure. Translate the cells, keep code-as-code.
7. **Headings** — translate, but keep `# aweswitch: I Asked My Agent to Read a README` style. Suggest: `# aweswitch：我让 agent 替我读了一份 README`. The English subtitle after the colon can become a Chinese subtitle.
8. **No marketing-speak**. The article is a soft article, but the voice is "developer who happens to be excited about a tool", not "PR rep". Earnest understatement > hype.

## Key translation moves

- **Opening hook**: the source leads with "I told my coding agent one sentence… I went to get a coffee." Preserve the literal coffee beat — do not domesticate to "I went to grab a drink" or similar. The English coffee is a meme in dev culture; the Chinese equivalent could be "我去泡了杯咖啡" (kept coffee, slightly Chinese-ized verb). Lean toward preserving coffee.
- **Meta-narrative**: lines like "The artifact that gets delegated is not the binary — it is a *readable spec the agent can execute*" must land. In Chinese, the parallel structure can be preserved with "被委托的并不是二进制包——而是一份 agent 能读懂、能执行的说明文档" or similar.
- **The "Why It Matters" three-criteria list**: keep the criteria language close to the original. They are quotable.
- **The "Try It" CTA**: imperative, friendly, slightly informal. Do not turn it into a sales pitch.
- **"A Day in Practice" entries**: these read as a developer's diary. Keep verbs vivid (e.g. "你遇到了一个棘手的并发 bug" not "你面临一个复杂的并发问题"). The 11:30 AM entry about adding the AiHubMix codex profile is a centerpiece — the agent does the JSON diff; make that feel effortless.

## Pitfalls to avoid

- **Translating "agent" as "代理" / "代理程序"** — the 0622 translation uses "代理" for Claude Code / Codex when describing them as software. In this article, "agent" refers more often to the AI assistant the user is talking to (the thing that reads README.ai.md and runs commands). Use "agent" in English for the AI assistant sense; use "代理" only when describing the underlying software product (e.g. "AI 编码代理").
- **Translating the three-step test in Why It Matters as a numbered Chinese list that loses parallelism** — preserve the rhetorical structure.
- **"Setup is a task. Configure is a task. Both can be delegated."** — the English rhythm of three short sentences with one-word subjects. In Chinese, prefer a structure that lands with similar weight, e.g. "安装是一个任务。配置是一个任务。两个任务都可以被委托。" (or similar). Don't over-paraphrase.
- **The Table "你说什么 / 技能跑什么"** — the header should be in Chinese, the cells translated, but the code in the cells (`aweswitch list`, etc.) stays as code.

## Output

Save the draft translation to `03-draft.md` in this directory.
