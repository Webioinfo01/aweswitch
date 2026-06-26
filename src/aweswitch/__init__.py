"""aweswitch package."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("aweswitch")
except PackageNotFoundError:
    __version__ = "0.0.0"  # fallback for running from source without install
