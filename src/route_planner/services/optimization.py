from __future__ import annotations

from route_planner.exceptions import NoFeasibleFuelPlanError
from route_planner.services.types import CandidateStation, FuelStopPlan, OptimizationResult

EPSILON = 1e-6


def optimize_fuel_plan(
    candidates: list[CandidateStation],
    route_distance_miles: float,
    start_fuel_gallons: float,
    mpg: float,
    tank_capacity_gallons: float,
    max_range_miles: float,
    optimizer: str,
) -> OptimizationResult:
    ordered = sorted(candidates, key=lambda candidate: candidate.milepost)
    if optimizer == "ortools":
        try:
            return _optimize_with_ortools(
                ordered,
                route_distance_miles,
                start_fuel_gallons,
                mpg,
                tank_capacity_gallons,
                max_range_miles,
            )
        except Exception:
            return _optimize_baseline(
                ordered,
                route_distance_miles,
                start_fuel_gallons,
                mpg,
                tank_capacity_gallons,
                max_range_miles,
            )

    return _optimize_baseline(
        ordered,
        route_distance_miles,
        start_fuel_gallons,
        mpg,
        tank_capacity_gallons,
        max_range_miles,
    )


def _optimize_baseline(
    candidates: list[CandidateStation],
    route_distance_miles: float,
    start_fuel_gallons: float,
    mpg: float,
    tank_capacity_gallons: float,
    max_range_miles: float,
) -> OptimizationResult:
    if route_distance_miles <= start_fuel_gallons * mpg + EPSILON:
        return OptimizationResult(
            optimizer_used="baseline",
            stops=[],
            total_gallons_purchased=0.0,
            total_fuel_cost=0.0,
        )

    if not candidates:
        raise NoFeasibleFuelPlanError("No candidate stations available along route")

    effective_max_range_miles = min(max_range_miles, tank_capacity_gallons * mpg)
    current_fuel = start_fuel_gallons
    previous_milepost = 0.0
    stops: list[FuelStopPlan] = []

    for index, station in enumerate(candidates):
        travel_miles = station.milepost - previous_milepost
        if travel_miles < -EPSILON:
            continue

        current_fuel -= travel_miles / mpg
        if current_fuel < -EPSILON:
            raise NoFeasibleFuelPlanError("Cannot reach next station with available fuel")
        current_fuel = max(current_fuel, 0.0)

        remaining_distance = route_distance_miles - station.milepost
        if remaining_distance <= current_fuel * mpg + EPSILON:
            previous_milepost = station.milepost
            continue

        reachable_stations = [
            candidate
            for candidate in candidates[index + 1 :]
            if candidate.milepost - station.milepost <= effective_max_range_miles + EPSILON
        ]
        can_reach_end_with_full_tank = remaining_distance <= effective_max_range_miles + EPSILON
        if not reachable_stations and not can_reach_end_with_full_tank:
            raise NoFeasibleFuelPlanError("Route contains a gap longer than the vehicle range")

        cheaper_station = next(
            (
                candidate
                for candidate in reachable_stations
                if candidate.price_per_gallon + EPSILON < station.price_per_gallon
            ),
            None,
        )

        if cheaper_station is not None:
            target_milepost = cheaper_station.milepost
        elif can_reach_end_with_full_tank:
            target_milepost = route_distance_miles
        else:
            target_milepost = reachable_stations[-1].milepost

        required_fuel = max(0.0, (target_milepost - station.milepost) / mpg)
        gallons_to_buy = min(
            tank_capacity_gallons - current_fuel, max(0.0, required_fuel - current_fuel)
        )

        if gallons_to_buy > EPSILON:
            fuel_before = current_fuel
            fuel_after = fuel_before + gallons_to_buy
            stops.append(
                FuelStopPlan(
                    station=station,
                    gallons_purchased=gallons_to_buy,
                    cost=gallons_to_buy * station.price_per_gallon,
                    fuel_before_gallons=fuel_before,
                    fuel_after_gallons=fuel_after,
                )
            )
            current_fuel = fuel_after

        previous_milepost = station.milepost

    remaining_to_finish = route_distance_miles - previous_milepost
    current_fuel -= remaining_to_finish / mpg
    if current_fuel < -EPSILON:
        raise NoFeasibleFuelPlanError(
            "Cannot reach destination with available stations and constraints"
        )

    total_gallons = sum(stop.gallons_purchased for stop in stops)
    total_cost = sum(stop.cost for stop in stops)
    return OptimizationResult(
        optimizer_used="baseline",
        stops=stops,
        total_gallons_purchased=total_gallons,
        total_fuel_cost=total_cost,
    )


