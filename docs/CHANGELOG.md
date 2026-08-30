# change log

## v0.5.2

`v0.5.2` simplifies OpenCode Responses configuration to a single knob: `OPENCODE_RESPONSES_MODEL` now works on its own, and the provider-wide `OPENCODE_RESPONSES` flag is gone.

### `OPENCODE_RESPONSES_MODEL` stands alone, `OPENCODE_RESPONSES` removed

`OPENCODE_MODEL` is no longer required when `OPENCODE_RESPONSES_MODEL` is set — the two fields have equal standing, so the responses list becomes the profile's full model list, with every model running on the Responses API (`@ai-sdk/openai`). Mixing is still supported: set both fields to keep the rest of the models on chat completions. A profile with neither field is rejected. Model order is deterministic: `OPENCODE_MODEL`'s order leads the merged list when present, responses-only models are appended in configured order, and the no-arg launch default follows that order.

The `OPENCODE_RESPONSES` boolean is removed. Profiles that set it no longer switch the whole provider to `@ai-sdk/openai`; a provider entry still carrying the responses npm from an older version is reset to `@ai-sdk/openai-compatible` on the next launch or `aweswitch apply`, and per-model overrides from `OPENCODE_RESPONSES_MODEL` are stamped on top. Hand-set vendor npm values are never touched.

### Highlights

- `OPENCODE_MODEL` is optional when `OPENCODE_RESPONSES_MODEL` lists the models (Responses-only profiles need one field)
- `OPENCODE_RESPONSES` boolean removed — use `OPENCODE_RESPONSES_MODEL` per model, or omit `OPENCODE_MODEL` to run everything on Responses
- Stale provider-level `@ai-sdk/openai` npm from v0.5.1 configs is reverted to the chat package automatically

## v0.5.1

`v0.5.1` lets OpenCode profiles speak the OpenAI Responses API: some backends only accept `/responses`, and until now every aweswitch-managed provider was pinned to chat completions.

### Responses API support for OpenCode profiles

`OPENCODE_RESPONSES` switches the provider's npm package between the default `@ai-sdk/openai-compatible` (chat completions, `/chat/completions`) and `@ai-sdk/openai` (Responses API, `/responses`) when set to true. Backends whose models only speak the Responses protocol now work without hand-editing `opencode.json`. The flag is owned by aweswitch like the other provider fields: launch and `aweswitch apply` both rewrite it when it differs, so clearing it reverts the provider to the chat package, and hand-set vendor SDK npm values are never touched.

`OPENCODE_RESPONSES_MODEL` is the mixed-protocol escape hatch: a comma-separated string or list of model IDs that get a per-model Responses override (`"provider": {"npm": "@ai-sdk/openai"}` on that model entry) while the rest of the provider stays on chat. Every ID must exist in `OPENCODE_MODEL` — a mismatch is rejected as a config typo. Clearing the list removes the stale overrides on the next sync. Orphan detection now recognizes both openai packages, so providers created in Responses mode are still reported and pruned correctly after a profile is renamed or deleted.

### Highlights

- New `OPENCODE_RESPONSES` env var: switch a whole OpenCode provider between chat completions and the Responses API
- New `OPENCODE_RESPONSES_MODEL` env var: per-model Responses overrides for mixed-protocol backends
- Both flags sync on launch and `aweswitch apply`; clearing them reverts cleanly
- Hand-written provider/model entries with a vendor npm are never modified

## v0.5.0

`v0.5.0` restores compatibility with codex 0.150+: launching any codex profile (`aweswitch cx-...`) failed with `model_providers.custom: provider name must not be empty` because the launch path injected the provider without a `name`.

### Codex 0.150 compatibility

codex 0.150 added a validation requiring every `model_providers` entry to carry a non-empty `name`. The apply path already wrote `name = "custom"` into `config.toml`, but the launch path's `-c` injection only carried `base_url` / `wire_api` / `env_key`, so every launch died at config load. Launches now inject `model_providers.custom.name="custom"` as well — the field is a long-standing provider key, so older codex versions accept it unchanged.

### Highlights

- Codex profile launches work again on codex 0.150+ (provider `name` injected via `-c`, matching what apply writes)
- Test suite runs on Python 3.9 without `tomllib`

## v0.4.8

