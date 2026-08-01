# Critical Review: 03-draft.md

**Reviewer focus**: diagnosis only. No rewrites in this file.
**Style target**: storytelling, general audience, zh-CN.
**Reference**: existing 0622 Chinese translation as closest prior art.

## Summary verdict

The draft is **publication-ready with 3 substantive fixes and 5-7 minor polish items**. The voice, the meta-narrative conceit, the "Day in Practice" rhythm, and the closing three-criteria test all land well. The main gaps are: (1) the "agent-native" thesis term was dropped, losing a quotable label; (2) one small accuracy issue in describing `apply` mode; (3) one heading uses awkward "长尾" for a non-statistical context.

---

## A. Accuracy issues (must fix)

### A1. "然后退出" misrepresents `apply` mode
- **Location**: "What the agent will not do" section, draft line ~30.
- **Source**: "It writes the profile's env into `~/.claude/settings.json` and exits. No interactive sub-process."
- **Issue**: "然后退出" in Chinese implies the user is "in" something and the agent "exits" it. The original "and exits" is from the CLI process's perspective — it returns to its caller. Net effect is correct, but phrasing is misleading.
- **Fix**: change to "写完即返回" or "完成写入后返回". Keep "不会启动交互式子进程" as the next sentence — that one is correct.

### A2. "agent-native" thesis term dropped
- **Location**: "Why It Matters" section, especially the closing sentence.
- **Source**: "The future of agent tooling is not 'tools that work well with agents.' It is 'tools that the agent itself can install, configure, and operate on your behalf.'"
- **Issue**: The source builds its entire closing around the term **"agent-native"** as a portable, quotable label. I paraphrased around it ("agent 工具", "agent 自己能装、能配、能替你用的工具") and the label vanished. The term appears earlier too: "agent-native tools are installable by other agents" (the "It Matters" lead) and "this is the test I now apply to every agent tool" (the criteria follow).
- **Fix**: reintroduce "agent-native" once, glossed: "agent-native（对 agent 友好的）" or "agent-native 工具（对 agent 友好的工具）". Use it 2-3 times in the closing argument. Keep my paraphrases for variety, but the term itself must reappear so readers can quote it.

### A3. "long tail" heading mistranslated
- **Location**: heading "## OpenCode、Codex，以及长尾".
- **Source**: "## OpenCode, Codex, and the Long Tail"
- **Issue**: "长尾" in Chinese dev/marketing context usually means the statistical long tail (e.g. niche products making up the bulk of the catalog). Here "the long tail" is colloquial for "the broader range of providers". A Chinese reader will misread the heading.
- **Fix**: change to "## OpenCode、Codex，以及更多" or "## OpenCode、Codex 与其他 provider". Drop the "long tail" framing entirely.

---

## B. Strategy execution (gaps vs. 01-analysis)

### B1. The "agent-native" test list is missing the label
- **Location**: "Why It Matters" three criteria.
- **Source**: "This is the test I now apply to every agent tool I evaluate: 1. Can another agent install it from a single prompt? 2. Can another agent use it from natural language after install? 3. Does the install require changes to my shell or global config that I have to maintain by hand?"
- **Issue**: My translation is faithful to the wording but loses the framing: "This is the **test** I now apply." Without naming it as a "test", the three criteria feel like a passing list rather than a portable framework. The fix in A2 helps; also consider calling it "一套测试标准" or "三个测试问题" — give it a name.

### B2. "Day in Practice" doesn't match source's emotional arc at 11:30 AM
- **Location**: 11:30 AM entry, the "Add a codex profile for AiHubMix" beat.
- **Source**: "No copy-paste. No 'let me find the docs.' The agent did the part you do not enjoy."
- **My version**: "没有复制粘贴，没有'让我翻一下文档'。agent 替你做了你最不想做的那部分。"
- **Issue**: Translation is accurate but flat. The source's emotional beat is the contrast between **annoyance** (copy-paste, finding docs) and **relief** (the agent does it). My version reads more like a feature list.
- **Fix**: in revision, add a beat of relief. Example: "没有复制粘贴，没有'让我翻一下文档'。这些你最烦的活，agent 顺手就替你做完了。"

