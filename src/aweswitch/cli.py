#!/usr/bin/env python3
import copy
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import click

from aweswitch import __version__
from aweswitch.update_check import check_async, get_pypi_latest, _version_gte


TEMPLATE_PATH = Path(__file__).parent / "default-config.json"

SECRET_RE = re.compile(r"(TOKEN|KEY|SECRET|PASSWORD|AUTH)", re.IGNORECASE)
ENV_REF_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def config_path():
    return Path(os.environ.get("AWESWITCH_CONFIG", "~/.config/aweswitch/config.json")).expanduser()


def claude_settings_path():
    return Path(os.environ.get("CLAUDE_SETTINGS", "~/.claude/settings.json")).expanduser()


def codex_config_path():
    return Path(os.environ.get("CODEX_CONFIG", "~/.codex/config.toml")).expanduser()


def generate_codex_config(provider_name, base_url):
    """Generate a minimal config.toml for a third-party Codex provider."""
    clean = re.sub(r"[^a-z0-9_]", "_", provider_name.lower()).strip("_") or "custom"
    return (
        f'model_provider = "{clean}"\n'
        f'disable_response_storage = true\n'
        f'\n'
        f'[model_providers.{clean}]\n'
        f'name = "{clean}"\n'
        f'base_url = "{base_url}"\n'
        f'wire_api = "responses"\n'
        f'requires_openai_auth = true\n'
    )


def die(message):
    raise SystemExit(f"aweswitch: {message}")


def init_config(path):
    path = Path(path).expanduser()
    if path.exists():
        die(f"config already exists: {path}")
    if not TEMPLATE_PATH.exists():
        die(f"template not found: {TEMPLATE_PATH}")
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TEMPLATE_PATH, path)


def load_config(path):
    path = Path(path).expanduser()
    if not path.exists():
        die(f"config not found: {path}\nrun: aweswitch config init")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        die(f"invalid config JSON at {path}: {exc}")
    if not isinstance(data.get("profiles"), dict):
        die("config must contain a profiles object")
    return data


def load_claude_settings_env(path=None):
    path = claude_settings_path() if path is None else Path(path).expanduser()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    env = data.get("env", {})
    if not isinstance(env, dict):
        return {}
    return {key: value for key, value in env.items() if isinstance(value, str)}


def expand_value(value, env):
    if not isinstance(value, str):
        return value

    def replace(match):
        name = match.group(1)
        if name not in env:
            die(f"missing environment variable: {name}")
        return env[name]

    return ENV_REF_RE.sub(replace, value)


def profile_for(config, name):
    matches = []
    for provider, provider_profiles in config.get("profiles", {}).items():
        if not isinstance(provider_profiles, dict):
            die(f"provider profiles must be an object: {provider}")
        profile = provider_profiles.get(name)
        if profile is not None:
            matches.append((provider, profile))

    if not matches:
        die(f"unknown profile: {name}\nrun: aweswitch list  # view available profiles")
    if len(matches) > 1:
        die(f"ambiguous profile: {name}")

    provider, profile = matches[0]
    if not isinstance(profile, dict):
        die(f"profile must be an object: {provider}.{name}")
    return provider, profile