`v0.4.8` completes the v0.4.7 model-matching promise: typing `aweswitch cx-aihubmix GPT` now actually finds `gpt-5.2-codex`. Short inputs match as case-insensitive substrings of model IDs and display names, instead of demanding a full exact replica.

### Case-insensitive substring matching

v0.4.7 shipped case-insensitive comparison, but it only matched when the input equaled a full model ID or display name — so the changelog example (`GPT` → `gpt-5.2-codex`) still failed. `select_model` now adds a third pass: after exact and case-insensitive matches miss, the input is matched as a case-insensitive substring of both IDs and display names.

Matching order: exact ID → exact display name → case-insensitive full match → case-insensitive substring. A unique match wins; multiple candidates fail with the same actionable error listing them.

### Highlights

- Launch args now resolve as case-insensitive substrings, so `GPT` selects `gpt-5.2-codex`
- Exact-match-first behavior unchanged; substring is the last fallback
- Ambiguous substring matches are rejected with the list of matching candidates

## v0.4.7

`v0.4.7` adds case-insensitive model matching: typing `aweswitch cx-aihubmix GPT` now finds `gpt-5.2-codex` instead of demanding an exact replica of the ID or display name.

### Case-insensitive model matching

When launching with a model argument, `select_model` first tries an exact match against model IDs and display names (unchanged). If nothing matches exactly, a case-insensitive comparison runs as a fallback across both model IDs and display names. This lets users type model names the way they'd naturally say them — `GPT-5.2-CODEX`, `doubao-seed-evolving`, `SEED` — without needing to match the exact casing configured in the profile.

Ambiguous case-insensitive matches still fail with the same actionable error as before, listing the candidates that matched.

### Highlights

- Launch args match model IDs and display names case-insensitively as a fallback after exact match fails
- No change to exact-match-first behavior; case-insensitive is a second pass
- Ambiguous case-insensitive matches are rejected with the list of candidates

## v0.4.6

`v0.4.6` makes bulk OpenCode apply explicit: bare `aweswitch apply` no longer implicitly writes every OpenCode profile — use `aweswitch apply --opencode` instead, so the default behavior is always intentional.

### Explicit bulk OpenCode apply

The old behavior of `aweswitch apply` with no arguments was to silently apply every OpenCode profile, which surprised users who forgot they had multiple OpenCode profiles. The new `--opencode` flag makes bulk write opt-in. Calling `aweswitch apply` with no arguments now prints a clear error showing both options.

### Highlights

- New `--opencode` flag: `aweswitch apply --opencode` writes every OpenCode profile
- `aweswitch apply` with no arguments now errors with a helpful usage hint instead of silently bulk-applying
- Passing both `--opencode` and explicit profile names is rejected with an actionable error

## v0.4.5

`v0.4.5` extends `apply` to all three agents — Claude, Codex, and OpenCode — so a profile's provider settings can be written directly into each agent's live config, and hardens the apply paths against hand-edited configs.

### Apply for all three agents

`aweswitch apply` now covers Claude (`settings.json`), Codex (`config.toml` via a surgical TOML edit with a `.toml.bak` backup, `env_key` resolved from `${VAR}` references), and OpenCode (provider upsert carrying the full model list; an existing provider is overwritten, a missing one is added). Bare `aweswitch apply` applies every OpenCode profile in bulk, while at most one Claude and one Codex profile per call. Launching an OpenCode profile with `-s` warns when the session's stored model differs from the requested one, since OpenCode restores the session model and ignores `-m`.

OpenCode profiles that were renamed or deleted could leave stale provider entries behind: apply now warns about these orphans and supports `--prune-orphans` to remove them safely. Namespaced model IDs (for example `hub/x`) are shown in full to avoid ambiguous picker rows from different producers.

### Hardening

- Hand-edited OpenCode entries (plain-string model values, non-object options/models) are repaired instead of crashing with `AttributeError`
- Codex table-header detection skips lines inside multi-line strings, so a `developer_instructions` body starting with `[` can no longer misplace top-level keys
- `sync_opencode_profiles --names ""` no longer falls back to applying all profiles
- SQLite read-only open uses `Path.as_uri` so Windows drive-letter paths form a valid URI
- Internal: removed an unreachable return after `die()` in `select_model`

### Highlights

- `apply` writes provider settings for all three agents: Claude, Codex, and OpenCode
- Bare `aweswitch apply` bulk-applies every OpenCode profile
- `apply --prune-orphans` removes stale OpenCode provider entries left by renames or deletes
- Warn when resuming an OpenCode session whose stored model differs from the requested one
- Apply paths tolerate hand-edited configs instead of crashing

