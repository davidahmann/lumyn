from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from lumyn.api.auth import require_hmac_signature
from lumyn.core.decide import LumynConfig, decide_v1
from lumyn.schemas.loaders import load_json_schema
from lumyn.store.sqlite import SqliteStore
from lumyn.telemetry.tracing import start_span


@dataclass(frozen=True, slots=True)
class ApiV1Deps:
    config: LumynConfig
    store: SqliteStore
    signing_secret: str | None = None


def build_routes_v1(*, deps: ApiV1Deps) -> APIRouter:
    router = APIRouter()
    request_schema = load_json_schema("schemas/decision_request.v1.schema.json")
    request_validator = Draft202012Validator(request_schema)

    @router.post("/v1/decide")
    async def post_decide(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        with start_span("http.post /v1/decide"):
            if deps.signing_secret is not None:
                body = await request.body()
                require_hmac_signature(
                    body=body,
                    secret=deps.signing_secret,
                    provided=request.headers.get("X-Lumyn-Signature"),
                )
            try:
                request_validator.validate(payload)
                record_v1 = decide_v1(
                    payload,
                    config=deps.config,
                    store=deps.store,
                )
                return record_v1
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

    return router
