from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from lumyn.assets import read_builtin_text


@lru_cache(maxsize=32)
def load_json_schema(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if p.exists():
        return cast(dict[str, Any], json.loads(p.read_text(encoding="utf-8")))
    text = read_builtin_text(str(p).lstrip("./"))
    return cast(dict[str, Any], json.loads(text))
