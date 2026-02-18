from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True, frozen=True)
class GeoPoint:
    latitude: float
    longitude: float


@dataclass(slots=True, frozen=True)
class GeocodeResult:
    point: GeoPoint
    country_code: str


@dataclass(slots=True, frozen=True)
class RouteData:
    coordinates: list[tuple[float, float]]
    distance_miles: float
    duration_seconds: float


@dataclass(slots=True, frozen=True)
class CandidateStation:
    station_id: int
    station_name: str
    address: str
    city: str
    state: str
    latitude: float
    longitude: float
    price_per_gallon: float
    milepost: float
    distance_from_route_miles: float


@dataclass(slots=True, frozen=True)
class FuelStopPlan:
    station: CandidateStation
    gallons_purchased: float
    cost: float
    fuel_before_gallons: float
    fuel_after_gallons: float


@dataclass(slots=True, frozen=True)
class OptimizationResult:
    optimizer_used: Literal["baseline", "ortools"]
    stops: list[FuelStopPlan]
    total_gallons_purchased: float
    total_fuel_cost: float
