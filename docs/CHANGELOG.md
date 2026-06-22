# change log

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
