from __future__ import annotations

import pytest

from route_planner.exceptions import NoFeasibleFuelPlanError
from route_planner.services.optimization import optimize_fuel_plan
from route_planner.services.types import CandidateStation


def _station(station_id: int, milepost: float, price: float) -> CandidateStation:
    return CandidateStation(
        station_id=station_id,
        station_name=f"Station {station_id}",
        address="123 Test St",
        city="Test City",
        state="TX",
        latitude=30.0,
        longitude=-97.0,
        price_per_gallon=price,
        milepost=milepost,
        distance_from_route_miles=1.0,
    )


def test_baseline_optimizer_returns_stops_and_cost() -> None:
    candidates = [
        _station(1, 80.0, 4.0),
        _station(2, 160.0, 3.0),
        _station(3, 240.0, 4.2),
    ]

    result = optimize_fuel_plan(
        candidates=candidates,
        route_distance_miles=300.0,
        start_fuel_gallons=10.0,
        mpg=10.0,
        tank_capacity_gallons=50.0,
        max_range_miles=500.0,
        optimizer="baseline",
    )

    assert result.optimizer_used == "baseline"
    assert len(result.stops) >= 1
    assert result.total_gallons_purchased > 0
    assert result.total_fuel_cost > 0


def test_infeasible_plan_raises_error() -> None:
    candidates = [_station(1, 450.0, 3.5)]

    with pytest.raises(NoFeasibleFuelPlanError):
        optimize_fuel_plan(
            candidates=candidates,
            route_distance_miles=700.0,
            start_fuel_gallons=20.0,
            mpg=10.0,
            tank_capacity_gallons=50.0,
            max_range_miles=500.0,
            optimizer="baseline",
        )


def test_ortools_optimizer_is_not_more_expensive_than_baseline() -> None:
    candidates = [
        _station(1, 60.0, 4.1),
        _station(2, 120.0, 3.8),
        _station(3, 180.0, 3.4),
        _station(4, 260.0, 3.9),
    ]

    baseline = optimize_fuel_plan(
        candidates=candidates,
        route_distance_miles=330.0,
        start_fuel_gallons=9.0,
        mpg=10.0,
        tank_capacity_gallons=50.0,
        max_range_miles=500.0,
        optimizer="baseline",
    )
    ortools = optimize_fuel_plan(
        candidates=candidates,
        route_distance_miles=330.0,
        start_fuel_gallons=9.0,
        mpg=10.0,
        tank_capacity_gallons=50.0,
        max_range_miles=500.0,
        optimizer="ortools",
    )

    assert ortools.optimizer_used in {"ortools", "baseline"}
    assert ortools.total_fuel_cost <= baseline.total_fuel_cost + 1e-4


def test_max_range_override_restricts_reachability() -> None:
    candidates = [_station(1, 180.0, 3.7), _station(2, 340.0, 3.6)]

    with pytest.raises(NoFeasibleFuelPlanError):
        optimize_fuel_plan(
            candidates=candidates,
            route_distance_miles=400.0,
            start_fuel_gallons=20.0,
            mpg=10.0,
            tank_capacity_gallons=50.0,
            max_range_miles=150.0,
            optimizer="baseline",
        )
