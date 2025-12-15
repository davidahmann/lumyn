from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class NormalizedRequest:
    action_type: str
    amount_currency: str | None
    amount_value: float | None
    amount_usd: float | None
    evidence: dict[str, object]
    fx_rate_to_usd_present: bool


def normalize_request(request: dict[str, Any]) -> NormalizedRequest:
    action = request.get("action") or {}
    evidence_raw = request.get("evidence") or {}

    action_type = str(action.get("type"))
    amount = action.get("amount") or {}

    amount_currency = amount.get("currency")
    if not isinstance(amount_currency, str):
        amount_currency = None

    amount_value_raw = amount.get("value")
    amount_value = float(amount_value_raw) if isinstance(amount_value_raw, int | float) else None

    evidence: dict[str, object]
    if isinstance(evidence_raw, dict):
        evidence = {str(k): v for k, v in evidence_raw.items()}
    else:
        evidence = {}

    fx_rate_raw = evidence.get("fx_rate_to_usd")
    if isinstance(fx_rate_raw, int | float):
        fx_rate_to_usd_present = True
        fx_rate_to_usd: float | None = float(fx_rate_raw)
    else:
        fx_rate_to_usd_present = False
        fx_rate_to_usd = None

    amount_usd: float | None
    if amount_value is None or amount_currency is None:
        amount_usd = None
    elif amount_currency == "USD":
        amount_usd = amount_value
    elif fx_rate_to_usd is not None:
        amount_usd = amount_value * fx_rate_to_usd
    else:
        amount_usd = None

    return NormalizedRequest(
        action_type=action_type,
        amount_currency=amount_currency,
        amount_value=amount_value,
        amount_usd=amount_usd,
        evidence=evidence,
        fx_rate_to_usd_present=fx_rate_to_usd_present,
    )