def write_settings_file(data):
    fd, path = tempfile.mkstemp(prefix="aweswitch-settings-", suffix=".json")
    os.chmod(path, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    return Path(path)


def prepare_run(config, profile_name, user_args, base_env=None, claude_settings_env=None):
    base_env = dict(os.environ if base_env is None else base_env)
    provider, profile = profile_for(config, profile_name)
    profile_env = profile.get("env", {})
    env = dict(base_env)
    expansion_env = dict(base_env)
    if provider == "claude":
        settings_env = load_claude_settings_env() if claude_settings_env is None else claude_settings_env
        expansion_env = {**settings_env, **base_env}

    if provider == "claude":
        argv = ["claude"]
        settings_env = {key: expand_value(value, expansion_env) for key, value in profile_env.items()}
        # ANTHROPIC_MODEL populates OPUS tier when not explicitly set.
        if "ANTHROPIC_MODEL" in settings_env and "ANTHROPIC_DEFAULT_OPUS_MODEL" not in settings_env:
            settings_env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = settings_env["ANTHROPIC_MODEL"]
        # Ensure _NAME variants are set so Claude Code /model picker shows
        # the correct label instead of a stale value from base settings.
        for suffix in ("ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL"):
            name_key = f"{suffix}_NAME"
            if suffix in settings_env and name_key not in settings_env:
                settings_env[name_key] = settings_env[suffix]
            elif suffix not in settings_env:
                settings_env[name_key] = "Not set"
        if settings_env:
            settings_path = write_settings_file({"env": settings_env})
            argv += ["--settings", str(settings_path)]
        argv += user_args
    elif provider == "codex":
        base_url_raw = profile_env.get("OPENAI_BASE_URL")
        api_key_raw = profile_env.get("OPENAI_API_KEY")
        if not base_url_raw:
            die(f"OPENAI_BASE_URL is required for codex profile: {profile_name}")
        if not api_key_raw:
            die(f"OPENAI_API_KEY is required for codex profile: {profile_name}")
        base_url = expand_value(base_url_raw, expansion_env)
        api_key = expand_value(api_key_raw, expansion_env)
        argv = ["codex"]
        argv += ["-c", f'model_provider="custom"']
        argv += ["-c", f'model_providers.custom.base_url="{base_url}"']
        argv += ["-c", f'model_providers.custom.wire_api="responses"']
        argv += ["-c", f'disable_response_storage=true']
        env["OPENAI_API_KEY"] = api_key
        argv += user_args
    else:
        die(f"unsupported provider for {profile_name}: {provider}")

    return argv, env


def redact(data):
    redacted = copy.deepcopy(data)

    def walk(value, key=""):
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                if SECRET_RE.search(child_key) and isinstance(child_value, str):
                    value[child_key] = "<redacted>"
                else:
                    walk(child_value, child_key)
        elif isinstance(value, list):
            for item in value:
                walk(item, key)

    walk(redacted)
    return redacted


def command_list(config):
    for provider in sorted(config["profiles"]):
        provider_profiles = config["profiles"][provider]
        if not isinstance(provider_profiles, dict):
            die(f"provider profiles must be an object: {provider}")
        for name in sorted(provider_profiles):
            profile = provider_profiles[name]
            model = profile_model_label(provider, profile)
            print(f"{name}\t{provider}\t{model}")


def profile_model_label(provider, profile):
    if provider == "claude":
        return profile.get("env", {}).get("ANTHROPIC_MODEL", "?")
    if provider == "codex":
        return profile.get("env", {}).get("OPENAI_BASE_URL", "?")
    return "?"


def command_show(config, name):
    _, profile = profile_for(config, name)
    print(json.dumps(redact(profile), indent=2))


def editor_argv(editor, path):
    return [*shlex.split(editor), str(path)]


CLAUDE_PROJECTS_DIR = Path("~/.claude/projects").expanduser()


def _auto_bookmark(category, profile, title=None):
    """Fork a child process to auto-bookmark the session after Claude creates it."""
    start_time = time.time()
    try:
        pid = os.fork()
    except OSError:
        return

    if pid != 0:
        # Parent: collect finished children, continue to exec claude
        try:
            os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            pass
        return

    # --- child process ---
    try:
        aweshelf_bin = shutil.which("aweshelf")
        if not aweshelf_bin:
            return

        for _ in range(30):
            time.sleep(2)
            if not CLAUDE_PROJECTS_DIR.exists():
                continue

            for jsonl_path in CLAUDE_PROJECTS_DIR.rglob("*.jsonl"):
                if "/subagents/" in str(jsonl_path):
                    continue
                try:
                    if jsonl_path.stat().st_mtime < start_time:
                        continue
                except OSError:
                    continue

                session_id = jsonl_path.stem
                cmd = [aweshelf_bin, "bookmark", session_id, "-c", category, "--profile", profile]
                if title:
                    cmd += ["-t", title]
                try:
                    subprocess.run(cmd, timeout=10, capture_output=True)
                except Exception:
                    pass
                return
    except Exception:
        pass
    finally:
        os._exit(0)


def exec_agent(argv, env):
    try:
        os.execvpe(argv[0], argv, env)
    except FileNotFoundError:
        die(f"command not found: {argv[0]}")
    except OSError as exc:
        die(f"failed to run {argv[0]}: {exc}")


def save_profile(path, name, env_vars, provider="claude"):
    path = Path(path).expanduser()
    data = load_config(path)
    provider_profiles = data["profiles"].setdefault(provider, {})
    if name in provider_profiles:
        die(f"profile already exists: {name}")
    profile = {"env": {k: v for k, v in env_vars.items() if v}}
    provider_profiles[name] = profile
    path.write_text(json.dumps(data, indent=2) + "\n")


def command_config(argv):
    path = config_path()
    subcommand = argv[0] if argv else "path"

    if subcommand == "path":
        print(path)
    elif subcommand == "show":
        print(json.dumps(redact(load_config(path)), indent=2))
    elif subcommand == "init":
        init_config(path)
        print(path)
    elif subcommand == "edit":
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            init_config(path)
        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or shutil.which("nano")
        if not editor:
            die(f"no EDITOR set; edit config manually: {path}")
        argv = editor_argv(editor, path)
        os.execvp(argv[0], argv)
    else:
        die(f"unknown config command: {subcommand}")


class ProfileGroup(click.Group):
    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            if not args:
                raise
            profile_name = args[0]
            ctx.meta["profile_name"] = profile_name
            command = self.get_command(ctx, "__profile__")
            return profile_name, command, args[1:]


@click.group(
    cls=ProfileGroup,
    name="aweswitch",
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Agent profile switcher for launching isolated runtime configs.\n\nSupported providers: claude, codex.\n\nLaunch: aweswitch <profile> [-c CATEGORY] [-t TITLE] [extra args...]\n\nBookmark (requires aweshelf): -c tags the session with a category and -t sets\na custom title. A background process auto-bookmarks the session once it starts.\nInstall aweshelf: pip3 install aweshelf. If aweshelf is not installed,\n-c and -t are ignored with a warning.",
)
@click.version_option(__version__, "-v", "--version", message="%(version)s")
def cli():
    pass


@cli.command("list")
def list_profiles():
    """List configured profiles."""
    command_list(load_config(config_path()))


@cli.command()
@click.argument("profile")
def show(profile):
    """Show one profile with secrets redacted."""
    command_show(load_config(config_path()), profile)


@cli.group(context_settings={"help_option_names": ["-h", "--help"]})
def config():
    """Manage aweswitch config."""


@config.command("path")
def config_path_command():
    """Print config path."""
    click.echo(config_path())


@config.command("show")
def config_show_command():
    """Show config with secrets redacted."""
    click.echo(json.dumps(redact(load_config(config_path())), indent=2))


@config.command("edit")
def config_edit_command():
    """Open config in $VISUAL, $EDITOR, or nano."""
    command_config(["edit"])


@config.command("init")
def config_init_command():
    """Create the default config."""
    init_config(config_path())
    click.echo(config_path())


@cli.command("init")
def init_command():
    """Create the default config."""
    init_config(config_path())
    click.echo(config_path())


@cli.command("self-update")
@click.option("--check", is_flag=True, help="Show versions without updating.")
def self_update_command(check):
    """Update aweswitch to the latest version."""
    try:
        latest = get_pypi_latest()
    except Exception as e:
        raise SystemExit(f"Failed to check PyPI: {e}")
    if _version_gte(__version__, latest):
        click.echo(f"aweswitch is up to date ({__version__}).")
        return
    click.echo(f"Current: {__version__}  Latest: {latest}")
    if check:
        return

    if Path(sys.prefix, "pyvenv.cfg").exists() and "pipx" in sys.prefix:
        cmd = [shutil.which("pipx") or "pipx", "upgrade", "aweswitch"]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "aweswitch"]

    click.echo(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        click.echo("Done. Restart aweswitch to use the new version.")
    else:
        raise SystemExit(result.returncode)


@cli.command("add")
def add_command():
    """Interactively add a new profile."""
    path = config_path()
    load_config(path)

    provider = click.prompt("Provider", type=click.Choice(["claude", "codex"]))
    name = click.prompt("Profile name")

    if provider == "claude":
        base_url = click.prompt("ANTHROPIC_BASE_URL")
        auth_var = click.prompt("ANTHROPIC_AUTH_TOKEN env var name (saved as ${VAR_NAME})")
        auth_token = f"${{{auth_var}}}"
        model = click.prompt("ANTHROPIC_MODEL")
        haiku_model = click.prompt("ANTHROPIC_DEFAULT_HAIKU_MODEL (optional, press Enter to skip)", default="", show_default=False)
        sonnet_model = click.prompt("ANTHROPIC_DEFAULT_SONNET_MODEL (optional, press Enter to skip)", default="", show_default=False)

        env_vars = {
            "ANTHROPIC_BASE_URL": base_url,
            "ANTHROPIC_AUTH_TOKEN": auth_token,
            "ANTHROPIC_MODEL": model,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": haiku_model,
            "ANTHROPIC_DEFAULT_SONNET_MODEL": sonnet_model,
        }
    else:
        base_url = click.prompt("OPENAI_BASE_URL")
        auth_var = click.prompt("OPENAI_API_KEY env var name (saved as ${VAR_NAME})")
        auth_token = f"${{{auth_var}}}"

        env_vars = {
            "OPENAI_BASE_URL": base_url,
            "OPENAI_API_KEY": auth_token,
        }

    save_profile(path, name, env_vars, provider=provider)
    click.echo(f"Profile '{name}' added.")



@click.command(
    "__profile__",
    hidden=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.option("-c", "--category", default=None, help="Bookmark category.")
@click.option("-t", "--title", default=None, help="Bookmark title.")
@click.pass_context
def run_profile(ctx, category, title):
    profile_name = ctx.parent.meta["profile_name"]
    if category:
        if not shutil.which("aweshelf"):
            click.echo("warning: aweshelf not found; -c/-t ignored. Install: pip3 install aweshelf (https://github.com/Webioinfo01/aweshelf)", err=True)
        else:
            _auto_bookmark(category, profile_name, title=title)
    run_argv, run_env = prepare_run(load_config(config_path()), profile_name, ctx.args)
    exec_agent(run_argv, run_env)


cli.add_command(run_profile)


def main(argv=None):
    get_reminder = check_async(sys.argv[1:] if argv is None else argv)
    try:
        return cli.main(args=argv, prog_name="aweswitch")
    finally:
        reminder = get_reminder()
        if reminder:
            click.echo(f"⚠  {reminder}", err=True)


if __name__ == "__main__":
    raise SystemExit(main())
