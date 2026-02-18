from __future__ import annotations

from pathlib import Path

import pytest
from django.core.management import call_command

from route_planner.models import FuelStation


@pytest.mark.django_db
def test_import_fuel_prices_deduplicates_and_uses_cheapest(tmp_path: Path) -> None:
    csv_path = tmp_path / "stations.csv"
    csv_path.write_text(
        "\n".join(
            [
                "OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price",
                "1,Stop A,100 Main St,Tulsa,OK,10,3.500",
                "2,Stop A Duplicate,100 Main St,Tulsa,OK,11,3.200",
                "3,Stop B,200 River Rd,Denver,CO,20,0",
                "4,Stop C,300 Lake Dr,Austin,TX,30,3.900",
            ]
        ),
        encoding="utf-8",
    )

    call_command("import_fuel_prices", csv_path=str(csv_path))

    stations = list(FuelStation.objects.order_by("canonical_key"))
    assert len(stations) == 2

    tulsa = FuelStation.objects.get(canonical_key="100 MAIN ST|TULSA|OK")
    assert float(tulsa.retail_price) == pytest.approx(3.2)
    assert tulsa.opis_truckstop_id == 2
