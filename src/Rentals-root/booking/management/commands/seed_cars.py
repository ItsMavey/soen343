import csv
from decimal import Decimal

from django.core.management.base import BaseCommand

from booking.factories import ProviderFactoryA
from booking.models import Car


class Command(BaseCommand):
    help = "Seeds the database with car data from a CSV"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the cars CSV file")

    def handle(self, *args, **kwargs):
        path = kwargs["csv_file"]
        factory = ProviderFactoryA()

        def safe_float(val, default=0.0):
            try:
                return float(val) if val and str(val).strip() else default
            except (ValueError, TypeError):
                return default

        def safe_int(val, default=0):
            try:
                return int(float(val)) if val and str(val).strip() else default
            except (ValueError, TypeError):
                return default

        created = 0
        with open(path, "r", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                make = row.get("vehicle.make")
                model = row.get("vehicle.model")
                year = safe_int(row.get("vehicle.year"))

                if Car.objects.filter(make=make, model=model, year=year).exists():
                    continue

                factory.create_car(
                    make=make,
                    model=model,
                    year=year,
                    fuel_type=row.get("fuelType", "GASOLINE").upper(),
                    body_style=row.get("vehicle.type", "Sedan"),
                    daily_rate=Decimal(str(row.get("rate.daily") or "0")),
                    rating=safe_float(row.get("rating")),
                    review_count=safe_int(row.get("reviewCount")),
                    total_trips=safe_int(row.get("renterTripsTaken")),
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} cars."))
