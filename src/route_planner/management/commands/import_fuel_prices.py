from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from route_planner.models import FuelStation


class Command(BaseCommand):
    help = "Import and normalize fuel prices from the CSV using Polars."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--csv-path",
            type=str,
            default=str(settings.PROJECT_ROOT / "fuel-prices-for-be-assessment.csv"),
            help="Path to the source fuel prices CSV",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing stations before importing",
        )

    def handle(self, *_: Any, **options: Any) -> None:
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"CSV file does not exist: {csv_path}")

        frame = self._load_and_transform(csv_path)
        records = frame.to_dicts()

        if options["replace"]:
            FuelStation.objects.all().delete()

        existing = {
            station.canonical_key: station
            for station in FuelStation.objects.filter(
                canonical_key__in=[row["canonical_key"] for row in records]
            )
        }

        to_create: list[FuelStation] = []
        to_update: list[FuelStation] = []

        for row in records:
            station = existing.get(row["canonical_key"])
            if station is None:
                to_create.append(
                    FuelStation(
                        opis_truckstop_id=row["opis_truckstop_id"],
                        truckstop_name=row["truckstop_name"],
                        address=row["address"],
                        city=row["city"],
                        state=row["state"],
                        rack_id=row["rack_id"],
                        retail_price=row["retail_price"],
                        canonical_key=row["canonical_key"],
                    )
                )
                continue

            station.opis_truckstop_id = row["opis_truckstop_id"]
            station.truckstop_name = row["truckstop_name"]
            station.address = row["address"]
            station.city = row["city"]
            station.state = row["state"]
            station.rack_id = row["rack_id"]
            station.retail_price = row["retail_price"]
            to_update.append(station)

        if to_create:
            FuelStation.objects.bulk_create(to_create, batch_size=1000)
        if to_update:
            FuelStation.objects.bulk_update(
                to_update,
                [
                    "opis_truckstop_id",
                    "truckstop_name",
                    "address",
                    "city",
                    "state",
                    "rack_id",
                    "retail_price",
                ],
                batch_size=1000,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Imported fuel stations: "
                + (
                    f"{len(records)} rows normalized, "
                    f"{len(to_create)} created, {len(to_update)} updated"
                )
            )
        )

    @staticmethod
    def _load_and_transform(csv_path: Path) -> pl.DataFrame:
        frame = pl.read_csv(csv_path, infer_schema_length=5000)
        required_columns = {
            "OPIS Truckstop ID",
            "Truckstop Name",
            "Address",
            "City",
            "State",
            "Rack ID",
            "Retail Price",
        }
        missing_columns = required_columns.difference(frame.columns)
        if missing_columns:
            raise CommandError(f"Missing expected columns: {sorted(missing_columns)}")

        normalized = (
            frame.select(
                pl.col("OPIS Truckstop ID").cast(pl.Int64, strict=False).alias("opis_truckstop_id"),
                pl.col("Truckstop Name")
                .cast(pl.Utf8, strict=False)
                .str.strip_chars()
                .fill_null("")
                .alias("truckstop_name"),
                pl.col("Address")
                .cast(pl.Utf8, strict=False)
                .str.strip_chars()
                .fill_null("")
                .alias("address"),
                pl.col("City")
                .cast(pl.Utf8, strict=False)
                .str.strip_chars()
                .fill_null("")
                .alias("city"),
                pl.col("State")
                .cast(pl.Utf8, strict=False)
                .str.strip_chars()
                .str.to_uppercase()
                .str.slice(0, 2)
                .fill_null("")
                .alias("state"),
                pl.col("Rack ID").cast(pl.Int64, strict=False).alias("rack_id"),
                pl.col("Retail Price").cast(pl.Float64, strict=False).alias("retail_price"),
            )
            .filter(
                pl.col("opis_truckstop_id").is_not_null()
                & pl.col("retail_price").is_not_null()
                & (pl.col("retail_price") > 0)
                & (pl.col("address").str.len_chars() > 0)
                & (pl.col("city").str.len_chars() > 0)
                & (pl.col("state").str.len_chars() == 2)
            )
            .with_columns(
                pl.concat_str(
                    [
                        pl.col("address").str.to_uppercase(),
                        pl.col("city").str.to_uppercase(),
                        pl.col("state"),
                    ],
                    separator="|",
                ).alias("canonical_key")
            )
            .sort(["canonical_key", "retail_price"])
            .unique(subset=["canonical_key"], keep="first", maintain_order=True)
        )

        return normalized
