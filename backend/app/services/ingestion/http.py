"""Shared HTTP helper: timeouts, retry with exponential backoff, per-host throttling."""
from __future__ import annotations

import threading
import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import ExternalSourceError, RateLimitedError
from app.core.logging import get_logger, log_event

logger = get_logger(__name__)

_last_call: dict[str, float] = {}
_lock = threading.Lock()

USER_AGENT = "SkyForce-ResearchPrototype/0.1 (academic, non-commercial)"


def throttle(key: str, min_interval_s: float) -> None:
    """Raise RateLimitedError if the same key was called less than ``min_interval_s`` ago."""
    with _lock:
        now = time.monotonic()
        last = _last_call.get(key)
        if last is not None and now - last < min_interval_s:
            raise RateLimitedError(
                f"Local throttle: wait {min_interval_s - (now - last):.0f}s before calling {key} again.",
                details={"min_interval_s": min_interval_s},
            )
        _last_call[key] = now


def request_with_retry(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
    source_name: str = "external",
) -> httpx.Response:
    s = get_settings()
    timeout = timeout or s.http_timeout_s
    max_retries = s.http_max_retries if max_retries is None else max_retries
    hdrs = {"User-Agent": USER_AGENT, **(headers or {})}
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = httpx.request(method, url, params=params, data=data, headers=hdrs, timeout=timeout)
            if resp.status_code == 429:
                raise RateLimitedError(f"{source_name} rate limit reached (HTTP 429).", details={"url": url})
            if resp.status_code >= 500:
                raise httpx.HTTPStatusError(f"server error {resp.status_code}", request=resp.request, response=resp)
            return resp
        except RateLimitedError:
            raise
        except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_exc = exc
            log_event(logger, "external request failed", source=source_name, attempt=attempt, error=str(exc))
            if attempt < max_retries:
                time.sleep(min(8.0, 0.5 * 2**attempt))
    raise ExternalSourceError(
        f"{source_name} unavailable after {max_retries + 1} attempts: {last_exc}", details={"url": url}
    )
