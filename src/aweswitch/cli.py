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
TEMP_SETTINGS_TTL_S = 24 * 60 * 60

# Claude Code reads these env vars to remap each /model tier to a concrete model
# id. Claude Code MERGES the --settings file with ~/.claude/settings.json, so a
# tier var the profile omits would let a stale value from a different provider
# leak through. build_claude_env defaults every unset tier to ANTHROPIC_MODEL to
# keep the --settings file authoritative regardless of which tier is selected.
CLAUDE_TIER_VARS = (
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_FABLE_MODEL",
)

# Profile kinds stored under `profiles`: "api" (env-based API profiles) and
# "account" (official OAuth logins). Profile names are unique across both.
PROFILE_KINDS = ("api", "account")

# Official-login accounts. Each account stores an opaque copy of the CLI's own
# credentials file and launches through a private config dir (CODEX_HOME /
# CLAUDE_CONFIG_DIR), so different accounts run side by side without touching
# the user's global ~/.codex or ~/.claude.
ACCOUNT_PROVIDERS = ("claude", "codex")
ACCOUNT_BLOB_KEY = {"codex": "auth", "claude": "credentials"}
ACCOUNT_CRED_FILENAME = {"codex": "auth.json", "claude": ".credentials.json"}


def config_path():
    return Path(os.environ.get("AWESWITCH_CONFIG", "~/.config/aweswitch/config.json")).expanduser()


def claude_settings_path():
    return Path(os.environ.get("CLAUDE_SETTINGS", "~/.claude/settings.json")).expanduser()


def codex_config_path():
    return Path(os.environ.get("CODEX_CONFIG", "~/.codex/config.toml")).expanduser()


def opencode_config_path():
    return Path(os.environ.get("OPENCODE_CONFIG", "~/.config/opencode/opencode.json")).expanduser()


def accounts_root():
    """Runtime dirs for official accounts live next to the config file."""
    return config_path().parent / "accounts"


def account_dir(provider, name):
    if provider not in ACCOUNT_PROVIDERS:
        die(f"official accounts support {', '.join(ACCOUNT_PROVIDERS)}, got: {provider}")
    return accounts_root() / provider / name


def live_credentials_path(provider):
    """Where the CLI itself stores an official login (for account import)."""
    if provider == "codex":
        return codex_config_path().with_name("auth.json")
    return claude_settings_path().with_name(".credentials.json")


def load_opencode_config():
    path = opencode_config_path()
    if not path.exists():
        return {"provider": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        # Never fall through to write_opencode_config with an empty config:
        # that would silently replace the user's whole opencode.json.
        die(f"invalid JSON in {path}: {exc}\n  Fix or remove the file, then retry.")
    if not isinstance(data, dict):
        die(f"unexpected JSON in {path}: expected an object at the top level")
    provider = data.get("provider")
    if provider is None:
        data["provider"] = {}
    elif not isinstance(provider, dict):
        die(f"'provider' in {path} must be an object")
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
            "setCacheKey": True,
        },
    }


def _opencode_api_key_ref(raw):
    """Return opencode's env ref syntax for a config ${VAR} API key.

    Allows bare values through with a warning so users aren't blocked from
    using plain strings; the env-ref form is still recommended because it
    keeps the actual key out of the config file.
    """
    if not isinstance(raw, str):
        click.echo(
            "  tip: OPENCODE_API_KEY is not a string — consider ${VAR_NAME} to keep the key out of the config file\n"
            "  Example: \"OPENCODE_API_KEY\": \"${MY_API_KEY}\"",
            err=True,
        )
        return str(raw)
    m = ENV_REF_RE.fullmatch(raw)
    if not m:
        click.echo(
            "  tip: OPENCODE_API_KEY is a plain value — consider ${VAR_NAME} to keep the key out of the config file\n"
            "  Example: \"OPENCODE_API_KEY\": \"${MY_API_KEY}\"",
            err=True,
        )
        return raw
    return f"{{env:{m.group(1)}}}"


