from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, cast


@lru_cache(maxsize=32)
def load_json_schema(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    return cast(dict[str, Any], json.loads(p.read_text(encoding="utf-8")))