## v0.4.2

`v0.4.2` lets launch arguments use a configured model's display value while preserving the full model ID passed to the agent.

### Model selection by display value

When a profile defines model IDs and display values as a mapping, the launch argument may use either form. The full model ID remains the value passed to the underlying agent, and duplicate display values fail with an actionable error.

### Highlights

- OpenCode and Codex launch commands can select a model by its configured display value, such as `step-router-v1` for `peng1/step-router-v1`
- Ambiguous display values are rejected with the matching model IDs instead of selecting one silently

## v0.4.1

`v0.4.1` reorganizes settings backup handling under `config`: a new `aweswitch config backup` command creates a settings backup and prints its path, and `restore` moves under `config` while gaining the ability to restore from an explicit backup file.

### Backup and restore under `config`

`aweswitch config backup` copies `~/.claude/settings.json` to `settings.json.bak` and prints the backup path. Like `apply`, an existing backup is not overwritten unless `--force` is given. The top-level `aweswitch restore` command is replaced by `aweswitch config restore [FILE]`: without arguments it restores from the default `settings.json.bak`; with a file argument it restores from that snapshot, so older timestamped backups can be rolled back to explicitly.

### Highlights

- New `aweswitch config backup`: back up settings on demand and print the backup path (`--force` to overwrite)
- `restore` moved to `config restore [FILE]`: restore from the default backup or any explicit snapshot file
- Internal: `die()` typed as NoReturn, clearing type-checker false positives

## v0.4.0

`v0.4.0` adds official-login accounts: multiple Claude Code and Codex OAuth logins can now be saved as accounts and launched side by side, each through a private config dir. The config schema gains an `api`/`accounts` split under `profiles`; old configs are migrated automatically on first load.

### Official accounts (Claude Code / Codex OAuth)

`aweswitch account login codex work` runs `codex login` inside a per-account runtime dir and captures the resulting credentials; `aweswitch account add codex work` imports the currently logged-in account from the live `~/.codex/auth.json` / `~/.claude/.credentials.json`. Launching works like any profile: `aweswitch cxo-work` starts the CLI with `CODEX_HOME` (codex) or `CLAUDE_CONFIG_DIR` plus `CLAUDE_CODE_DONT_USE_KEYCHAIN=1` (claude) pointed at the account dir, so several official accounts can run simultaneously without touching the global `~/.codex` or `~/.claude`.

Credentials are stored as opaque blobs in `config.json` (`profiles.accounts.<provider>.<name>`), treated as unreadable by aweswitch, and masked entirely in `show` / `config show`. Once an account dir exists it is the source of truth (the CLI refreshes OAuth tokens there); `aweswitch account sync` copies refreshed tokens back into the config, and an existing credentials file is never overwritten by a stale blob. The config file is chmod 600 when the first account is added.

### Config schema v2

Profiles now live under `profiles.api.<provider>` and accounts under `profiles.accounts.<provider>`, with names unique across both trees. Loading a pre-0.4 config transparently moves it to the new layout (a `.json.bak` backup is written first); configs that mix both layouts are rejected with a clear error. `aweswitch list` prints a kind column (`api` / `account`).

### Highlights

- Official-login accounts for Claude Code and Codex with per-account private config dirs
- `aweswitch account add / login / sync / remove [--purge]` command group
- Side-by-side official accounts: launch isolation via `CODEX_HOME` / `CLAUDE_CONFIG_DIR`
- Config schema v2 (`profiles.api` + `profiles.accounts`) with automatic migration and backup
- Account credential blobs masked entirely in `show` / `config show`; config chmod 600 on first account
- `list` output gains an api/account kind column
- `apply` restricted to claude **api** profiles (accounts are launch-only)

## v0.3.9

`v0.3.9` hardens the runtime against corrupt configs and fixes the auto-bookmark worker so it survives agent launches on POSIX. Editable installs now report the correct version after bumps.

### Version detection

`aweswitch.__version__` now reads from `pyproject.toml` when running from source, instead of relying on `importlib.metadata` which freezes the installed dist-info version at install time. This fixes stale version reports after bumps in editable installs.

### Config parsing