def ensure_opencode_provider(base_url, api_key_ref, provider_name, model,
                             display_name=None, model_display_name=None):
    """Ensure provider+model exist in opencode.json, synced to the aweswitch config.

    The provider entry is owned by aweswitch (its name is the profile name), so
    stale credentials are updated to match the config instead of rejected.
    """
    oc_config = load_opencode_config()
    providers = oc_config["provider"]
    existing = providers.get(provider_name)
    model_name = model_display_name or model

    if existing:
        opts = existing.setdefault("options", {})
        changed = False
        if opts.get("baseURL") != base_url:
            opts["baseURL"] = base_url
            changed = True
        if opts.get("apiKey") != api_key_ref:
            opts["apiKey"] = api_key_ref
            changed = True
        models = existing.setdefault("models", {})
        if model not in models:
            models[model] = {"name": model_name}
            changed = True
        if changed:
            write_opencode_config(oc_config)
    else:
        entry = build_opencode_provider_entry(base_url, api_key_ref, name=display_name or provider_name)
        entry["models"] = {model: {"name": model_name}}
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
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        die(f"invalid config JSON at {path}: {exc}")
    if not isinstance(data.get("profiles"), dict):
        die("config must contain a profiles object")
    if migrate_profiles(data):
        backup = path.with_suffix(".json.bak")
        try:
            shutil.copy2(path, backup)
        except OSError as exc:
            die(f"failed to back up config before migration: {exc}")
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def migrate_profiles(data):
    """Fold the pre-0.4 provider-first layout into profiles.api, in place.

    v1: {"profiles": {"claude": {...}, "codex": {...}}}
    v2: {"profiles": {"api": {...}, "accounts": {...}}}

    Returns True when the config was rewritten (caller persists it). A file
    that mixes both layouts is rejected instead of guessed at.
    """
    profiles = data["profiles"]
    if not profiles:
        return False
    if not any(key in profiles for key in ("api", "accounts")):
        data["profiles"] = {"api": profiles}
        return True
    stale = [key for key in profiles if key not in ("api", "accounts")]
    if stale:
        die(
            "config mixes old and new profile layouts under 'profiles': "
            + ", ".join(sorted(stale))
            + "\n  Expected only 'api' and 'accounts'. Fix or remove the file, then retry."
        )
    return False


def kind_group(config, kind):
    """Return the provider->entries mapping for a profile kind."""
    key = "accounts" if kind == "account" else kind
    group = config.get("profiles", {}).get(key, {})
    if not isinstance(group, dict):
        die(f"profiles.{key} must be an object")
    return group


def load_claude_settings_env(path=None):
    path = claude_settings_path() if path is None else Path(path).expanduser()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
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
    """Resolve a profile name to (provider, kind, entry).

    kind is "api" or "account". Names must be unique across both kinds and
    all providers; a name found twice is ambiguous.
    """
    matches = []
    for kind in PROFILE_KINDS:
        for provider, provider_entries in kind_group(config, kind).items():
            if not isinstance(provider_entries, dict):
                die(f"provider entries must be an object: {kind}.{provider}")
            entry = provider_entries.get(name)
            if entry is not None:
                matches.append((provider, kind, entry))

    if not matches:
        die(f"unknown profile: {name}\nrun: aweswitch list  # view available profiles")
    if len(matches) > 1:
        die(f"ambiguous profile: {name}")

    provider, kind, entry = matches[0]
    if not isinstance(entry, dict):
        die(f"profile must be an object: {provider}.{name}")
    return provider, kind, entry


