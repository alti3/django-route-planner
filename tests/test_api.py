from __future__ import annotations

import json
import re

import pytest

from route_planner.models import FuelStation
from route_planner.schemas import Coordinate, RoutePlanResponse, RouteSummaryResponse


def test_route_map_view_renders(api_client) -> None:
    response = api_client.get("/")

    assert response.status_code == 200
    body = response.content.decode()
    assert 'id="map"' in body
    assert "/api/v1/route-plan" in body
    assert 'id="optimizer"' in body
    assert 'name="vehicle_mpg"' in body
    assert 'name="tank_capacity_gallons"' in body
    assert 'name="max_range_miles"' in body
    assert re.search(r'id="max-range-miles"[\s\S]*?readonly', body)
    assert 'vehicleMpgInput.addEventListener("input", updateComputedMaxRange);' in body
    assert 'tankCapacityInput.addEventListener("input", updateComputedMaxRange);' in body
    assert 'id="planner-help-trigger"' in body
    assert 'id="start-location-help-trigger"' in body


@pytest.mark.django_db
def test_health_endpoint_returns_station_counts(api_client) -> None:
    FuelStation.objects.create(
        opis_truckstop_id=1,
        truckstop_name="Station",
        address="1 Main",
        city="Austin",
        state="TX",
        rack_id=1,
        retail_price=3.5,
        canonical_key="1 MAIN|AUSTIN|TX",
        latitude=30.1,
        longitude=-97.1,
    )
    FuelStation.objects.create(
        opis_truckstop_id=2,
        truckstop_name="Station 2",
        address="2 Main",
        city="Dallas",
        state="TX",
        rack_id=2,
        retail_price=3.8,
        canonical_key="2 MAIN|DALLAS|TX",
    )

    response = api_client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["stations"]["total"] == 2
    assert payload["stations"]["geocoded"] == 1


def test_route_plan_validation_error_returns_400(api_client) -> None:
    response = api_client.post(
        "/api/v1/route-plan",
        data=json.dumps({"start_location": "Austin, TX"}),
        content_type="application/json",
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"


@pytest.mark.django_db
def test_route_plan_success_uses_planner_response(api_client, mocker) -> None:
    fake_response = RoutePlanResponse(
        start=Coordinate(latitude=30.2672, longitude=-97.7431),
        finish=Coordinate(latitude=29.7604, longitude=-95.3698),
        optimizer_used="baseline",
        route_geojson={
            "type": "LineString",
            "coordinates": [[-97.7431, 30.2672], [-95.3698, 29.7604]],
        },
        stops=[],
        summary=RouteSummaryResponse(
            distance_miles=160.0,
            duration_minutes=160.0,
            total_gallons_purchased=0.0,
            total_fuel_cost=0.0,
            estimated_fuel_needed_gallons=16.0,
        ),
        assumptions={
            "vehicle_mpg": 10.0,
            "max_range_miles": 500.0,
            "tank_capacity_gallons": 50.0,
            "corridor_miles": 8.0,
        },
    )

    planner = mocker.Mock()
    planner.plan.return_value = fake_response
    mocker.patch("route_planner.views.get_route_planner", return_value=planner)

    response = api_client.post(
        "/api/v1/route-plan",
        data=json.dumps(
            {
                "start_location": "Austin, TX",
                "finish_location": "Houston, TX",
                "start_fuel_percent": 100,
                "corridor_miles": 8,
                "optimizer": "baseline",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["optimizer_used"] == "baseline"
    assert payload["summary"]["distance_miles"] == 160.0
    planner.plan.assert_called_once()


def test_route_plan_accepts_vehicle_overrides(api_client, mocker) -> None:
    planner = mocker.Mock()
    planner.plan.return_value = mocker.Mock(model_dump=lambda mode: {"ok": True})
    mocker.patch("route_planner.views.get_route_planner", return_value=planner)

    response = api_client.post(
        "/api/v1/route-plan",
        data=json.dumps(
            {
                "start_location": "Austin, TX",
                "finish_location": "Houston, TX",
                "start_fuel_percent": 75.0,
                "corridor_miles": 10.0,
                "optimizer": "ortools",
                "vehicle_mpg": 12.5,
                "tank_capacity_gallons": 70.0,
                "max_range_miles": 650.0,
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    planner.plan.assert_called_once()
    route_request = planner.plan.call_args.args[0]
    assert route_request.vehicle_mpg == 12.5
    assert route_request.tank_capacity_gallons == 70.0
    assert route_request.max_range_miles == 650.0