JSON loading now uses explicit `encoding="utf-8"` across the config, OpenCode, and update-check paths, and handles `UnicodeDecodeError` alongside `JSONDecodeError`.

`load_opencode_config` now validates the top-level structure and the `provider` key before returning. Corrupt or unexpected JSON causes a loud exit instead of silently falling through to `write_opencode_config`, which could otherwise clobber the user's `opencode.json`.

### Auto-bookmark worker

The background bookmark worker now runs in a detached forked child on POSIX. The previous daemon-thread approach died before its first poll because `os.execvpe()` destroys every thread in the process during agent launch. On Windows the launch path uses `subprocess.run()`, which keeps this process alive, so the daemon thread is retained there.

### Editor fallback

`aweswitch config edit` now reports a clear error when the configured editor binary is not found, instead of raising an unhandled `FileNotFoundError`.

### Highlights

- Read version from `pyproject.toml` for editable installs
- Harden JSON loading with explicit UTF-8 and `UnicodeDecodeError` handling
- Fail loudly on corrupt `opencode.json` instead of silently overwriting it
- Fork detached bookmark worker on POSIX to survive `execvpe()`
- Clear error when editor binary is missing in `config edit`
- Skip PyPI update check on bare invocation

## v0.3.8

`v0.3.8` softens auth-token validation across Claude and OpenCode profiles: plaintext values are now allowed with a tip instead of a hard error, reducing friction for users who don't need `${VAR}` references.

### Highlights
- **Plaintext API keys allowed with a tip**: `OPENCODE_API_KEY` and `ANTHROPIC_AUTH_TOKEN` now emit a warning when the value is not a `${VAR_NAME}` env reference, but no longer block launch. The env-ref form is still recommended to keep keys out of the config file.
- **Claude auth validation aligned with Codex/OpenCode**: `ANTHROPIC_BASE_URL` is now required (existence check), and `ANTHROPIC_AUTH_TOKEN` format is checked with the same warn-only policy.
- **Model list display**: `aweswitch list` now renders `OPENAI_MODEL` / `OPENCODE_MODEL` correctly when they are dicts, lists, or comma-separated strings.

### Docs
- README: added `awerouter` to the companion tools list.

## v0.3.7

`v0.3.7` lets Codex profiles select a model at launch, and keeps OpenCode provider entries in sync when their credentials change.

### Third-party models for Codex profiles

Codex profiles now support an optional `OPENAI_MODEL` (dict, list, or comma-separated string), following the same convention as OpenCode profiles: `aweswitch cx-<name> [model]` picks the model at launch, defaulting to the first entry. The model is injected via Codex `-c` config overrides, so nothing is written to `~/.codex/`. Without the key, the profile keeps the legacy behavior of only switching the API source.

### Sync stale OpenCode provider entries

When an OpenCode profile's `OPENCODE_BASE_URL` or `OPENCODE_API_KEY` changes, `aweswitch` now updates the existing provider entry in `~/.config/opencode/opencode.json` to match instead of erroring with "different credentials". The entry is owned by aweswitch (its name is the profile name), so the aweswitch config is the source of truth. The API key is always stored as an `{env:VAR}` reference — the resolved key is no longer passed through internal launch state.

### Highlights

- Add optional `OPENAI_MODEL` for Codex profiles: `aweswitch cx-<name> [model]`
- Support dict/list/string model formats for Codex, same as OpenCode
- Update stale OpenCode provider credentials instead of failing
- Drop internal plaintext API key from launch state; only `{env:VAR}` refs are written

## v0.3.6

`v0.3.6` fixes a profile-switching bug where a Claude profile could launch against the wrong model.

### Default unset model tiers to ANTHROPIC_MODEL

When launching a Claude profile, `aweswitch` now defaults every model-tier env var it does not explicitly set — `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`, and `ANTHROPIC_DEFAULT_FABLE_MODEL` — to the profile's `ANTHROPIC_MODEL`.

Previously only the OPUS tier was defaulted. Claude Code merges the `--settings` file with `~/.claude/settings.json`, so a tier the profile left unset inherited a stale model mapping from a previous provider. If the selected `/model` tier was one of those, the request resolved to a model the current provider does not serve (for example, a minimax profile erroring with "selected model (mimo-v2.5)"). Explicit per-tier overrides in a profile are preserved.

### Highlights

