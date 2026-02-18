from __future__ import annotations

import json
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from pydantic import ValidationError

from route_planner.exceptions import (
    ExternalServiceError,
    InvalidLocationError,
    NoFeasibleFuelPlanError,
    NoRouteFoundError,
)
from route_planner.models import FuelStation
from route_planner.schemas import RoutePlanRequest
from route_planner.services.planner import RoutePlannerService

_planner_service: RoutePlannerService | None = None


def get_route_planner() -> RoutePlannerService:
    global _planner_service
    if _planner_service is None:
        _planner_service = RoutePlannerService()
    return _planner_service


@require_GET
def route_map_view(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "route_planner/route_map.html",
        {
            "defaults": {
                "start_fuel_percent": 100.0,
                "corridor_miles": float(settings.DEFAULT_CORRIDOR_MILES),
                "optimizer": "baseline",
                "vehicle_mpg": float(settings.VEHICLE_MPG),
                "tank_capacity_gallons": float(settings.FUEL_TANK_GALLONS),
                "max_range_miles": float(settings.MAX_RANGE_MILES),
            }
        },
    )


@require_GET
def health_view(_: HttpRequest) -> HttpResponse:
    total_stations = FuelStation.objects.count()
    geocoded_stations = (
        FuelStation.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True).count()
    )
    return JsonResponse(
        {
            "status": "ok",
            "stations": {
                "total": total_stations,
                "geocoded": geocoded_stations,
            },
        }
    )


@csrf_exempt
@require_POST
def route_plan_view(request: HttpRequest) -> HttpResponse:
    payload = _parse_json_payload(request)
    if isinstance(payload, JsonResponse):
        return payload

    try:
        route_request = RoutePlanRequest.model_validate(payload)
    except ValidationError as exc:
        return JsonResponse(
            {
                "error": {
                    "code": "validation_error",
                    "message": "Invalid request payload",
                    "details": exc.errors(),
                }
            },
            status=400,
        )

    planner = get_route_planner()
    try:
        response = planner.plan(route_request)
    except InvalidLocationError as exc:
        return _error_response("invalid_location", str(exc), status=400)
    except NoFeasibleFuelPlanError as exc:
        return _error_response("no_feasible_plan", str(exc), status=422)
    except NoRouteFoundError as exc:
        return _error_response("no_route", str(exc), status=502)
    except ExternalServiceError as exc:
        return _error_response("upstream_error", str(exc), status=502)

    return JsonResponse(response.model_dump(mode="json"), status=200)


def _parse_json_payload(request: HttpRequest) -> dict[str, Any] | JsonResponse:
    if not request.body:
        return {}

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return _error_response("invalid_json", "Request body must be valid JSON", status=400)

    if not isinstance(payload, dict):
        return _error_response("invalid_json", "JSON body must be an object", status=400)

    return payload


def _error_response(code: str, message: str, status: int) -> JsonResponse:
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)
