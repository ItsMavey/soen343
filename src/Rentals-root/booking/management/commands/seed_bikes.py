"""Seed exactly 10 bikes per city (60 total)."""
from decimal import Decimal

from django.core.management.base import BaseCommand

from booking.factories import ProviderFactoryB
from booking.models import Vehicle

_CITIES = [c[0] for c in Vehicle.CITY_CHOICES]

# Exactly 10 models — each created in every city
_BIKES = [
    {"make": "Trek",        "model": "FX 3 Disc",      "year": 2023, "bike_type": "STANDARD", "has_motor": False, "daily_rate": "25.00"},
    {"make": "Giant",       "model": "Escape 3",        "year": 2023, "bike_type": "STANDARD", "has_motor": False, "daily_rate": "20.00"},
    {"make": "Cannondale",  "model": "Quick 3",         "year": 2023, "bike_type": "STANDARD", "has_motor": False, "daily_rate": "26.00"},
    {"make": "Specialized", "model": "Sirrus 2.0",      "year": 2022, "bike_type": "STANDARD", "has_motor": False, "daily_rate": "30.00"},
    {"make": "Norco",       "model": "Search S2",       "year": 2022, "bike_type": "STANDARD", "has_motor": False, "daily_rate": "24.00"},
    {"make": "Trek",        "model": "Allant+ 7",       "year": 2023, "bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "55.00"},
    {"make": "Giant",       "model": "FastRoad E+ 1",   "year": 2023, "bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "60.00"},
    {"make": "Specialized", "model": "Turbo Vado 3.0",  "year": 2022, "bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "68.00"},
    {"make": "Rad Power",   "model": "RadCity 5 Plus",  "year": 2023, "bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "52.00"},
    {"make": "Gazelle",     "model": "Ultimate C380",   "year": 2022, "bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "70.00"},
]


class Command(BaseCommand):
    help = "Seed 10 bikes per city (60 total)"

    def handle(self, *args, **kwargs):
        from booking.models import Bike
        factory = ProviderFactoryB()
        created = 0
        for city in _CITIES:
            for i, data in enumerate(_BIKES):
                if Bike.objects.filter(make=data["make"], model=data["model"],
                                       year=data["year"], city=city).exists():
                    continue
                bike = factory.create_bike(
                    make=data["make"],
                    model=data["model"],
                    year=data["year"],
                    bike_type=data["bike_type"],
                    has_motor=data["has_motor"],
                    daily_rate=Decimal(data["daily_rate"]),
                    rating=round(3.5 + (i % 5) * 0.3, 1),
                    review_count=10 + i * 2,
                    total_trips=20 + i * 3,
                )
                bike.city = city
                bike.save(update_fields=["city"])
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} bikes ({created // max(len(_CITIES), 1)} per city)."))