- Default all unset Claude model tiers (OPUS/SONNET/HAIKU/FABLE) to `ANTHROPIC_MODEL`
- Prevent stale tier→model mappings from leaking across providers via settings merge
- Preserve explicit per-tier model overrides in profiles

## v0.3.5

`v0.3.5` improves the Windows experience with PowerShell-first agent launcher routing and updated documentation. Windows users can now run `aweswitch` against PowerShell-installed agent binaries without manual script invocation.

### Windows PowerShell support

When resolving the agent command on Windows, `aweswitch` now prefers `shutil.which` with PATHEXT resolution (`.cmd`, `.exe`, `.bat`, `.ps1`). `.ps1` scripts are automatically routed through `powershell.exe -ExecutionPolicy Bypass -File`, matching how users typically install Claude Code and other agent CLIs on Windows.

### PowerShell env-var documentation

Setup docs in both READMEs and the bundled skill now document `setx` for persisting tokens on Windows, so `cmd` and PowerShell agree on the same persistent environment without requiring shell-specific rc files.

### OpenCode documentation

The READMEs and AI bootstrap guide now include full OpenCode provider examples, covering the three supported `OPENCODE_MODEL` formats and the `{env:VAR}` key storage policy.

### Cross-platform README updates

Both READMEs now advertise cross-platform support explicitly with updated badges and a one-line positioning statement.

### Highlights

- Route `.ps1` agent binaries through PowerShell automatically on Windows
- Prefer `setx` for persistent Windows env vars in setup docs
- Documented PowerShell env-var setup in READMEs and skill
- Added OpenCode provider documentation with model format examples
- Updated README badges to show `ubuntu | macOS | windows`
- Added cross-platform positioning line to both READMEs

## v0.3.3

`v0.3.3` hardens several runtime paths and cleans up version management.

### OpenCode API key validation

`OPENCODE_API_KEY` must now be an environment variable reference (`${VAR_NAME}`). Plain-text keys are rejected at startup with a clear error message, preventing accidental secret writes to `opencode.json`.

### Temp settings cleanup

Temporary settings files in `/tmp/aweswitch/` are now garbage-collected on each launch. Files older than 24 hours are removed before creating a new one, preventing unbounded accumulation.

### Backup error handling

`aweswitch apply` now fails with a clear message if the settings backup cannot be created (e.g. disk full), instead of silently continuing and overwriting the original.

### Highlights

- Reject plain-text `OPENCODE_API_KEY`; require `${VAR}` env-ref syntax
- Auto-clean temp settings files older than 24h
- Die with clear message if settings backup fails
- Parse pre-release version suffixes (e.g. `0.3.0a1`) correctly
- Use `pyproject.toml` as single version source; `__init__.py` reads via `importlib.metadata`
- Switch README version badges to PyPI dynamic badge

## v0.3.2

`v0.3.2` adds OpenCode as a supported provider, alongside Claude Code and Codex. Profiles targeting OpenCode are written to `~/.config/opencode/opencode.json` and launched via `opencode -m <provider>/<model>`. This release also refreshes documentation for the new provider and normalizes model handling across formats.

### OpenCode provider support

Profiles can now target OpenCode. Set `"provider": "opencode"` in a profile (or select "opencode" in `aweswitch add`) and provide `OPENCODE_BASE_URL`, `OPENCODE_API_KEY`, and `OPENCODE_MODEL`. aweswitch writes the provider entry to `~/.config/opencode/opencode.json` on first launch, using `{env:VAR}` syntax so the API key is never stored on disk. The model is passed as a positional argument: `aweswitch oc-<profile> <model>`. If no model is given, the first model in `OPENCODE_MODEL` is used.

### Model format normalization

`OPENCODE_MODEL` now accepts three formats and normalizes them consistently:

- **Dict** — `{"glm-5.1": "GLM-5.1"}` — model `name` uses the display value
- **List** — `["glm-5.1", "glm-5.2"]` — model `name` uses the list key
- **String** — `"glm-5.1,glm-5.2"` — model `name` uses the first key

### Documentation refresh

Both READMEs and the bundled skill (`resources/skills/aweswitch/SKILL.md`) now document all three providers (Claude, Codex, OpenCode), with provider-specific config examples, model selection syntax, and a mode-availability table.

### Highlights

