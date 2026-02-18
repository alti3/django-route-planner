from __future__ import annotations

from django.conf import settings

from route_planner.schemas import (
    Coordinate,
    FuelStopResponse,
    RoutePlanRequest,
    RoutePlanResponse,
    RouteSummaryResponse,
)
from route_planner.services.geocoding import GeocodingClient
from route_planner.services.optimization import optimize_fuel_plan
from route_planner.services.osrm import OsrmClient
from route_planner.services.station_selection import StationSelector


class RoutePlannerService:
    def __init__(
        self,
        geocoding_client: GeocodingClient | None = None,
        osrm_client: OsrmClient | None = None,
        station_selector: StationSelector | None = None,
    ) -> None:
        self.geocoding_client = geocoding_client or GeocodingClient()
        self.osrm_client = osrm_client or OsrmClient()
        self.station_selector = station_selector or StationSelector()

    def plan(self, request: RoutePlanRequest) -> RoutePlanResponse:
        vehicle_mpg = request.vehicle_mpg or float(settings.VEHICLE_MPG)
        tank_capacity_gallons = request.tank_capacity_gallons or float(settings.FUEL_TANK_GALLONS)
        max_range_miles = request.max_range_miles or float(settings.MAX_RANGE_MILES)

        start_geocode = self.geocoding_client.geocode(request.start_location, country_code="us")
        finish_geocode = self.geocoding_client.geocode(request.finish_location, country_code="us")

        route = self.osrm_client.route(start_geocode.point, finish_geocode.point)

        candidates = self.station_selector.select_candidate_stations(
            route_coordinates=route.coordinates,
            corridor_miles=request.corridor_miles,
        )

        start_fuel_gallons = tank_capacity_gallons * (request.start_fuel_percent / 100.0)
        optimization = optimize_fuel_plan(
            candidates=candidates,
            route_distance_miles=route.distance_miles,
            start_fuel_gallons=start_fuel_gallons,
            mpg=vehicle_mpg,
            tank_capacity_gallons=tank_capacity_gallons,
            max_range_miles=max_range_miles,
            optimizer=request.optimizer,
        )

        stops = [
            FuelStopResponse(
                station_id=stop.station.station_id,
                station_name=stop.station.station_name,
                address=stop.station.address,
                city=stop.station.city,
                state=stop.station.state,
                latitude=stop.station.latitude,
                longitude=stop.station.longitude,
                milepost=round(stop.station.milepost, 3),
                distance_from_route_miles=round(stop.station.distance_from_route_miles, 3),
                price_per_gallon=round(stop.station.price_per_gallon, 3),
                gallons_purchased=round(stop.gallons_purchased, 3),
                cost=round(stop.cost, 2),
                fuel_before_gallons=round(stop.fuel_before_gallons, 3),
                fuel_after_gallons=round(stop.fuel_after_gallons, 3),
            )
            for stop in optimization.stops
        ]

        summary = RouteSummaryResponse(
            distance_miles=round(route.distance_miles, 3),
            duration_minutes=round(route.duration_seconds / 60.0, 2),
            total_gallons_purchased=round(optimization.total_gallons_purchased, 3),
            total_fuel_cost=round(optimization.total_fuel_cost, 2),
            estimated_fuel_needed_gallons=round(route.distance_miles / vehicle_mpg, 3),
        )

        return RoutePlanResponse(
            start=Coordinate(
                latitude=round(start_geocode.point.latitude, 6),
                longitude=round(start_geocode.point.longitude, 6),
            ),
            finish=Coordinate(
                latitude=round(finish_geocode.point.latitude, 6),
                longitude=round(finish_geocode.point.longitude, 6),
            ),
            optimizer_used=optimization.optimizer_used,
            route_geojson={
                "type": "LineString",
                "coordinates": route.coordinates,
            },
            stops=stops,
            summary=summary,
            assumptions={
                "vehicle_mpg": vehicle_mpg,
                "max_range_miles": max_range_miles,
                "tank_capacity_gallons": tank_capacity_gallons,
                "corridor_miles": float(request.corridor_miles),
            },
        )
