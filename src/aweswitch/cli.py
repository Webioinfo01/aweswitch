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
import threading
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


def opencode_config_path():
    return Path(os.environ.get("OPENCODE_CONFIG", "~/.config/opencode/opencode.json")).expanduser()


def load_opencode_config():
    path = opencode_config_path()
    if not path.exists():
        return {"provider": {}}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {"provider": {}}
    if not isinstance(data.get("provider"), dict):
        data["provider"] = {}
    return data


def write_opencode_config(data):
    path = opencode_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def build_opencode_provider_entry(base_url, api_key, name="aweswitch"):
    return {
        "name": name,
        "npm": "@ai-sdk/openai-compatible",
        "options": {
            "apiKey": api_key,
            "baseURL": base_url,
        },
    }


def _resolve_opencode_api_key(raw):
    """Normalize an apiKey value for comparison.

    Handles ${VAR} (shell), {env:VAR} (opencode), and literal keys.
    Returns the resolved value from the environment, or the raw string if not a ref.
    """
    if not isinstance(raw, str):
        return raw
    m = ENV_REF_RE.match(raw)
    if m:
        return os.environ.get(m.group(1), raw)
    m = re.match(r"^\{env:([A-Za-z_][A-Za-z0-9_]*)\}$", raw)
    if m:
        return os.environ.get(m.group(1), raw)
    return raw