- Added OpenCode provider with `OPENCODE_BASE_URL` / `OPENCODE_API_KEY` / `OPENCODE_MODEL` support
- `aweswitch add` now prompts for provider (`claude`, `codex`, or `opencode`)
- First launch writes provider entry to `~/.config/opencode/opencode.json`; subsequent launches reuse it
- API key written as `{env:VAR}` — actual key never stored on disk
- Model specified as first positional argument; defaults to first model in list
- Normalized `OPENCODE_MODEL` dict/list/string formats with consistent label resolution
- Updated README, README_cn, and SKILL.md with OpenCode examples and provider table
- Removed `cc-gemini` and `cx-aihubmix` example profiles from default config

## v0.3.0

`v0.3.0` adds `apply` and `restore` commands for writing profiles directly to `~/.claude/settings.json`, and restructures documentation around the two switching modes.

### Apply and restore commands

`aweswitch apply <profile>` writes a Claude profile's expanded env (including `_NAME` variants for the `/model` picker) directly to `~/.claude/settings.json`. A backup is created on first apply; subsequent applies skip the backup to preserve the original. Use `--force` to overwrite the backup. `aweswitch restore` reverts settings from the backup.

This enables a new workflow: start claude normally, then apply a profile from another terminal (or via the aweswitch skill), and use `/model` to switch models within the session — without launching a new process.

### Two modes documentation

README and SKILL.md now clearly distinguish two modes:

- **Launch mode** (`aweswitch <profile>`) — isolated sessions, env frozen at launch, multiple profiles in parallel terminals.
- **Apply mode** (`aweswitch apply <profile>`) — persistent default via settings.json, `/model` works within session.

Install and Usage sections were merged into a single "Install & Usage" section to eliminate duplication. The AI agent bootstrap guide (README.ai.md) now installs the skill early so the agent has profile knowledge during setup.

### Highlights

- New `aweswitch apply <profile>` command (Claude only)
- New `aweswitch restore` command
- `--force` flag to overwrite existing backup
- Backup only created on first apply to preserve original settings
- Extracted `build_claude_env()` from `prepare_run()` for reuse
- Merged Install and Usage sections in both READMEs
- Skill installation moved to Step 2 in AI bootstrap guide
- SKILL.md defaults to apply mode; launch mode marked as user-only

## v0.2.1

`v0.2.1` improves the missing-environment-variable error message and fixes README skill references.

### Better error messages

When a profile references an environment variable that is not set, aweswitch now prints a clear hint telling the user to add it to their shell config and reload — instead of a bare "missing environment variable" message. The hint is cross-platform and does not hardcode any specific shell or rc file.

### Docs fixes

Updated README skill references to point to the GitHub-hosted `SKILL.md` instead of a local `.aweskill` path, so the link works for all users.

### Highlights

- Improved missing env var error message with actionable reload hint
- Fixed `SKILL.md` links in README.md and README_cn.md to use GitHub URL

## v0.2.0

`v0.2.0` makes aweswitch fully cross-platform. Windows users can now launch profiles without hitting Unix-only system calls.

### Cross-platform support

Four Unix-specific calls were replaced with portable alternatives. `os.fork()` (used for auto-bookmark background polling) is now a `threading.Thread`. `os.execvpe()` / `os.execvp()` (used to hand off to `claude` or `codex`) fall back to `subprocess.run()` on Windows. `os.chmod(0o600)` is skipped on Windows where it has no effect. `shlex.split()` uses `posix=False` on Windows to preserve backslash paths.

### Highlights

- Replaced `os.fork()` with `threading.Thread` for auto-bookmark
- `exec_agent` uses `subprocess.run` on Windows instead of `os.execvpe`
- `config edit` uses `subprocess.run` on Windows instead of `os.execvp`
- Skipped `os.chmod(0o600)` on Windows
- `editor_argv` uses `posix=False` on Windows for correct path splitting
- CI already covers `windows-latest` with Python 3.9 and 3.13

## v0.1.9

`v0.1.9` adds Codex as a supported provider alongside Claude Code, and ships an AI guide and skill for aweswitch.

### Codex provider support

Profiles can now target OpenAI Codex. Set `"provider": "codex"` on a profile (or select "codex" in `aweswitch add`) and provide `OPENAI_BASE_URL` and `OPENAI_API_KEY`. aweswitch launches `codex` with the base URL, wire API, and auth injected via `-c` flags and environment variables. The default config includes a `codex-openai` example profile.

### AI guide and skill

