from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


@contextmanager
def start_span(name: str, *, attributes: dict[str, Any] | None = None) -> Iterator[None]:
    """
    Optional OpenTelemetry span wrapper.

    If opentelemetry is not installed/configured, this is a no-op.
    """
    try:
        from opentelemetry import trace  # type: ignore[import-not-found]
    except Exception:
        yield
        return

    tracer = trace.get_tracer("lumyn")
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                if isinstance(v, bool | int | float | str):
                    span.set_attribute(k, v)
                else:
                    span.set_attribute(k, str(v))
        yield
