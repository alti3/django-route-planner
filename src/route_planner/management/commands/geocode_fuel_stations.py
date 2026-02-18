from __future__ import annotations

import time
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from route_planner.exceptions import ExternalServiceError, InvalidLocationError
from route_planner.models import FuelStation
from route_planner.services.geocoding import GeocodingClient


class Command(BaseCommand):
    help = "Geocode imported fuel stations using Nominatim."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--limit", type=int, default=50, help="Max stations to geocode in one run"
        )
        parser.add_argument(
            "--sleep-seconds",
            type=float,
            default=1.1,
            help="Sleep interval between geocoding requests",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-geocode all stations, including already geocoded rows",
        )

    def handle(self, *_: Any, **options: Any) -> None:
        limit = max(1, options["limit"])
        sleep_seconds = max(0.0, options["sleep_seconds"])
        force = bool(options["force"])

        queryset = FuelStation.objects.all()
        if not force:
            queryset = queryset.filter(
                latitude__isnull=True, longitude__isnull=True, is_geocode_failed=False
            )

        stations = list(queryset.order_by("id")[:limit])
        if not stations:
            self.stdout.write(self.style.WARNING("No stations to geocode"))
            return

        geocoder = GeocodingClient()

        geocoded = 0
        failed = 0
        for station in stations:
            try:
                result = geocoder.geocode(station.full_address, country_code="us")
                station.latitude = result.point.latitude
                station.longitude = result.point.longitude
                station.is_geocode_failed = False
                geocoded += 1
            except (InvalidLocationError, ExternalServiceError):
                station.is_geocode_failed = True
                failed += 1
            finally:
                station.geocode_attempts += 1
                station.last_geocoded_at = timezone.now()
                station.save(
                    update_fields=[
                        "latitude",
                        "longitude",
                        "is_geocode_failed",
                        "geocode_attempts",
                        "last_geocoded_at",
                        "updated_at",
                    ]
                )
                if sleep_seconds:
                    time.sleep(sleep_seconds)

        self.stdout.write(
            self.style.SUCCESS(
                f"Geocode run complete: {geocoded} succeeded, {failed} failed (limit={limit})"
            )
        )
