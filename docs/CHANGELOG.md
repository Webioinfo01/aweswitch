# change log

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
