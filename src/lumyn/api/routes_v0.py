from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from jsonschema.exceptions import ValidationError

from lumyn.api.auth import require_hmac_signature
from lumyn.core.decide import LumynConfig, decide
from lumyn.policy.loader import load_policy
from lumyn.store.sqlite import SqliteStore
from lumyn.telemetry.tracing import start_span


@dataclass(frozen=True, slots=True)
class ApiV0Deps:
    config: LumynConfig
    store: SqliteStore
    signing_secret: str | None = None


def build_routes_v0(*, deps: ApiV0Deps) -> APIRouter:
    router = APIRouter()

    @router.post("/v0/decide")
    async def post_decide(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        with start_span("http.post /v0/decide"):
            if deps.signing_secret is not None:
                body = await request.body()
                require_hmac_signature(
                    body=body,
                    secret=deps.signing_secret,
                    provided=request.headers.get("X-Lumyn-Signature"),
                )
            try:
                return decide(payload, config=deps.config, store=deps.store)
            except ValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e.message)
                ) from e
            except FileNotFoundError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
                ) from e
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
                ) from e

    @router.get("/v0/decisions/{decision_id}")
    def get_decision(decision_id: str) -> dict[str, Any]:
        with start_span("http.get /v0/decisions/{decision_id}"):
            deps.store.init()
            record = deps.store.get_decision_record(decision_id)
            if record is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
            return record

    @router.post("/v0/decisions/{decision_id}/events")
    def post_event(decision_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with start_span("http.post /v0/decisions/{decision_id}/events"):
            deps.store.init()
            record = deps.store.get_decision_record(decision_id)
            if record is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

            event_type = payload.get("type")
            if not isinstance(event_type, str) or event_type.strip() == "":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="payload.type must be a non-empty string",
                )
            data = payload.get("data", {})
            if not isinstance(data, dict):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="payload.data must be an object",
                )

            event_id = deps.store.append_decision_event(decision_id, event_type, data)
            return {"event_id": event_id}

    @router.get("/v0/policy")
    def get_policy() -> dict[str, Any]:
        with start_span("http.get /v0/policy"):
            loaded = load_policy(deps.config.policy_path)
            return {
                "policy_id": loaded.policy["policy_id"],
                "policy_version": loaded.policy["policy_version"],
                "policy_hash": loaded.policy_hash,
            }

    return router


def make_default_deps(*, policy_path: str | Path, store_path: str | Path, top_k: int) -> ApiV0Deps:
    cfg = LumynConfig(policy_path=policy_path, store_path=store_path, top_k=top_k)
    store = SqliteStore(store_path)
    return ApiV0Deps(config=cfg, store=store)