### B3. Final CTA underplays the philosophical close
- **Location**: "试试看" section.
- **Source**: "Tell your agent: [prompt]. Then check that /aweswitch appears in the skill list. If it does, you are thirty seconds away from a new profile. If it does not, restart the agent. From there, the questions become ordinary: 'Add a codex profile for AiHubMix.' 'Show me which profile is active.' 'Switch to cc-xiaomi so I can use /model.' The agent already knows the answers. You just had not given it the README yet."
- **My version**: faithful but the closing line "agent 已经知道答案。你只是还没把那份 README 递给它。" is good; the middle "剩下的就是些普通问题" is fine but slightly weakened by "都". Keep most, just polish.
- **Fix**: minor — see polish list.

---

## C. Europeanized language / translation-speak

No serious issues. The "agent / 技能 / profile / 配置 / 启动模式 / 应用模式 / 路由 / 管道" vocabulary is all appropriate for the audience. A few small items:

### C1. "OpenCode 自带的 `@`-agent 调用"
- **Location**: "OpenCode、Codex..." section, second paragraph.
- **Issue**: "OpenCode 自带的 X" reads slightly broken; "自带" is more commonly used for physical attributes or built-in features that the user discovers, not features described functionally.
- **Fix**: "OpenCode 的 `@`-agent 调用功能" or "通过 OpenCode 的 `@`-agent 调用，...".

### C2. "这也是 agent 干任务的本意" — not present in draft. Skip.

### C3. "agent 干任务"
- **Location**: opening hook, after "我把任务派给了 agent".
- **Issue**: "干" is colloquial for "做". Fits the voice (developer diary), but the source's "The agent does tasks" is just descriptive. The colloquial tone works because the next sentence also uses informal voice. Keep, but verify the surrounding sentences still feel consistent.

---

## D. Expression issues (polish list)

### D1. Parallel structure in "Install is a task. Configure is a task."
- **Source**: "Install is a task. Configure is a task. Both can be delegated."
- **My version**: "安装是一个任务。配置是一项任务。两个任务都可以被委托。"
- **Issue**: "一个" vs "一项" — minor inconsistency. Both are grammatical in Chinese, but for parallel structure prefer one measure word.
- **Fix**: pick one. Suggest "项" for both: "安装是一项任务。配置是一项任务。两个任务都可以被委托。"

### D2. "这是我现在评估每一个 agent 工具时会用的一套标准"
- **Issue**: "现在" is not in the source. Source: "The test I now apply to every agent tool I evaluate." Trim "现在".
- **Fix**: "这是我评估每一个 agent 工具时会用的一套标准".

### D3. "三个 / 三条 都过"
- Source: "aweswitch passes all three."
- My version: "aweswitch 三条都过."
- **Issue**: "三条都过" is colloquial, fits voice. Keep.

### D4. "我让 agent 替我读了一份 README" (title)
- **Source title**: "I Asked My Agent to Read a README"
- **Issue**: "替" is stiff; "帮我" is more natural. But "替" carries the "in place of" sense that fits the meta-narrative. Either works; I'd lean toward "帮我" for smoother Chinese.
- **Fix**: change to "我让 agent 帮我读了一份 README". If "替" is kept, accept it as a stylistic choice.

### D5. "它会做剩下的事" — fine.

### D6. "agent 会照做"
- **Source**: "the agent respects it"
- **My version**: "agent 会照做"
- **Issue**: works, slightly flat. "agent 也会照做" might add a touch of "of course, naturally". Minor.