A new `README.ai.md` documents how to use aweswitch from AI agents. A bundled skill file (`resources/skills/aweswitch/SKILL.md`) lets AI assistants discover and invoke aweswitch directly.

### Highlights

- Added Codex provider with `OPENAI_BASE_URL` / `OPENAI_API_KEY` support
- `aweswitch add` now prompts for provider (claude or codex) before profile fields
- Default config includes `codex-openai` example profile
- Added `README.ai.md` for AI agent integration
- Added bundled aweswitch skill for AI assistants
- Clarified Codex profile behavior in both READMEs

## v0.1.8

`v0.1.8` adds a self-update command and background update checking.

### Self-update

`aweswitch self-update` upgrades to the latest PyPI release, automatically detecting whether to use `pipx upgrade` or `pip install --upgrade`. A `--check` flag shows available updates without installing.

### Background update reminder

Each run now checks PyPI in the background (once per 24h) and prints a reminder to stderr when a newer version exists. Set `AWESWITCH_NO_UPDATE_CHECK=1` to disable.

### Highlights

- Added `aweswitch self-update` command with `--check` flag
- Background update check on each run with 24h cooldown
- Robust pipx detection using `sys.prefix` instead of path substring matching
- Error handling for network failures during update checks

## v0.1.7

`v0.1.7` improves model picker display for unset tiers and auto-populates the Opus model fallback.

### Model picker "Not set" display

