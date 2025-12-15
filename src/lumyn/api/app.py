from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from lumyn.api.routes_v0 import ApiV0Deps, build_routes_v0
from lumyn.api.routes_v1 import ApiV1Deps, build_routes_v1
from lumyn.config import Settings, load_settings, storage_path_from_url
from lumyn.core.decide import LumynConfig
from lumyn.store.sqlite import SqliteStore
from lumyn.telemetry.logging import configure_logging
from lumyn.version import __version__


def create_app(*, settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging()

    store_path = storage_path_from_url(settings.lumyn.storage_url)
    store = SqliteStore(store_path)

    deps = ApiV0Deps(
        config=LumynConfig(
            policy_path=settings.lumyn.policy_path,
            store_path=store_path,
            top_k=settings.lumyn.top_k,
            mode=settings.lumyn.mode,
            redaction_profile=settings.lumyn.redaction_profile,
        ),
        store=store,
        signing_secret=settings.service.signing_secret,
    )

    app = FastAPI(title="Lumyn", version=__version__)
    app.include_router(build_routes_v0(deps=deps))

    deps_v1 = ApiV1Deps(
        config=deps.config,
        store=deps.store,
        signing_secret=deps.signing_secret,
    )
    app.include_router(build_routes_v1(deps=deps_v1))

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"ok": True}

    return app


app = create_app()
