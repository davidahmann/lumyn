from __future__ import annotations

from importlib import resources
from pathlib import Path


def read_builtin_text(relpath: str | Path) -> str:
    """
    Read a built-in asset shipped in the package.

    Supported relpaths:
    - schemas/<name>.json
    - policies/<name>.yml
    - policies/packs/<name>.yml
    """
    path_str = str(relpath).lstrip("./")
    base = resources.files("lumyn._data")
    try:
        return base.joinpath(path_str).read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"built-in asset not found: {path_str}") from e
