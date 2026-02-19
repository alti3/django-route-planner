from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx
from django.conf import settings
from django.core.cache import cache

from route_planner.exceptions import ExternalServiceError, NoRouteFoundError
from route_planner.services.types import GeoPoint, RouteData

METERS_TO_MILES = 0.000621371


class OsrmClient:
    def __init__(self) -> None:
        self.base_url = settings.OSRM_BASE_URL.rstrip("/")
        self.timeout = settings.OSRM_TIMEOUT_SECONDS
        self.retry_count = settings.OSRM_RETRY_COUNT

    def route(self, start: GeoPoint, finish: GeoPoint) -> RouteData:
        return self.route_through([start, finish])

    def route_through(self, waypoints: list[GeoPoint]) -> RouteData:
        if len(waypoints) < 2:
            raise NoRouteFoundError("At least two route waypoints are required")

        cache_key = self._cache_key(waypoints)
        cached = cache.get(cache_key)
        if cached:
            return RouteData(
                coordinates=[tuple(coord) for coord in cached["coordinates"]],
                distance_miles=cached["distance_miles"],
                duration_seconds=cached["duration_seconds"],
            )

        coordinates = ";".join(f"{point.longitude:.6f},{point.latitude:.6f}" for point in waypoints)
        endpoint = f"{self.base_url}/route/v1/driving/{coordinates}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
            "annotations": "false",
        }

        for attempt in range(self.retry_count + 1):
            try:
                response = httpx.get(endpoint, params=params, timeout=self.timeout)
                response.raise_for_status()
                route_data = self._parse_response(response.json())
                cache.set(
                    cache_key,
                    {
                        "coordinates": route_data.coordinates,
                        "distance_miles": route_data.distance_miles,
                        "duration_seconds": route_data.duration_seconds,
                    },
                    timeout=settings.ROUTE_CACHE_TTL_SECONDS,
                )
                return route_data
            except NoRouteFoundError:
                raise
            except httpx.HTTPError as exc:
                if attempt >= self.retry_count:
                    raise ExternalServiceError("OSRM request failed") from exc
                time.sleep(0.3 * (attempt + 1))

        raise ExternalServiceError("OSRM request failed")

    @staticmethod
    def _cache_key(waypoints: list[GeoPoint]) -> str:
        encoded = "|".join(
            f"{point.latitude:.5f}:{point.longitude:.5f}" for point in waypoints
        ).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        return f"route:{digest}"

    @staticmethod
    def _parse_response(payload: Any) -> RouteData:
        if payload.get("code") != "Ok":
            raise NoRouteFoundError("Could not compute route")

        routes = payload.get("routes") or []
        if not routes:
            raise NoRouteFoundError("Could not compute route")

        first = routes[0]
        coordinates = [tuple(coord) for coord in first.get("geometry", {}).get("coordinates", [])]
        if len(coordinates) < 2:
            raise NoRouteFoundError("Route geometry unavailable")

        distance_miles = float(first.get("distance", 0.0)) * METERS_TO_MILES
        duration_seconds = float(first.get("duration", 0.0))
        return RouteData(
            coordinates=coordinates,
            distance_miles=distance_miles,
            duration_seconds=duration_seconds,
        )
