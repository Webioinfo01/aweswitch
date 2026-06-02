#!/usr/bin/env python3
import copy
import json
import os
import re
import shlex
import shutil
import tempfile
from pathlib import Path

import click

from aweswitch import __version__


TEMPLATE_PATH = Path(__file__).parent / "default-config.json"

SECRET_RE = re.compile(r"(TOKEN|KEY|SECRET|PASSWORD|AUTH)", re.IGNORECASE)
ENV_REF_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def config_path():
    return Path(os.environ.get("AWESWITCH_CONFIG", "~/.config/aweswitch/config.json")).expanduser()


def claude_settings_path():
    return Path(os.environ.get("CLAUDE_SETTINGS", "~/.claude/settings.json")).expanduser()


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
        if settings_env:
            settings_path = write_settings_file({"env": settings_env})
            argv += ["--settings", str(settings_path)]
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
    return "?"


def command_show(config, name):
    _, profile = profile_for(config, name)
    print(json.dumps(redact(profile), indent=2))


def editor_argv(editor, path):
    return [*shlex.split(editor), str(path)]


def exec_agent(argv, env):
    try:
        os.execvpe(argv[0], argv, env)
    except FileNotFoundError:
        die(f"command not found: {argv[0]}")
    except OSError as exc:
        die(f"failed to run {argv[0]}: {exc}")


def save_profile(path, name, env_vars):
    path = Path(path).expanduser()
    data = load_config(path)
    claude_profiles = data["profiles"].setdefault("claude", {})
    if name in claude_profiles:
        die(f"profile already exists: {name}")
    profile = {"env": {k: v for k, v in env_vars.items() if v}}
    claude_profiles[name] = profile
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
    help="Agent profile switcher for launching isolated runtime configs.",
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


@cli.command("add")
def add_command():
    """Interactively add a new profile."""
    path = config_path()
    load_config(path)

    name = click.prompt("Profile name")
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

    save_profile(path, name, env_vars)
    click.echo(f"Profile '{name}' added.")



@click.command(
    "__profile__",
    hidden=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.pass_context
def run_profile(ctx):
    profile_name = ctx.parent.meta["profile_name"]
    run_argv, run_env = prepare_run(load_config(config_path()), profile_name, ctx.args)
    exec_agent(run_argv, run_env)


cli.add_command(run_profile)


def main(argv=None):
    return cli.main(args=argv, prog_name="aweswitch")


if __name__ == "__main__":
    raise SystemExit(main())