def write_settings_file(data):
    settings_dir = Path(tempfile.gettempdir()) / "aweswitch"
    settings_dir.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - TEMP_SETTINGS_TTL_S
    for old_path in settings_dir.glob("aweswitch-settings-*.json"):
        try:
            if old_path.stat().st_mtime < cutoff:
                old_path.unlink()
        except OSError:
            pass

    fd, path = tempfile.mkstemp(prefix="aweswitch-settings-", suffix=".json", dir=settings_dir)
    if os.name != "nt":
        os.chmod(path, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    return Path(path)


def read_json_object(path, what):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        die(f"invalid JSON in {path} ({what}): {exc}")
    if not isinstance(data, dict):
        die(f"unexpected JSON in {path} ({what}): expected an object")
    return data


def write_secret_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if os.name != "nt":
        os.chmod(path, 0o600)


def seed_claude_settings(source, destination):
    """Copy settings while dropping API-provider overrides for an OAuth account."""
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        shutil.copy2(source, destination)
        return
    if not isinstance(data, dict):
        shutil.copy2(source, destination)
        return
    env = data.get("env")
    if isinstance(env, dict):
        data = copy.deepcopy(data)
        data["env"] = {key: value for key, value in env.items() if not key.startswith("ANTHROPIC_")}
    destination.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def seed_codex_config(source, destination):
    """Copy config.toml without the selected third-party model provider."""
    text = source.read_text(encoding="utf-8")
    match = re.search(r'^\s*model_provider\s*=\s*["\']([^"\']+)["\']\s*$', text, re.MULTILINE)
    if not match:
        shutil.copy2(source, destination)
        return

    provider = re.escape(match.group(1))
    provider_table = re.compile(rf"^\s*\[\s*model_providers\.{provider}(?:\.|\s*\])")
    table_header = re.compile(r"^\s*\[")
    model_provider = re.compile(r"^\s*model_provider\s*=")
    filtered = []
    skipping_provider_table = False
    for line in text.splitlines(keepends=True):
        if model_provider.match(line):
            continue
        if table_header.match(line):
            skipping_provider_table = bool(provider_table.match(line))
        if not skipping_provider_table:
            filtered.append(line)
    destination.write_text("".join(filtered), encoding="utf-8")


def ensure_account_dir(provider, name, blob, force=False):
    """Materialize an official account's runtime dir and return its path.

    Once the dir exists it is the source of truth: the CLI refreshes OAuth
    tokens in place, so an existing credentials file is never overwritten by
    the (possibly stale) config blob unless force=True. Companion config
    files (codex config.toml / claude settings.json) are seeded once from the
    user's live files so model and MCP settings carry over.
    """
    d = account_dir(provider, name)
    d.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(d, 0o700)
    cred_path = d / ACCOUNT_CRED_FILENAME[provider]
    if (force or not cred_path.exists()) and isinstance(blob, dict) and blob:
        write_secret_json(cred_path, blob)
    if provider == "codex":
        seed, src, seed_config = d / "config.toml", codex_config_path(), seed_codex_config
    else:
        seed, src, seed_config = d / "settings.json", claude_settings_path(), seed_claude_settings
    if not seed.exists() and src.exists():
        seed_config(src, seed)
    return d


def profile_name_taken(config, name, ignore=None):
    """True when NAME is used by any profile other than `ignore` (kind, provider)."""
    for kind in PROFILE_KINDS:
        for provider, entries in kind_group(config, kind).items():
            if (kind, provider) == ignore:
                continue
            if isinstance(entries, dict) and name in entries:
                return True
    return False


def secure_config_file(path):
    if os.name != "nt":
        os.chmod(path, 0o600)


def save_account(path, provider, name, blob):
    """Store an account's credential blob under profiles.accounts.<provider>.<name>."""
    path = Path(path).expanduser()
    data = load_config(path)
    if profile_name_taken(data, name, ignore=("account", provider)):
        die(f"name already used: {name}")
    first_account = not kind_group(data, "account")
    accounts = data["profiles"].setdefault("accounts", {})
    accounts.setdefault(provider, {})[name] = {ACCOUNT_BLOB_KEY[provider]: blob}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    secure_config_file(path)
    if first_account:
        click.echo(
            f"Note: {path} now contains login credentials — keep it private "
            f"(permissions set to 600; do not commit or sync it publicly).",
            err=True,
        )


def build_claude_env(config, profile_name, base_env=None, claude_settings_env=None):
    """Build expanded env dict for a Claude profile, including _NAME variants.

    Every model-tier var (OPUS/SONNET/HAIKU/FABLE) the profile does not set is
    defaulted to ANTHROPIC_MODEL, and each gets a matching _NAME label. Without
    explicit values, Claude Code merges --settings with ~/.claude/settings.json
    and a stale tier->model mapping from a previous provider wins, so /model can
    resolve to a model the current provider doesn't serve (e.g. a minimax profile
    erroring with "selected model (mimo-v2.5)").
    """
    base_env = dict(os.environ if base_env is None else base_env)
    provider, kind, profile = profile_for(config, profile_name)
    if provider != "claude" or kind != "api":
        die(f"only claude api profiles are supported, got: provider={provider}, kind={kind}")
    profile_env = profile.get("env", {})
    if not profile_env.get("ANTHROPIC_BASE_URL"):
        die("ANTHROPIC_BASE_URL is required for claude profile")
    auth_token_raw = profile_env.get("ANTHROPIC_AUTH_TOKEN")
    if auth_token_raw and not ENV_REF_RE.fullmatch(auth_token_raw):
        click.echo(
            "  tip: ANTHROPIC_AUTH_TOKEN is a plain value — consider ${VAR_NAME} to keep the key out of the config file\n"
            "  Example: \"ANTHROPIC_AUTH_TOKEN\": \"${MY_API_KEY}\"",
            err=True,
        )
    settings_env = load_claude_settings_env() if claude_settings_env is None else claude_settings_env
    expansion_env = {**settings_env, **base_env}
    result = {key: expand_value(value, expansion_env) for key, value in profile_env.items()}

    # Default every unset tier to the main model so /model always resolves to a
    # model this provider serves, no matter which tier is selected.
    main_model = result.get("ANTHROPIC_MODEL")
    if main_model:
        for tier in CLAUDE_TIER_VARS:
            result.setdefault(tier, main_model)

    # Ensure _NAME variants are set so Claude Code /model picker shows the
    # correct label instead of a stale value from base settings.
    for tier in CLAUDE_TIER_VARS:
        name_key = f"{tier}_NAME"
        if tier in result:
            result.setdefault(name_key, result[tier])
        else:
            result[name_key] = "Not set"
    return result


def normalize_models(raw, profile_name, key):
    """Normalize a model list (dict, list, or comma-separated str) → {id: name}."""
    if isinstance(raw, dict) and raw:
        return raw
    if isinstance(raw, list) and raw:
        return {m: m for m in raw if isinstance(m, str) and m.strip()}
    if isinstance(raw, str) and raw.strip():
        return {m.strip(): m.strip() for m in raw.split(",") if m.strip()}
    die(f"{key} is required for {profile_name}")


def select_model(models_dict, user_args, profile_name):
    """Treat the first positional arg as the model name; default to the first entry."""
    if user_args:
        model = user_args[0]
        user_args = user_args[1:]
    else:
        model = next(iter(models_dict))
    if model not in models_dict:
        available = ", ".join(sorted(models_dict))
        die(f"unknown model '{model}' for {profile_name}\n  Available: {available}")
    return model, user_args


def prepare_run(config, profile_name, user_args, base_env=None, claude_settings_env=None, oc_providers=None):
    base_env = dict(os.environ if base_env is None else base_env)
    provider, kind, profile = profile_for(config, profile_name)
    profile_env = profile.get("env", {})
    env = dict(base_env)
    expansion_env = dict(base_env)
    oc_write_info = None
    account_info = None
    if kind == "account":
        if provider == "codex":
            env["CODEX_HOME"] = str(account_dir("codex", profile_name))
            argv = ["codex"]
        elif provider == "claude":
            env["CLAUDE_CONFIG_DIR"] = str(account_dir("claude", profile_name))
            # Claude Code defaults to the macOS Keychain on macOS; force file
            # credentials inside the account dir so the snapshot round-trips.
            env["CLAUDE_CODE_DONT_USE_KEYCHAIN"] = "1"
            argv = ["claude"]
        else:
            die(f"official accounts are not supported for {profile_name}: {provider}")
        argv += user_args
        account_info = {
            "provider": provider,
            "name": profile_name,
            "blob": profile.get(ACCOUNT_BLOB_KEY[provider]),
        }
    elif provider == "claude":
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
        # OPENAI_MODEL is optional: without it the profile only switches the API
        # source (legacy behavior). With it, the first positional arg selects the
        # model, same convention as opencode profiles.
        model = None
        if profile_env.get("OPENAI_MODEL"):
            models_dict = normalize_models(profile_env["OPENAI_MODEL"], profile_name, "OPENAI_MODEL")
            model, user_args = select_model(models_dict, user_args, profile_name)
        base_url = expand_value(base_url_raw, expansion_env)
        api_key = expand_value(api_key_raw, expansion_env)
        argv = ["codex"]
        if model:
            argv += ["-c", f'model="{model}"']
        argv += ["-c", f'model_provider="custom"']
        argv += ["-c", f'model_providers.custom.base_url="{base_url}"']
        argv += ["-c", f'model_providers.custom.wire_api="responses"']
        argv += ["-c", f'model_providers.custom.env_key="OPENAI_API_KEY"']
        argv += ["-c", f'disable_response_storage=true']
        env["OPENAI_API_KEY"] = api_key
        argv += user_args
    elif provider == "opencode":
        base_url_raw = profile_env.get("OPENCODE_BASE_URL")
        api_key_raw = profile_env.get("OPENCODE_API_KEY")
        models_raw = profile_env.get("OPENCODE_MODEL")
        if not base_url_raw:
            die(f"OPENCODE_BASE_URL is required for opencode profile: {profile_name}")
        if not api_key_raw:
            die(f"OPENCODE_API_KEY is required for opencode profile: {profile_name}")
        models_dict = normalize_models(models_raw, profile_name, "OPENCODE_MODEL")
        # First positional arg is the model name; default to first in dict
        model, user_args = select_model(models_dict, user_args, profile_name)
        base_url = expand_value(base_url_raw, expansion_env)
        # Keep an env reference in opencode.json so the actual key is never written to disk.
        api_key_ref = _opencode_api_key_ref(api_key_raw)
        oc_write_info = {
            "base_url": base_url,
            "api_key_ref": api_key_ref,
            "provider_name": profile_name,
            "model": model,
            "display_name": profile_env.get("OPENCODE_NAME") or profile_name,
            "model_display_name": models_dict.get(model, model),
        }
        argv = ["opencode", "-m", f"{profile_name}/{model}"]
        argv += user_args
    else:
        die(f"unsupported provider for {profile_name}: {provider}")

    return argv, env, oc_write_info, account_info


def redact(data):
    redacted = copy.deepcopy(data)

    # Account blobs are live OAuth tokens: mask them whole rather than hoping
    # every nested key matches the secret-name heuristic below.
    accounts = redacted.get("profiles", {}).get("accounts")
    if isinstance(accounts, dict):
        for provider_accounts in accounts.values():
            if isinstance(provider_accounts, dict):
                for entry in provider_accounts.values():
                    if isinstance(entry, dict):
                        for key in ACCOUNT_BLOB_KEY.values():
                            if key in entry:
                                entry[key] = "<redacted>"

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
    providers = set()
    for kind in PROFILE_KINDS:
        for provider, provider_entries in kind_group(config, kind).items():
            if not isinstance(provider_entries, dict):
                die(f"provider entries must be an object: {kind}.{provider}")
            providers.add(provider)
    for provider in sorted(providers):
        for kind in PROFILE_KINDS:
            entries = kind_group(config, kind).get(provider, {})
            for name in sorted(entries):
                if kind == "api":
                    label = profile_model_label(provider, entries[name])
                else:
                    label = "official login"
                print(f"{name}\t{provider}\t{kind}\t{label}")


def profile_model_label(provider, profile):
    env = profile.get("env", {})
    if provider == "claude":
        return env.get("ANTHROPIC_MODEL", "?")
    if provider == "codex":
        models = env.get("OPENAI_MODEL")
        if isinstance(models, dict):
            return ", ".join(sorted(models)) if models else env.get("OPENAI_BASE_URL", "?")
        if isinstance(models, list):
            return ", ".join(models) if models else env.get("OPENAI_BASE_URL", "?")
        if isinstance(models, str) and models.strip():
            return models.strip()
        return env.get("OPENAI_BASE_URL", "?")
    if provider == "opencode":
        models = env.get("OPENCODE_MODEL", {})
        if isinstance(models, dict):
            return ", ".join(sorted(models)) if models else "?"
        if isinstance(models, list):
            return ", ".join(models) if models else "?"
        if isinstance(models, str):
            parts = [m.strip() for m in models.split(",")]
            return ", ".join(p for p in parts if p) or "?"
        return "?"
    return "?"


def command_show(config, name):
    _, kind, profile = profile_for(config, name)
    if kind == "account":
        # The whole entry is an OAuth credential blob; mask it entirely.
        print(json.dumps({key: "<redacted>" for key in profile}, indent=2))
        return
    print(json.dumps(redact(profile), indent=2))


def editor_argv(editor, path):
    return [*shlex.split(editor, posix=(os.name != "nt")), str(path)]


CLAUDE_PROJECTS_DIR = Path("~/.claude/projects").expanduser()


def _bookmark_worker(start_time, category, profile, title):
    """Poll for a new session file and bookmark it."""
    try:
        aweshelf_bin = shutil.which("aweshelf")
        if not aweshelf_bin:
            return

        for _ in range(30):
            time.sleep(2)
            if not CLAUDE_PROJECTS_DIR.exists():
                continue

            for jsonl_path in CLAUDE_PROJECTS_DIR.rglob("*.jsonl"):
                if "subagents" in jsonl_path.parts:
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
    """Spawn a detached worker to auto-bookmark the session after Claude creates it.

    On POSIX the launch path os.execvpe()s the agent, which destroys every
    thread in the process — a background thread would die before its first
    poll. Fork a detached child instead; it survives the exec. On Windows the
    agent runs via subprocess.run(), which keeps this process (and its
    threads) alive, so a daemon thread is enough.
    """
    start = time.time()
    if os.name == "nt":
        threading.Thread(
            target=_bookmark_worker,
            args=(start, category, profile, title),
            daemon=True,
        ).start()
        return
    pid = os.fork()
    if pid == 0:
        try:
            os.setsid()
            _bookmark_worker(start, category, profile, title)
        except BaseException:
            pass
        finally:
            os._exit(0)


def exec_agent(argv, env):
    if os.name == "nt":
        # On Windows, CreateProcess (which subprocess.run uses) does not
        # perform PATHEXT resolution for a bare command name, and it
        # cannot execute .ps1 scripts directly. Resolve the command via
        # shutil.which (which honors PATHEXT), then re-route .ps1 hits
        # through PowerShell. .exe / .cmd / .bat can be exec'd as-is.
        resolved = shutil.which(argv[0], path=env.get("PATH"))
        if resolved:
            if resolved.lower().endswith(".ps1"):
                pwsh = (
                    shutil.which("powershell", path=env.get("PATH"))
                    or shutil.which("powershell.exe", path=env.get("PATH"))
                    or "powershell.exe"
                )
                argv = [pwsh, "-NoLogo", "-ExecutionPolicy", "Bypass",
                        "-File", resolved, *argv[1:]]
            else:
                argv = [resolved, *argv[1:]]
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
    if profile_name_taken(data, name):
        die(f"profile already exists: {name}")
    profile = {"env": {k: v for k, v in env_vars.items() if v}}
    data["profiles"].setdefault("api", {}).setdefault(provider, {})[name] = profile
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


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
            try:
                os.execvp(argv[0], argv)
            except FileNotFoundError:
                die(f"editor not found: {argv[0]}")
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
    help="Agent profile switcher for launching isolated runtime configs.\n\nSupported providers: claude, codex, opencode. Official accounts (claude/codex\nOAuth logins) are managed with `aweswitch account` and launch through private\nper-account config dirs.\n\nLaunch: aweswitch <profile> [-c CATEGORY] [-t TITLE] [extra args...]\n\nBookmark (requires aweshelf): -c tags the session with a category and -t sets\na custom title. A background process auto-bookmarks the session once it starts.\nInstall aweshelf: pip3 install aweshelf. If aweshelf is not installed,\n-c and -t are ignored with a warning.",
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

    kind = click.prompt("Type", type=click.Choice(["api", "official"]))
    if kind == "official":
        provider = click.prompt("Provider", type=click.Choice(ACCOUNT_PROVIDERS))
        name = click.prompt("Account name")
        method = click.prompt(
            "Method",
            type=click.Choice(["login", "import"]),
            default="login",
        )
        if method == "login":
            login_account(path, provider, name)
        else:
            import_account(path, provider, name)
        return

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
        models_str = click.prompt("OPENAI_MODEL (comma-separated, Enter to skip)", default="", show_default=False)

        env_vars = {
            "OPENAI_BASE_URL": base_url,
            "OPENAI_API_KEY": auth_token,
        }
        if models_str.strip():
            env_vars["OPENAI_MODEL"] = {m.strip(): m.strip() for m in models_str.split(",") if m.strip()}
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
    provider, kind, _ = profile_for(config, profile)
    if provider != "claude" or kind != "api":
        die(f"apply only supports claude api profiles, got: provider={provider}, kind={kind}")

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
            try:
                shutil.copy2(settings_path, backup_path)
            except OSError as exc:
                die(f"failed to create backup {backup_path}: {exc}")
            backed_up = True
        elif force:
            try:
                shutil.copy2(settings_path, backup_path)
            except OSError as exc:
                die(f"failed to create backup {backup_path}: {exc}")
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


@cli.group(context_settings={"help_option_names": ["-h", "--help"]})
def account():
    """Manage official-login accounts (Claude Code / Codex OAuth).

    Accounts launch like profiles (aweswitch <name>) but run through a
    private config dir, so several official accounts can be used side by
    side. See `aweswitch account login` to add one.
    """


def import_account(path, provider, name):
    """Save an official account from the CLI's live credentials."""
    load_config(path)
    live = live_credentials_path(provider)
    if not live.exists():
        die(
            f"no live credentials found at {live}\n"
            f"  Log in with the CLI first, or use: aweswitch account login {provider} {name}"
        )
    save_account(path, provider, name, read_json_object(live, "live credentials"))
    click.echo(f"Account '{name}' added ({provider}). Launch it with: aweswitch {name}")


def login_account(path, provider, name):
    """Run the CLI's own OAuth login inside the account dir and capture it."""
    data = load_config(path)
    existing = kind_group(data, "account").get(provider, {}).get(name)
    if existing is None and profile_name_taken(data, name):
        die(f"name already used: {name}")
    blob = existing.get(ACCOUNT_BLOB_KEY[provider]) if isinstance(existing, dict) else None
    d = ensure_account_dir(provider, name, blob)
    cred_path = d / ACCOUNT_CRED_FILENAME[provider]
    backup_path = cred_path.with_name(f".{cred_path.name}.login-backup")
    if cred_path.exists():
        if backup_path.exists():
            backup_path.unlink()
        cred_path.replace(backup_path)

    def restore_previous_credentials():
        if backup_path.exists():
            if cred_path.exists():
                cred_path.unlink()
            backup_path.replace(cred_path)

    env = dict(os.environ)
    if provider == "codex":
        env["CODEX_HOME"] = str(d)
        argv = ["codex", "login"]
        click.echo(f"Starting codex login for account '{name}' ...")
    else:
        env["CLAUDE_CONFIG_DIR"] = str(d)
        env["CLAUDE_CODE_DONT_USE_KEYCHAIN"] = "1"
        argv = ["claude"]
        click.echo(f"Starting claude for account '{name}' — run /login inside, then exit.")
    try:
        result = subprocess.run(argv, env=env)
    except FileNotFoundError:
        restore_previous_credentials()
        die(f"command not found: {argv[0]}")
    if result.returncode != 0 or not cred_path.exists():
        restore_previous_credentials()
        die(f"no credentials captured at {cred_path} (login exited with code {result.returncode})")
    try:
        captured = read_json_object(cred_path, "captured credentials")
    except SystemExit:
        restore_previous_credentials()
        raise
    if backup_path.exists():
        backup_path.unlink()
    save_account(path, provider, name, captured)
    click.echo(f"Account '{name}' saved. Launch it with: aweswitch {name}")


@account.command("add")
@click.argument("provider", type=click.Choice(ACCOUNT_PROVIDERS))
@click.argument("name")
def account_add_command(provider, name):
    """Save the currently logged-in official account as NAME.

    Imports the CLI's live credentials (~/.codex/auth.json or
    ~/.claude/.credentials.json). Claude Code on macOS usually keeps login
    in the Keychain instead; use `aweswitch account login` there.
    """
    import_account(config_path(), provider, name)


@account.command("login")
@click.argument("provider", type=click.Choice(ACCOUNT_PROVIDERS))
@click.argument("name")
def account_login_command(provider, name):
    """Log in to an official account NAME and capture its credentials.

    Runs the CLI's own login flow inside the account's private config dir,
    then stores the resulting credentials in the aweswitch config.
    """
    login_account(config_path(), provider, name)


@account.command("sync")
@click.argument("provider", type=click.Choice(ACCOUNT_PROVIDERS))
@click.argument("name")
def account_sync_command(provider, name):
    """Refresh NAME's stored credentials from its runtime dir.

    The CLI refreshes OAuth tokens inside the account dir at launch; sync
    copies the refreshed credentials back into the config file.
    """
    path = config_path()
    data = load_config(path)
    entry = kind_group(data, "account").get(provider, {}).get(name)
    if not isinstance(entry, dict):
        die(f"unknown account: {name}\nrun: aweswitch list  # view available profiles")
    cred_path = account_dir(provider, name) / ACCOUNT_CRED_FILENAME[provider]
    if not cred_path.exists():
        die(
            f"no runtime credentials at {cred_path}\n"
            f"  Launch or log in to the account first: aweswitch account login {provider} {name}"
        )
    save_account(path, provider, name, read_json_object(cred_path, "runtime credentials"))
    click.echo(f"Account '{name}' synced from {cred_path}")


@account.command("remove")
@click.argument("provider", type=click.Choice(ACCOUNT_PROVIDERS))
@click.argument("name")
@click.option("--purge", is_flag=True, help="Also delete the account's runtime directory.")
def account_remove_command(provider, name, purge):
    """Remove account NAME from the config."""
    path = config_path()
    data = load_config(path)
    provider_accounts = kind_group(data, "account").get(provider, {})
    if name not in provider_accounts:
        die(f"unknown account: {name}\nrun: aweswitch list  # view available profiles")
    del provider_accounts[name]
    if not provider_accounts:
        kind_group(data, "account").pop(provider, None)
        if not kind_group(data, "account"):
            data["profiles"].pop("accounts", None)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    d = account_dir(provider, name)
    if purge and d.exists():
        shutil.rmtree(d)
        click.echo(f"Removed account '{name}' and deleted {d}")
    else:
        click.echo(f"Removed account '{name}' (runtime dir kept: {d}; use --purge to delete)")


@click.command(
    "__profile__",
    hidden=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.option("-c", "--category", default=None, help="Bookmark category.")
@click.option("-t", "--title", default=None, help="Bookmark title.")
@click.pass_context
def run_profile(ctx, category, title):
    profile_name = ctx.parent.meta.get("profile_name")
    if not profile_name:
        die("missing profile name")
    if category:
        if not shutil.which("aweshelf"):
            click.echo("warning: aweshelf not found; -c/-t ignored. Install: pip3 install aweshelf (https://github.com/Webioinfo01/aweshelf)", err=True)
        else:
            _auto_bookmark(category, profile_name, title=title)
    run_argv, run_env, oc_write_info, account_info = prepare_run(load_config(config_path()), profile_name, ctx.args)
    if oc_write_info is not None:
        ensure_opencode_provider(
            oc_write_info["base_url"],
            oc_write_info["api_key_ref"],
            oc_write_info["provider_name"],
            oc_write_info["model"],
            display_name=oc_write_info["display_name"],
            model_display_name=oc_write_info["model_display_name"],
        )
    if account_info is not None:
        ensure_account_dir(account_info["provider"], account_info["name"], account_info["blob"])
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
