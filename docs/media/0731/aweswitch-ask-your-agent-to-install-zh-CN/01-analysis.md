# Content Analysis: aweswitch-ask-your-agent-to-install.md

**Source path**: `/Users/peng/Desktop/Project/product/tools/aweswitch/docs/media/0731/aweswitch-ask-your-agent-to-install.md`
**Source word count**: 1773 words / 11328 characters
**Target language**: zh-CN
**Mode**: refined
**Audience**: general (developer-adjacent; users who use AI coding agents but may not be deeply technical)
**Style**: storytelling

## Domain

- **Primary**: Developer tools / CLI / AI agent infrastructure
- **Secondary**: Open-source project communication (release blog / soft-article)
- **Product context**: `aweswitch` is a profile switcher for AI coding agents (Claude Code, Codex, OpenCode). This article is the third in a 2026 series (after 0609, 0622, 0627) and shifts the angle from "feature announcement" to "install via agent" / "agent-native" philosophy.

## Tone & Voice

- **First-person narrator** at the opening ("I told my coding agent one sentence…", "I went to get a coffee"). Shifts to second-person ("you") for instructional sections, then back to first-person for the A Day in Practice timeline.
- **Conversational but precise** — uses developer jargon (CLI flags, env vars, JSON keys) without apologizing for it. Treats the reader as someone who runs commands in a terminal.
- **Self-aware meta-narrative** — the article is about an agent tool, written for people who use agents, and the install process itself involves an agent. The "agent installs the agent tool" framing is the central conceit.
- **Light humor** — "I went to get a coffee" is the kind of understated joke that signals shared experience among developers.
- **Closing philosophy** — "Why It Matters" shifts to a more declarative, essayistic register. Three numbered criteria function as a portable mental model.

## Terminology (load-bearing terms to handle carefully)

| English | Chinese | Notes |
|---|---|---|
| profile (aweswitch concept) | 配置（profile） | Keep `profile` in code/JSON, gloss as "配置" in prose on first use. The aweswitch concept is a named bundle of (URL, token, model). |
| launch mode | 启动模式 | Established term from 0622 translation. |
| apply mode | 应用模式 | Established term from 0622 translation. |
| skill (aweswitch SKILL.md) | 技能 | The agent-installable unit. Distinguish from "skill" as generic English. First use should clarify: "aweswitch 技能（SKILL.md）" or similar. |
| `/aweswitch` | `/aweswitch` | Slash command, keep as-is. |
| `aweswitch apply` | `aweswitch apply` | CLI command, keep code unchanged. |
| `aweswitch <profile>` | `aweswitch <profile>` | CLI invocation, keep code unchanged. |
| `os.execvpe` | `os.execvpe` | Python API call, keep as code reference. |
| `${VAR_NAME}` | `${VAR_NAME}` | Shell variable expansion syntax, keep as-is. |
| `{env:VAR}` | `{env:VAR}` | OpenCode syntax, keep as-is. |
| `@glm`, `@step` | `@glm`、`@step` | OpenCode agent invocation syntax, keep as-is. |
| `aweshelf` | aweshelf | Sister product, keep name. |
| `aweskill` | aweskill | Sister product, keep name. |
| agent-native | agent-native（或"对 agent 友好"） | Recurring thesis term. First use: clarify in context. |
| session | 会话 | Standard translation. |
| bookmark | 书签 | aweshelf concept. |
| endpoint | 端点 | Technical term, standard translation. |
| token | 令牌 / token | Use "令牌" in prose; keep "token" in code/variable names. |
| README.ai.md | `README.ai.md` | File name, keep as code. |
| Python ≥ 3.9 | Python ≥ 3.9 | Keep code as-is. |
| Node.js ≥ 20 | Node.js ≥ 20 | Keep code as-is. |

## Translation Challenges

1. **Meta-narrative arc** — the article's emotional payload is the moment when the author realizes the install itself is a task that can be delegated. This must survive translation. Avoid flattening the "coffee" beat into a literal "我离开了" — it should land as wry understatement.

2. **English-specific rhythm in "A Day in Practice"** — the time-stamped entries (7:42 AM, 9:15 AM, etc.) are a stylistic device from the 0622/0627 articles. Keep the timestamps, but adapt the verb tenses. Chinese uses different aspect markers; preserve the "present continuous, you are in the middle of doing this" feel.

3. **The "agent installs the agent tool" phrase is the article's title concept** — the Chinese title must make this self-referential joke land. Options:
   - 《aweswitch：我让 agent 替我读了一份 README》
   - 《aweswitch：当 agent 开始自己安装自己》
   - 《aweswitch：我让 AI 帮我装 AI 工具》
   
   Recommend the first — it preserves the "one sentence" / "I went to get a coffee" narrative hook most directly.

4. **Avoid translating the philosophical close too literally** — the three-criteria list ("Can another agent install it from a single prompt?" etc.) is meant to be portable. In Chinese, preserve as a numbered list and keep the criteria language close to the original so they remain quotable.

5. **Tables and code blocks** — preserve all formatting exactly. Code blocks in particular must not be translated (CLI flags, env var names, JSON keys, file paths). The "you say → skill runs" table is the article's most shareable asset; format it identically.

6. **The "self-aware" sentences risk sounding awkward in Chinese** — lines like "The future of agent tooling is not 'tools that work well with agents.' It is 'tools that the agent itself can install, configure, and operate on your behalf.'" use parallel English structure. Chinese should preserve the parallelism but may need to break the long sentence into two for readability.

7. **CTA "Try It" section** — original ends with imperative "Tell your agent: [prompt]. Then check…". The CTA should feel like a friend pointing you to a doorway, not a sales pitch. Direct, slightly informal Chinese matches the voice.

## Key voice rules to enforce

- Use "我" sparingly in the opening, then shift to "你" for instructions, then back to "我" for the A Day in Practice timeline (where first-person recounts the day's events).
- Keep dashes (`——`) where they appear in the source, since they're used to set off asides.
- Keep `aweswitch` in English throughout; do not transliterate.
- Time-stamp entries (7:42 AM etc.) should remain in English-AM/PM format to match the existing 0622/0627 translation convention.
- Preserve English-only product/feature names: `aweswitch`, `aweskill`, `aweshelf`, `awescholar`, `Webioinfo`, `OpenCode`, `Claude Code`, `Codex`.
- Preserve the `pip3 install` style commands unchanged.

## Style references

- Existing 0622 Chinese translation (`0622/aweswitch-cross-platform-codex-apply-zh-CN/translation.md`) is the closest prior art — same series, same voice, same "Day in Practice" device. Match its level of informality and its preference for natural Chinese sentence breaks over literal English structure.
- Existing 0627 translation if available.
