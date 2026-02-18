from django.contrib import admin

from route_planner.models import FuelStation


@admin.register(FuelStation)
class FuelStationAdmin(admin.ModelAdmin):
    list_display = (
        "truckstop_name",
        "city",
        "state",
        "retail_price",
        "latitude",
        "longitude",
        "is_geocode_failed",
    )
    list_filter = ("state", "is_geocode_failed")
    search_fields = ("truckstop_name", "address", "city", "state")
    ordering = ("state", "city", "truckstop_name")
