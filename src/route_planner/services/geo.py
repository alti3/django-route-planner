from __future__ import annotations

import math

EARTH_RADIUS_MILES = 3958.7613
MILES_PER_DEGREE_LAT = 69.0


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2.0) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_MILES * c


def lon_lat_to_miles_xy(lon: float, lat: float, ref_lat: float) -> tuple[float, float]:
    miles_per_degree_lon = MILES_PER_DEGREE_LAT * math.cos(math.radians(ref_lat))
    return lon * miles_per_degree_lon, lat * MILES_PER_DEGREE_LAT
