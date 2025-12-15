from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class LoadedPolicy:
    policy: Mapping[str, Any]
    policy_hash: str
