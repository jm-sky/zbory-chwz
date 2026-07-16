"""Server-side geocoding of congregation addresses via Nominatim (OpenStreetMap).

Called server-side (rather than from the browser) so the required
User-Agent header and the 1 request/second throttling Nominatim's usage
policy demands are enforced in one place, regardless of how many admins are
editing addresses concurrently.

Limitation: the throttle below is a single asyncio.Lock scoped to this
process. It correctly serializes requests within one backend worker, but
does NOT coordinate across multiple worker processes/instances - at the
current scale (a handful of admins editing addresses) that's not a real
constraint, but if the backend is ever scaled horizontally, this lock
should move to Redis (already a dependency, see app.core.config.RedisSettings).
"""

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_MIN_REQUEST_INTERVAL_SECONDS = 1.1
_lock = asyncio.Lock()
_last_request_at = 0.0


@dataclass
class GeocodeResult:
    latitude: float
    longitude: float
    display_name: str
    confidence: str  # "exact" | "approximate"


async def _throttle() -> None:
    """Block until at least _MIN_REQUEST_INTERVAL_SECONDS have passed since
    the last Nominatim request made by this process."""
    global _last_request_at
    async with _lock:
        elapsed = time.monotonic() - _last_request_at
        wait_for = _MIN_REQUEST_INTERVAL_SECONDS - elapsed
        if wait_for > 0:
            await asyncio.sleep(wait_for)
        _last_request_at = time.monotonic()


def _build_query(street: str | None, city: str, postal_code: str | None, province: str | None) -> str:
    parts = [part for part in [street, postal_code, city, province] if part]
    return ", ".join(parts)


async def geocode_address(
    *,
    street: str | None,
    city: str,
    postal_code: str | None,
    province: str | None,
    country: str,
) -> GeocodeResult | None:
    """Look up coordinates for an address via Nominatim.

    Returns None if geocoding is disabled, the request fails, or no match is
    found - callers should treat that as "not_found"/"failed", not raise.
    """
    if not settings.nominatim.enabled:
        return None

    query = _build_query(street, city, postal_code, province)
    if not query:
        return None

    await _throttle()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.nominatim.base_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": country.lower(),
                },
                headers={"User-Agent": settings.nominatim.user_agent},
                timeout=10.0,
            )
            response.raise_for_status()
            results = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(f"Nominatim geocoding request failed for {query!r}: {exc}")
        return None

    if not results:
        return None

    match = results[0]
    try:
        return GeocodeResult(
            latitude=float(match["lat"]),
            longitude=float(match["lon"]),
            display_name=match.get("display_name", query),
            confidence="exact" if street else "approximate",
        )
    except (KeyError, ValueError) as exc:
        logger.warning(f"Nominatim returned an unexpected result shape for {query!r}: {exc}")
        return None
