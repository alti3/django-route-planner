from __future__ import annotations

from collections import defaultdict

from django.conf import settings

from route_planner.models import FuelStation
from route_planner.services.geo import haversine_miles, lon_lat_to_miles_xy
from route_planner.services.types import CandidateStation


class StationSelector:
    def select_candidate_stations(
        self,
        route_coordinates: list[tuple[float, float]],
        corridor_miles: float,
    ) -> list[CandidateStation]:
        if len(route_coordinates) < 2:
            return []

        simplified_coordinates = self._simplify_route(route_coordinates, max_points=1500)
        cumulative_miles = self._build_cumulative_miles(simplified_coordinates)

        lon_values = [coord[0] for coord in simplified_coordinates]
        lat_values = [coord[1] for coord in simplified_coordinates]
        margin = corridor_miles / 69.0

        stations = FuelStation.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            longitude__gte=min(lon_values) - margin,
            longitude__lte=max(lon_values) + margin,
            latitude__gte=min(lat_values) - margin,
            latitude__lte=max(lat_values) + margin,
        ).only(
            "id",
            "truckstop_name",
            "address",
            "city",
            "state",
            "latitude",
            "longitude",
            "retail_price",
        )

        candidates: list[CandidateStation] = []
        for station in stations.iterator(chunk_size=1000):
            if station.latitude is None or station.longitude is None:
                continue
            distance_from_route, milepost = self._project_station(
                station.longitude,
                station.latitude,
                simplified_coordinates,
                cumulative_miles,
            )
            if distance_from_route > corridor_miles:
                continue

            candidates.append(
                CandidateStation(
                    station_id=station.id,
                    station_name=station.truckstop_name,
                    address=station.address,
                    city=station.city,
                    state=station.state,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    price_per_gallon=float(station.retail_price),
                    milepost=milepost,
                    distance_from_route_miles=distance_from_route,
                )
            )

        return self._reduce_candidates(candidates, settings.MAX_CANDIDATE_STATIONS)

    @staticmethod
    def _simplify_route(
        route_coordinates: list[tuple[float, float]], max_points: int
    ) -> list[tuple[float, float]]:
        if len(route_coordinates) <= max_points:
            return route_coordinates

        step = max(1, len(route_coordinates) // max_points)
        simplified = route_coordinates[::step]
        if simplified[-1] != route_coordinates[-1]:
            simplified.append(route_coordinates[-1])
        return simplified

    @staticmethod
    def _build_cumulative_miles(route_coordinates: list[tuple[float, float]]) -> list[float]:
        cumulative = [0.0]
        for index in range(1, len(route_coordinates)):
            prev_lon, prev_lat = route_coordinates[index - 1]
            lon, lat = route_coordinates[index]
            cumulative.append(cumulative[-1] + haversine_miles(prev_lat, prev_lon, lat, lon))
        return cumulative

    @staticmethod
    def _project_station(
        station_lon: float,
        station_lat: float,
        route_coordinates: list[tuple[float, float]],
        cumulative_miles: list[float],
    ) -> tuple[float, float]:
        best_distance = float("inf")
        best_milepost = 0.0

        for index in range(len(route_coordinates) - 1):
            start_lon, start_lat = route_coordinates[index]
            end_lon, end_lat = route_coordinates[index + 1]
            ref_lat = (start_lat + end_lat) / 2.0

            start_x, start_y = lon_lat_to_miles_xy(start_lon, start_lat, ref_lat)
            end_x, end_y = lon_lat_to_miles_xy(end_lon, end_lat, ref_lat)
            point_x, point_y = lon_lat_to_miles_xy(station_lon, station_lat, ref_lat)

            vector_x = end_x - start_x
            vector_y = end_y - start_y
            vector_norm_sq = vector_x * vector_x + vector_y * vector_y
            if vector_norm_sq == 0:
                continue

            t = ((point_x - start_x) * vector_x + (point_y - start_y) * vector_y) / vector_norm_sq
            t = max(0.0, min(1.0, t))

            projected_x = start_x + t * vector_x
            projected_y = start_y + t * vector_y
            distance = ((point_x - projected_x) ** 2 + (point_y - projected_y) ** 2) ** 0.5

            if distance < best_distance:
                segment_length = cumulative_miles[index + 1] - cumulative_miles[index]
                best_distance = distance
                best_milepost = cumulative_miles[index] + (t * segment_length)

        return best_distance, best_milepost

    @staticmethod
    def _reduce_candidates(
        candidates: list[CandidateStation], max_candidates: int
    ) -> list[CandidateStation]:
        ordered = sorted(
            candidates, key=lambda candidate: (candidate.milepost, candidate.price_per_gallon)
        )
        if len(ordered) <= max_candidates:
            return ordered

        buckets: dict[int, list[CandidateStation]] = defaultdict(list)
        for candidate in ordered:
            bucket = int(candidate.milepost // 25)
            if len(buckets[bucket]) < 3:
                buckets[bucket].append(candidate)

        reduced: list[CandidateStation] = []
        for bucket in sorted(buckets):
            reduced.extend(sorted(buckets[bucket], key=lambda value: value.price_per_gallon))

        if len(reduced) > max_candidates:
            reduced = sorted(reduced, key=lambda value: value.price_per_gallon)[:max_candidates]

        return sorted(
            reduced, key=lambda candidate: (candidate.milepost, candidate.price_per_gallon)
        )
