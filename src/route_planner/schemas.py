from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RoutePlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_location: str = Field(min_length=3, max_length=300)
    finish_location: str = Field(min_length=3, max_length=300)
    start_fuel_percent: float = Field(default=100.0, ge=0.0, le=100.0)
    corridor_miles: float = Field(default=8.0, ge=1.0, le=50.0)
    vehicle_mpg: float | None = Field(default=None, gt=0.0, le=100.0)
    tank_capacity_gallons: float | None = Field(default=None, gt=0.0, le=300.0)
    max_range_miles: float | None = Field(default=None, gt=0.0, le=2000.0)
    optimizer: Literal["baseline", "ortools"] = "baseline"


class Coordinate(BaseModel):
    latitude: float
    longitude: float


class FuelStopResponse(BaseModel):
    station_id: int
    station_name: str
    address: str
    city: str
    state: str
    latitude: float
    longitude: float
    milepost: float
    distance_from_route_miles: float
    price_per_gallon: float
    gallons_purchased: float
    cost: float
    fuel_before_gallons: float
    fuel_after_gallons: float


class RouteSummaryResponse(BaseModel):
    distance_miles: float
    duration_minutes: float
    total_gallons_purchased: float
    total_fuel_cost: float
    estimated_fuel_needed_gallons: float


class RoutePlanResponse(BaseModel):
    start: Coordinate
    finish: Coordinate
    optimizer_used: Literal["baseline", "ortools"]
    route_geojson: dict
    stops: list[FuelStopResponse]
    summary: RouteSummaryResponse
    assumptions: dict[str, float]
