from __future__ import annotations

from django.db import models


class FuelStation(models.Model):
    objects = models.Manager["FuelStation"]()

    # Original fields from CSV
    opis_truckstop_id = models.IntegerField()
    truckstop_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField(null=True, blank=True)
    retail_price = models.DecimalField(max_digits=6, decimal_places=3)
    canonical_key = models.CharField(max_length=400, unique=True)

    # Geocoding fields
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    geocode_attempts = models.PositiveIntegerField(default=0)
    is_geocode_failed = models.BooleanField(default=False)
    last_geocoded_at = models.DateTimeField(null=True, blank=True)


    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("state", "city", "truckstop_name")
        indexes = (
            models.Index(fields=["state"]),
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["canonical_key"]),
        )

    @property
    def full_address(self) -> str:
        return f"{self.address}, {self.city}, {self.state}, USA"

    def __str__(self) -> str:
        return f"{self.truckstop_name} ({self.city}, {self.state})"