### D7. "它反正都是每次重新启动"
- **Source**: "they are launched fresh each time anyway"
- **My version**: "它反正都是每次重新启动"
- **Issue**: "它反正都是" is slightly sloppy; the "它" (singular) refers to OpenCode and Codex collectively, which is awkward. "它们反正都是" or "反正都是每次重新启动" reads better.
- **Fix**: drop the "它". "反正都是每次重新启动" works.

### D8. "agent 还会..." — not present.

### D9. "三个 profile、两个并行会话、新加了一条 profile、四条书签"
- **Source**: "Three profiles, two parallel sessions, one new profile added during the day, four bookmarks."
- **My version**: "三个 profile、两个并行会话、新加了一条 profile、四条书签"
- **Issue**: the parallel structure is preserved but "新加了一条" breaks the "number + noun" pattern of the others. Acceptable since the source also breaks the pattern with "one new profile added". Keep.

### D10. The table headers
- **Source**: "You say" / "The skill runs"
- **My version**: "你说什么" / "技能跑什么"
- **Issue**: "你说什么" is colloquial — fits voice. "技能跑什么" is good. The verb "跑" (run) for "runs" is colloquial but works in the same register. Keep.

### D11. Heading "技能栈：它能触达什么"
- **Source**: "The Stack: What the Skill Can Reach"
- **Issue**: "技能栈" preserves "stack" but is a bit techy. "它能触达什么" is good. Keep, but the colon-after-Stack convention may be a Western thing. Acceptable.

### D12. "另一半：会话记忆"
- **Source**: "The Other Half: Session Memory"
- **Issue**: works in Chinese. Keep.

### D13. "Webioinfo 出品"
- **Source**: "More from Webioinfo"
- **Issue**: "出品" is a bit formal/film-credits-feel for the context. But it has rhythm. The existing 0622 translation likely uses similar phrasing — let me note as "verify against 0622" but keep current.

---

## E. Code references — all preserved ✓

Spot-checked: `~/.config/aweswitch/config.json`, `~/.zshrc`, `~/.claude/settings.json`, `pip3 install aweswitch`, `aweswitch -v`, `aweswitch config init`, `aweswitch add`, `aweswitch <profile>`, `aweswitch apply`, `aweswitch apply cc-glm`, `aweswitch restore`, `aweswitch list`, `aweswitch show`, `aweswitch cx-aihubmix --model o3`, `aweswitch cc-glm -c backend -t "..."`, `aweswitch oc-glm glm-5.1 -c docs -t "..."`, `aweshelf browse`, `aweshelf resume`, `aweshelf search`, `os.execvpe`, `${AIHUBMIX_OPENAI_KEY}`, `{env:VAR}`, `@glm`, `@step`, `@mimo`, `~/.claude/skills/aweswitch/`, `~/.config/opencode/opencode.json`, `aweskill`, `aweshelf`, `awescholar`, `Webioinfo`, `OpenCode`, `Claude Code`, `Codex`, `Cursor`. All preserved correctly in code blocks and inline code.

## F. Image references

Single hero image: `../../../logo/hero.png`. Same as 0622/0627. No change needed. The image is the project logo (no localized text), so no image-language pass is required for the hero.

---

## Priority summary for revision

**Must fix (substantive):**
1. A1 — "然后退出" → "写完即返回"
2. A2 — reintroduce "agent-native" thesis term (2-3 occurrences in Why It Matters)
3. A3 — "长尾" → "以及更多" or similar

**Should fix (polish):**
4. B2 — punch up the 11:30 AM relief beat
5. B3 — minor CTA polish
6. C1 — "OpenCode 自带的" → "OpenCode 的 ... 功能"
7. D1 — "一个/一项" parallel structure
8. D2 — drop "现在" 
9. D4 — "替" → "帮我" (or accept stylistic choice)
10. D7 — drop "它" before "反正都是"
11. B1 — give the three-criteria test a name

**Optional:**
12. D6 — "agent 会照做" → "agent 也会照做" (very minor)
13. D13 — verify "Webioinfo 出品" against 0622 prior art