When a profile does not define `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `SONNET_MODEL`, or `OPUS_MODEL`, the corresponding `_NAME` variant is now set to `"Not set"`. This prevents Claude Code's `/model` picker from showing a stale label inherited from `~/.claude/settings.json`.

### Highlights

- Show "Not set" in `/model` picker for unset model tiers instead of stale values
- Auto-populate `ANTHROPIC_DEFAULT_OPUS_MODEL` from `ANTHROPIC_MODEL` when not explicitly set
- Added aweshelf companion section and race condition notes to both READMEs
- Added `docs/CONTRIBUTING.md`

## v0.1.6

`v0.1.6` adds auto-bookmark support via [aweshelf](https://github.com/Webioinfo01/aweshelf). Sessions can now be tagged with a category and custom title at launch time, without requiring a separate bookmark step.

### Auto-bookmark with aweshelf

When launching a profile with `-c` (category), aweswitch forks a background process before exec that waits for the new session JSONL file to appear, then calls `aweshelf bookmark` to record it automatically. An optional `-t` flag sets the bookmark title; if omitted, aweshelf uses the session's first message. If aweshelf is not installed, `-c` and `-t` are ignored with a warning printed to stderr.

### Highlights

- Added `-c` / `--category` option to profile launch for auto-bookmarking
- Added `-t` / `--title` option to set a custom bookmark title
- Background fork process polls `~/.claude/projects/` for up to 60s
- Graceful degradation when aweshelf is not installed
- Updated help text with bookmark feature description and install instructions
- Updated both READMEs with aweshelf integration docs

## v0.1.5

`v0.1.5` fixes a model picker display issue when switching profiles and improves unknown-profile error messages.

### Model picker label fix

When a profile sets `ANTHROPIC_DEFAULT_HAIKU_MODEL` (or `SONNET`/`OPUS`), Claude Code's `/model` picker uses the corresponding `_NAME` variant as the display label. If `~/.claude/settings.json` already defines a `_NAME` variant for a different provider, the profile's model value alone wouldn't override the label, causing stale names to appear. aweswitch now automatically sets `_NAME` variants to match the model value at launch time, so users only need to configure the model itself.

### Highlights

- Auto-sync `ANTHROPIC_DEFAULT_*_MODEL_NAME` with the model value on profile launch
- Suggest `aweswitch list` when an unknown profile name is used
- Bumped `__version__` to stay in sync with `pyproject.toml`

## v0.1.4

`v0.1.4` replaces the `help` subcommands with an interactive `add` command for creating new profiles, and improves test coverage and documentation.

### Interactive profile creation

The `help` and `config help` subcommands have been removed. In their place, `aweswitch add` walks through an interactive prompt to create a new profile: name, base URL, auth token variable, model, and optional haiku/sonnet model overrides. Empty optional fields are skipped automatically, and duplicate profile names are rejected.

### Highlights

- Added `aweswitch add` command for interactive profile creation
- Added `save_profile()` helper with duplicate detection and empty-value filtering
- Removed `help` and `config help` subcommands
- Updated README version badges and install examples to v0.1.4

## v0.1.3

`v0.1.3` adds the GitHub Actions release path for aweswitch. The repository now has the same basic CI and tag-driven release structure used by aweskill, adapted for Python packaging and PyPI publishing.

### GitHub Actions release automation

Pushing a `v*` tag now runs the release workflow: it verifies the tag matches the package version, runs the test suite, builds the wheel and source distribution, checks package metadata, extracts release notes from this changelog, creates the GitHub Release, and publishes to PyPI with the configured `PYPI_API_TOKEN` secret.

### Highlights

- Added CI workflow for Python 3.9 and 3.13 across Linux, macOS, and Windows
- Added package build and `twine check` validation to CI
- Added tag-triggered release workflow for GitHub Releases and PyPI publishing
- Added a tag/package version consistency check before publishing
- Updated release-sensitive README version references

## v0.1.2

`v0.1.2` switches Claude profile settings injection from inline JSON to a temporary file. This keeps API tokens out of the process listing.

### Settings file injection

Previously, `aweswitch` passed `--settings '{"env": {...}}'` directly on the command line, which meant tokens were visible in `ps` output. Now it writes the settings object to a temporary file with `0o600` permissions and passes the file path to Claude Code instead.

### Highlights

- Settings written to a temporary file instead of inline JSON
- Temp file created with `0o600` permissions
- Tests updated for the new settings file approach
- Added PyPI downloads and GitHub stars badges to both READMEs

## v0.1.1

`v0.1.1` merges the `dev` branch into `main`. Profiles are now grouped under provider keys, the default config is Claude-only, and both README files include a hero image.

### Provider-grouped profiles

Profiles now live under provider groups:

```json
{
  "profiles": {
    "claude": {
      "cc-glm": {
        "env": {
          "ANTHROPIC_MODEL": "glm-5.1"
        }
      }
    }
  }
}
```

Profile names are still invoked directly with `aweswitch <profile>`, so existing command usage stays short. If a profile name appears under multiple providers, aweswitch reports it as ambiguous.

### Claude-only default config

The default config now contains only Claude Code profiles. Codex and Hermes are reserved for future provider support and are not executable in the current CLI.

### Documentation refresh

The README files were reworked around the same structure used by the larger aweskill project: concise positioning, install steps, FAQ, quick start, config rules, and development notes. Contributor guidance now lives in `docs/CONTRIBUTING.md`. Both READMEs now show a hero image at the top.

### Highlights

- Grouped config under `profiles.claude`
- Removed per-profile `provider` fields
- Removed `codex-mini` from the default config
- Kept direct `aweswitch <profile>` invocation
- Added duplicate profile-name detection
- Added contributor documentation
- Refreshed English and Chinese READMEs
- Added hero image to README headers

## initial line

Earlier commits introduced the single-file Python launcher, externalized the default config template, added tests, inherited token values from Claude settings when needed, switched Claude profile env injection to runtime `--settings`, and documented Claude model override behavior.

## v0.1.0

`v0.1.0` is the first package-oriented release line for aweswitch. The project now installs as a Python package with a console-script entry point, while keeping the CLI intentionally small and dependency-free at runtime.

### Python package installation

aweswitch now uses a `pyproject.toml` package definition with a `src/aweswitch/` layout. The command is exposed through the package entry point:

```toml
[project.scripts]
aweswitch = "aweswitch.cli:main"
```

The default config template is bundled as package data, so `aweswitch config init` works after `pip install aweswitch` without copying files by hand.

### Agent profile switcher positioning

The project positioning was broadened from a Claude Code-only profile switcher to an agent profile switcher. The executable provider set remains intentionally limited to Claude Code for now.

### Similar tools

The README now calls out [cc-switch](https://github.com/farion1231/cc-switch) as a similar Claude Code switching tool and explains how aweswitch currently differs: smaller Python package, local JSON profiles, runtime-only Claude Code `--settings`, and redacted inspection commands.

### Highlights

- Started versioning at `v0.1.0`
- Added `pyproject.toml`
- Moved implementation into `src/aweswitch/cli.py`
- Added the `aweswitch = "aweswitch.cli:main"` console script
- Bundled `default-config.json` as package data
- Updated README badges in the aweskill style
- Repositioned aweswitch as an agent profile switcher
- Added a similar-tools note for `cc-switch`
