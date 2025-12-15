from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from lumyn.api.routes_v0 import build_routes_v0, make_default_deps
from lumyn.version import __version__


@dataclass(frozen=True, slots=True)
class ApiConfig:
    policy_path: Path = Path("policies/lumyn-support.v0.yml")
    store_path: Path = Path(".lumyn/lumyn.db")
    top_k: int = 5

    @staticmethod
    def from_env() -> ApiConfig:
        policy_path = Path(os.getenv("LUMYN_POLICY_PATH", "policies/lumyn-support.v0.yml"))
        store_path = Path(os.getenv("LUMYN_STORE_PATH", ".lumyn/lumyn.db"))
        top_k_raw = os.getenv("LUMYN_TOP_K", "5")
        try:
            top_k = int(top_k_raw)
        except ValueError:
            top_k = 5
        return ApiConfig(policy_path=policy_path, store_path=store_path, top_k=top_k)


def create_app(*, config: ApiConfig | None = None) -> FastAPI:
    cfg = config or ApiConfig.from_env()
    deps = make_default_deps(
        policy_path=cfg.policy_path, store_path=cfg.store_path, top_k=cfg.top_k
    )

    app = FastAPI(title="Lumyn", version=__version__)
    app.include_router(build_routes_v0(deps=deps))

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"ok": True}

    return app
