"""Unit tests for Nominatim geocoding: throttling, response parsing, and the
not-found/error paths. The Nominatim HTTP call is faked so these tests never
touch the network."""

import time

import pytest

from app.modules.congregations import geocoding


class _FakeResponse:
    def __init__(self, data: object) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        pass

    def json(self) -> object:
        return self._data


def _fake_client(data: object, *, captured_headers: dict | None = None):
    class _FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None, headers=None, timeout=None):
            if captured_headers is not None:
                captured_headers.update(headers or {})
            return _FakeResponse(data)

    return _FakeAsyncClient


@pytest.fixture(autouse=True)
def _fast_throttle(monkeypatch):
    """Keep the 1.1s real-world throttle out of the way for tests that
    aren't specifically exercising it."""
    monkeypatch.setattr(geocoding, "_MIN_REQUEST_INTERVAL_SECONDS", 0.05)
    monkeypatch.setattr(geocoding, "_last_request_at", 0.0)


@pytest.mark.asyncio
async def test_geocode_address_returns_exact_match_with_street(monkeypatch) -> None:
    headers: dict = {}
    monkeypatch.setattr(
        geocoding.httpx,
        "AsyncClient",
        _fake_client(
            [{"lat": "51.1079", "lon": "17.0385", "display_name": "Wrocław, Poland"}],
            captured_headers=headers,
        ),
    )

    result = await geocoding.geocode_address(
        street="Rynek 1",
        city="Wrocław",
        postal_code="50-101",
        province="dolnoslaskie",
        country="PL",
    )

    assert result is not None
    assert result.latitude == pytest.approx(51.1079)
    assert result.longitude == pytest.approx(17.0385)
    assert result.display_name == "Wrocław, Poland"
    assert result.confidence == "exact"
    assert headers["User-Agent"]


@pytest.mark.asyncio
async def test_geocode_address_strips_polish_street_prefix(monkeypatch) -> None:
    """Nominatim returns no results for "ul. Marszałkowska 1, Warszawa" but
    does match "Marszałkowska 1, Warszawa" - the "ul." prefix must be
    stripped before querying."""
    captured_params: dict = {}

    class _FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None, headers=None, timeout=None):
            captured_params.update(params or {})
            return _FakeResponse(
                [
                    {
                        "lat": "52.2141815",
                        "lon": "21.0210292",
                        "display_name": "Marszałkowska 1, Warszawa",
                    }
                ]
            )

    monkeypatch.setattr(geocoding.httpx, "AsyncClient", _FakeAsyncClient)

    result = await geocoding.geocode_address(
        street="ul. Marszałkowska 1",
        city="Warszawa",
        postal_code="00-590",
        province="mazowieckie",
        country="PL",
    )

    assert result is not None
    assert "ul." not in captured_params["q"]
    assert captured_params["q"].startswith("Marszałkowska 1")


@pytest.mark.asyncio
async def test_geocode_address_without_street_is_approximate(monkeypatch) -> None:
    monkeypatch.setattr(
        geocoding.httpx,
        "AsyncClient",
        _fake_client([{"lat": "50.0", "lon": "20.0", "display_name": "Some City"}]),
    )

    result = await geocoding.geocode_address(street=None, city="Kraków", postal_code=None, province=None, country="PL")

    assert result is not None
    assert result.confidence == "approximate"


@pytest.mark.asyncio
async def test_geocode_address_returns_none_when_no_results(monkeypatch) -> None:
    monkeypatch.setattr(geocoding.httpx, "AsyncClient", _fake_client([]))

    result = await geocoding.geocode_address(
        street=None,
        city="Nieistniejące Miasto",
        postal_code=None,
        province=None,
        country="PL",
    )

    assert result is None


@pytest.mark.asyncio
async def test_geocode_address_returns_none_on_malformed_result(monkeypatch) -> None:
    monkeypatch.setattr(
        geocoding.httpx,
        "AsyncClient",
        _fake_client([{"display_name": "Missing lat/lon"}]),
    )

    result = await geocoding.geocode_address(street=None, city="Wrocław", postal_code=None, province=None, country="PL")

    assert result is None


@pytest.mark.asyncio
async def test_geocode_address_disabled_returns_none_without_calling_client(
    monkeypatch,
) -> None:
    monkeypatch.setattr(geocoding.settings.nominatim, "enabled", False)

    def _boom(*args, **kwargs):
        raise AssertionError("HTTP client should not be constructed when geocoding is disabled")

    monkeypatch.setattr(geocoding.httpx, "AsyncClient", _boom)

    result = await geocoding.geocode_address(street=None, city="Wrocław", postal_code=None, province=None, country="PL")

    assert result is None


@pytest.mark.asyncio
async def test_throttle_enforces_minimum_interval_between_calls(monkeypatch) -> None:
    monkeypatch.setattr(geocoding, "_MIN_REQUEST_INTERVAL_SECONDS", 0.2)
    monkeypatch.setattr(geocoding, "_last_request_at", 0.0)

    start = time.monotonic()
    await geocoding._throttle()
    await geocoding._throttle()
    elapsed = time.monotonic() - start

    assert elapsed >= 0.2