def ensure_opencode_provider(base_url, api_key, api_key_ref, provider_name, model, display_name=None):
    """Ensure provider+model exist in opencode.json. Writes if needed."""
    oc_config = load_opencode_config()
    providers = oc_config["provider"]
    existing = providers.get(provider_name)

    if existing:
        opts = existing.get("options", {})
        existing_key = opts.get("apiKey", "")
        keys_match = (
            existing_key == api_key
            or existing_key == api_key_ref
            or _resolve_opencode_api_key(existing_key) == api_key
        )
        if opts.get("baseURL") == base_url and keys_match:
            # Normalize existing key to {env:VAR} format if needed
            if existing_key != api_key_ref:
                opts["apiKey"] = api_key_ref
            models = existing.setdefault("models", {})
            if model not in models:
                models[model] = {"name": model}
            write_opencode_config(oc_config)
        else:
            die(
                f"opencode provider '{provider_name}' already exists with different credentials.\n"
                f"  Existing baseURL: {opts.get('baseURL', '?')}\n"
                f"  Either update opencode.json manually or use a different provider name."
            )
    else:
        name = display_name or provider_name
        entry = build_opencode_provider_entry(base_url, api_key_ref, name=name)
        entry["models"] = {model: {"name": model}}
        providers[provider_name] = entry
        write_opencode_config(oc_config)


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
            die(
                f"required environment variable not set: {name}\n"
                f"  Add it to your shell config (e.g. ~/.zshrc or ~/.bashrc), then reload your shell."
            )
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
    if os.name != "nt":
        os.chmod(path, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    return Path(path)


def build_claude_env(config, profile_name, base_env=None, claude_settings_env=None):
    """Build expanded env dict for a Claude profile, including _NAME variants."""
    base_env = dict(os.environ if base_env is None else base_env)
    provider, profile = profile_for(config, profile_name)
    if provider != "claude":
        die(f"only claude profiles are supported, got: {provider}")
    profile_env = profile.get("env", {})
    settings_env = load_claude_settings_env() if claude_settings_env is None else claude_settings_env
    expansion_env = {**settings_env, **base_env}
    result = {key: expand_value(value, expansion_env) for key, value in profile_env.items()}
    # ANTHROPIC_MODEL populates OPUS tier when not explicitly set.
    if "ANTHROPIC_MODEL" in result and "ANTHROPIC_DEFAULT_OPUS_MODEL" not in result:
        result["ANTHROPIC_DEFAULT_OPUS_MODEL"] = result["ANTHROPIC_MODEL"]
    # Ensure _NAME variants are set so Claude Code /model picker shows
    # the correct label instead of a stale value from base settings.
    for suffix in ("ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL"):
        name_key = f"{suffix}_NAME"
        if suffix in result and name_key not in result:
            result[name_key] = result[suffix]
        elif suffix not in result:
            result[name_key] = "Not set"
    return result


def prepare_run(config, profile_name, user_args, base_env=None, claude_settings_env=None, oc_providers=None):
    base_env = dict(os.environ if base_env is None else base_env)
    provider, profile = profile_for(config, profile_name)
    profile_env = profile.get("env", {})
    env = dict(base_env)
    expansion_env = dict(base_env)
    oc_write_info = None
    if provider == "claude":
        settings_env = load_claude_settings_env() if claude_settings_env is None else claude_settings_env
        expansion_env = {**settings_env, **base_env}

    if provider == "claude":
        argv = ["claude"]
        settings_env = build_claude_env(config, profile_name, base_env, claude_settings_env)
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
    elif provider == "opencode":
        base_url_raw = profile_env.get("OPENCODE_BASE_URL")
        api_key_raw = profile_env.get("OPENCODE_API_KEY")
        models_dict = profile_env.get("OPENCODE_MODEL")
        if not base_url_raw:
            die(f"OPENCODE_BASE_URL is required for opencode profile: {profile_name}")
        if not api_key_raw:
            die(f"OPENCODE_API_KEY is required for opencode profile: {profile_name}")
        if not isinstance(models_dict, dict) or not models_dict:
            die(f"OPENCODE_MODEL must be a non-empty dict for opencode profile: {profile_name}")
        # First positional arg is the model name
        if not user_args:
            available = ", ".join(sorted(models_dict))
            die(f"model required for opencode profile: {profile_name}\n  Available: {available}\n  Usage: aweswitch {profile_name} <model>")
        model = user_args[0]
        if model not in models_dict:
            available = ", ".join(sorted(models_dict))
            die(f"unknown model '{model}' for opencode profile: {profile_name}\n  Available: {available}")
        base_url = expand_value(base_url_raw, expansion_env)
        api_key = expand_value(api_key_raw, expansion_env)
        # Keep the raw ${VAR} reference for opencode.json ({env:VAR} syntax)
        # so the actual key is never written to disk.
        api_key_ref = api_key_raw
        if ENV_REF_RE.fullmatch(api_key_ref):
            var_name = ENV_REF_RE.match(api_key_ref).group(1)
            api_key_ref = f"{{env:{var_name}}}"
        oc_write_info = {
            "base_url": base_url,
            "api_key": api_key,
            "api_key_ref": api_key_ref,
            "provider_name": profile_name,
            "model": model,
            "display_name": profile_env.get("OPENCODE_NAME") or profile_name,
        }
        argv = ["opencode", "-m", f"{profile_name}/{model}"]
        argv += user_args[1:]  # skip the model arg, pass the rest
    else:
        die(f"unsupported provider for {profile_name}: {provider}")

    return argv, env, oc_write_info


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
    env = profile.get("env", {})
    if provider == "claude":
        return env.get("ANTHROPIC_MODEL", "?")
    if provider == "codex":
        return env.get("OPENAI_BASE_URL", "?")
    if provider == "opencode":
        models = env.get("OPENCODE_MODEL", {})
        if isinstance(models, dict):
            return ", ".join(sorted(models))
        return "?"
    return "?"


def command_show(config, name):
    _, profile = profile_for(config, name)
    print(json.dumps(redact(profile), indent=2))


def editor_argv(editor, path):
    return [*shlex.split(editor, posix=(os.name != "nt")), str(path)]


CLAUDE_PROJECTS_DIR = Path("~/.claude/projects").expanduser()


def _bookmark_worker(start_time, category, profile, title):
    """Background thread: poll for a new session file and bookmark it."""
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


def _auto_bookmark(category, profile, title=None):
    """Spawn a daemon thread to auto-bookmark the session after Claude creates it."""
    t = threading.Thread(
        target=_bookmark_worker,
        args=(time.time(), category, profile, title),
        daemon=True,
    )
    t.start()


def exec_agent(argv, env):
    if os.name == "nt":
        try:
            result = subprocess.run(argv, env=env)
            sys.exit(result.returncode)
        except FileNotFoundError:
            die(f"command not found: {argv[0]}")
        except OSError as exc:
            die(f"failed to run {argv[0]}: {exc}")
    else:
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
        if os.name == "nt":
            result = subprocess.run(argv)
            sys.exit(result.returncode)
        else:
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
    help="Agent profile switcher for launching isolated runtime configs.\n\nSupported providers: claude, codex, opencode.\n\nLaunch: aweswitch <profile> [-c CATEGORY] [-t TITLE] [extra args...]\n\nBookmark (requires aweshelf): -c tags the session with a category and -t sets\na custom title. A background process auto-bookmarks the session once it starts.\nInstall aweshelf: pip3 install aweshelf. If aweshelf is not installed,\n-c and -t are ignored with a warning.",
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

    provider = click.prompt("Provider", type=click.Choice(["claude", "codex", "opencode"]))
    name = click.prompt("Profile name")

    if provider == "opencode":
        base_url = click.prompt("OPENCODE_BASE_URL")
        auth_var = click.prompt("OPENCODE_API_KEY env var name (saved as ${VAR_NAME})")
        auth_token = f"${{{auth_var}}}"
        models_str = click.prompt("OPENCODE_MODEL (comma-separated, e.g. glm-5.1,glm-5.2)")
        models_dict = {m.strip(): m.strip() for m in models_str.split(",") if m.strip()}

        env_vars = {
            "OPENCODE_BASE_URL": base_url,
            "OPENCODE_API_KEY": auth_token,
            "OPENCODE_MODEL": models_dict,
        }
        save_profile(path, name, env_vars, provider=provider)
        click.echo(f"Profile '{name}' added.")
    elif provider == "claude":
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
        save_profile(path, name, env_vars, provider=provider)
        click.echo(f"Profile '{name}' added.")
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



def _mask_value(key, value):
    """Mask values that look like secrets for display."""
    if not isinstance(value, str):
        return value
    if SECRET_RE.search(key) and len(value) > 8:
        return value[:4] + "***"
    return value


@cli.command("apply")
@click.argument("profile")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing backup.")
def apply_command(profile, force):
    """Write a Claude profile's env into ~/.claude/settings.json.

    This overwrites the env section in your Claude settings so the profile
    takes effect in new sessions or via /model. A backup is saved on first
    apply; use --force to overwrite an existing backup.
    """
    config = load_config(config_path())
    provider, _ = profile_for(config, profile)
    if provider != "claude":
        die(f"apply only supports claude profiles, got: {provider}")

    settings_path = claude_settings_path()
    if settings_path.exists():
        try:
            settings_data = json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            die(f"invalid JSON in {settings_path}")
    else:
        settings_data = {}

    expanded_env = build_claude_env(config, profile)

    # Backup: only on first apply, or when --force is used.
    backup_path = settings_path.with_suffix(".json.bak")
    backed_up = False
    if settings_path.exists():
        if not backup_path.exists():
            shutil.copy2(settings_path, backup_path)
            backed_up = True
        elif force:
            shutil.copy2(settings_path, backup_path)
            backed_up = True

    settings_data["env"] = {**settings_data.get("env", {}), **expanded_env}
    settings_path.write_text(json.dumps(settings_data, indent=2) + "\n")

    click.echo(f"Applied {profile} to {settings_path}")
    for key, value in sorted(expanded_env.items()):
        click.echo(f"  {key:42s} → {_mask_value(key, value)}")
    if backed_up:
        click.echo(f"Backup: {backup_path}")
    elif backup_path.exists():
        click.echo(f"Note: backup already exists, not overwritten. Use --force to overwrite.")
    click.echo("Restart your session or use /model to pick the new model.")


@cli.command("restore")
def restore_command():
    """Restore ~/.claude/settings.json from backup."""
    settings_path = claude_settings_path()
    backup_path = settings_path.with_suffix(".json.bak")
    if not backup_path.exists():
        die(f"no backup found: {backup_path}")
    shutil.copy2(backup_path, settings_path)
    click.echo(f"Restored {settings_path} from backup.")
    click.echo("Restart your session for changes to take effect.")


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
    run_argv, run_env, oc_write_info = prepare_run(load_config(config_path()), profile_name, ctx.args)
    if oc_write_info is not None:
        ensure_opencode_provider(
            oc_write_info["base_url"],
            oc_write_info["api_key"],
            oc_write_info["api_key_ref"],
            oc_write_info["provider_name"],
            oc_write_info["model"],
            display_name=oc_write_info["display_name"],
        )
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