def _optimize_with_ortools(
    candidates: list[CandidateStation],
    route_distance_miles: float,
    start_fuel_gallons: float,
    mpg: float,
    tank_capacity_gallons: float,
    max_range_miles: float,
) -> OptimizationResult:
    if route_distance_miles <= start_fuel_gallons * mpg + EPSILON:
        return OptimizationResult(
            optimizer_used="ortools",
            stops=[],
            total_gallons_purchased=0.0,
            total_fuel_cost=0.0,
        )

    if not candidates:
        raise NoFeasibleFuelPlanError("No candidate stations available along route")

    try:
        from ortools.linear_solver import pywraplp
    except ImportError as exc:
        raise NoFeasibleFuelPlanError("OR-Tools is not available") from exc

    effective_max_range_miles = min(max_range_miles, tank_capacity_gallons * mpg)
    point_miles = [0.0, *[station.milepost for station in candidates], route_distance_miles]

    for index in range(len(point_miles) - 1):
        if point_miles[index + 1] + EPSILON < point_miles[index]:
            raise NoFeasibleFuelPlanError("Stations are not ordered correctly")
        if point_miles[index + 1] - point_miles[index] > effective_max_range_miles + EPSILON:
            raise NoFeasibleFuelPlanError("Route contains a gap longer than the vehicle range")

    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:
        raise NoFeasibleFuelPlanError("Could not initialize OR-Tools solver")

    fuel_before = [
        solver.NumVar(0.0, tank_capacity_gallons, f"fuel_before_{index}")
        for index in range(len(point_miles))
    ]
    station_buy = {
        station_index: solver.NumVar(0.0, tank_capacity_gallons, f"buy_{station_index}")
        for station_index in range(1, len(point_miles) - 1)
    }

    solver.Add(fuel_before[0] == start_fuel_gallons)

    for index in range(len(point_miles) - 1):
        next_index = index + 1
        travel_miles = point_miles[next_index] - point_miles[index]
        fuel_used = travel_miles / mpg

        buy_here = station_buy.get(index)
        if buy_here is None:
            solver.Add(fuel_before[next_index] == fuel_before[index] - fuel_used)
            solver.Add(fuel_before[index] <= tank_capacity_gallons)
        else:
            solver.Add(fuel_before[index] + buy_here <= tank_capacity_gallons)
            solver.Add(fuel_before[next_index] == fuel_before[index] + buy_here - fuel_used)

    objective = solver.Objective()
    for station_index, station in enumerate(candidates, start=1):
        objective.SetCoefficient(station_buy[station_index], station.price_per_gallon)
    objective.SetMinimization()

    result_status = solver.Solve()
    if result_status != pywraplp.Solver.OPTIMAL:
        raise NoFeasibleFuelPlanError("No feasible solution for fuel optimization")

    stops: list[FuelStopPlan] = []
    total_gallons = 0.0
    total_cost = 0.0

    for station_index, station in enumerate(candidates, start=1):
        gallons = station_buy[station_index].solution_value()
        if gallons <= 1e-4:
            continue

        fuel_before_value = fuel_before[station_index].solution_value()
        fuel_after_value = fuel_before_value + gallons
        cost = gallons * station.price_per_gallon

        stops.append(
            FuelStopPlan(
                station=station,
                gallons_purchased=gallons,
                cost=cost,
                fuel_before_gallons=fuel_before_value,
                fuel_after_gallons=fuel_after_value,
            )
        )
        total_gallons += gallons
        total_cost += cost

    return OptimizationResult(
        optimizer_used="ortools",
        stops=stops,
        total_gallons_purchased=total_gallons,
        total_fuel_cost=total_cost,
    )
