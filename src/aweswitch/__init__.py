"""aweswitch package."""

from __future__ import annotations

from pathlib import Path


def _source_version() -> str | None:
    """Read version from the repo's pyproject.toml (editable installs).

    pip freezes the version into dist-info metadata at install time, so an
    editable install keeps reporting the old version after bumps. The source
    pyproject.toml is the single source of truth.
    """
    pyproject = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
    if not pyproject.exists():
        return None
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("version"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


__version__ = _source_version()

if __version__ is None:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("aweswitch")
    except PackageNotFoundError:
        __version__ = "0.0.0"  # fallback for running from source without install
