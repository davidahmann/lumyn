from __future__ import annotations

import hashlib
import hmac

from fastapi import HTTPException, status


def compute_hmac_signature(*, body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256:{digest}"


def require_hmac_signature(*, body: bytes, secret: str, provided: str | None) -> None:
    if provided is None or provided.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"reason_code": "AUTH_REQUIRED"},
        )

    if not provided.startswith("sha256:"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"reason_code": "AUTH_INVALID_SIGNATURE"},
        )

    expected = compute_hmac_signature(body=body, secret=secret)
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"reason_code": "AUTH_INVALID_SIGNATURE"},
        )
