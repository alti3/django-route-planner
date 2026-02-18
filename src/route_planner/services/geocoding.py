from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx
from django.conf import settings
from django.core.cache import cache

from route_planner.exceptions import ExternalServiceError, InvalidLocationError
from route_planner.services.types import GeocodeResult, GeoPoint


class GeocodingClient:
    def __init__(self) -> None:
        self.base_url = settings.GEOCODING_BASE_URL.rstrip("/")
        self.timeout = settings.GEOCODING_TIMEOUT_SECONDS
        self.retry_count = settings.GEOCODING_RETRY_COUNT
        self.user_agent = settings.GEOCODING_USER_AGENT

    def geocode(self, query: str, *, country_code: str = "us") -> GeocodeResult:
        cache_key = self._cache_key(query, country_code)
        cached = cache.get(cache_key)
        if cached:
            return GeocodeResult(
                point=GeoPoint(latitude=cached["latitude"], longitude=cached["longitude"]),
                country_code=cached["country_code"],
            )

        params = {
            "q": query,
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
        }
        if country_code:
            params["countrycodes"] = country_code

        for attempt in range(self.retry_count + 1):
            try:
                response = httpx.get(
                    f"{self.base_url}/search",
                    params=params,
                    timeout=self.timeout,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": self.user_agent,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                result = self._parse_result(payload, country_code)
                cache.set(
                    cache_key,
                    {
                        "latitude": result.point.latitude,
                        "longitude": result.point.longitude,
                        "country_code": result.country_code,
                    },
                    timeout=settings.GEOCODE_CACHE_TTL_SECONDS,
                )
                return result
            except InvalidLocationError:
                raise
            except httpx.HTTPError as exc:
                if attempt >= self.retry_count:
                    raise ExternalServiceError("Geocoding request failed") from exc
                time.sleep(0.3 * (attempt + 1))

        raise ExternalServiceError("Geocoding request failed")

    @staticmethod
    def _cache_key(query: str, country_code: str) -> str:
        digest = hashlib.sha256(f"{query.lower()}|{country_code}".encode()).hexdigest()
        return f"geocode:{digest}"

    @staticmethod
    def _parse_result(payload: Any, expected_country: str) -> GeocodeResult:
        if not isinstance(payload, list) or not payload:
            raise InvalidLocationError("Location could not be resolved")

        first = payload[0]
        try:
            latitude = float(first["lat"])
            longitude = float(first["lon"])
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidLocationError("Invalid geocoding response") from exc

        country_code = str(first.get("address", {}).get("country_code", "")).lower()
        if expected_country and country_code and country_code != expected_country.lower():
            raise InvalidLocationError("Location must be within the USA")

        return GeocodeResult(
            point=GeoPoint(latitude=latitude, longitude=longitude),
            country_code=country_code,
        )
