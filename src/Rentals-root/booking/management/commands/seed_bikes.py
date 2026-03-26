from decimal import Decimal

from django.core.management.base import BaseCommand

from booking.factories import ProviderFactoryB
from booking.models import Vehicle

_CITIES = [c[0] for c in Vehicle.CITY_CHOICES]

# Base models — each will be seeded once per year in YEARS, giving 12 models × ~8 years = 96+
_BASE_BIKES = [
    # Standard bikes
    {"make": "Trek",        "model": "FX 3",          "bike_type": "STANDARD", "has_motor": False, "daily_rate": "25.00"},
    {"make": "Trek",        "model": "FX 2",          "bike_type": "STANDARD", "has_motor": False, "daily_rate": "22.00"},
    {"make": "Giant",       "model": "Escape 3",      "bike_type": "STANDARD", "has_motor": False, "daily_rate": "20.00"},
    {"make": "Giant",       "model": "Escape 2",      "bike_type": "STANDARD", "has_motor": False, "daily_rate": "18.00"},
    {"make": "Cannondale",  "model": "Quick 4",       "bike_type": "STANDARD", "has_motor": False, "daily_rate": "28.00"},
    {"make": "Cannondale",  "model": "Quick 3",       "bike_type": "STANDARD", "has_motor": False, "daily_rate": "26.00"},
    {"make": "Specialized", "model": "Sirrus 2.0",    "bike_type": "STANDARD", "has_motor": False, "daily_rate": "30.00"},
    {"make": "Specialized", "model": "Sirrus 1.0",    "bike_type": "STANDARD", "has_motor": False, "daily_rate": "27.00"},
    {"make": "Norco",       "model": "Search S2",     "bike_type": "STANDARD", "has_motor": False, "daily_rate": "24.00"},
    {"make": "Norco",       "model": "Threshold A1",  "bike_type": "STANDARD", "has_motor": False, "daily_rate": "23.00"},
    {"make": "Kona",        "model": "Dew",           "bike_type": "STANDARD", "has_motor": False, "daily_rate": "21.00"},
    {"make": "Scott",       "model": "Sub Cross 20",  "bike_type": "STANDARD", "has_motor": False, "daily_rate": "22.00"},
    # E-Bikes
    {"make": "Trek",        "model": "Allant+ 7",     "bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "55.00"},
    {"make": "Trek",        "model": "Allant+ 5",     "bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "50.00"},
    {"make": "Giant",       "model": "Explore E+ 2",  "bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "60.00"},
    {"make": "Giant",       "model": "FastRoad E+ 1", "bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "65.00"},
    {"make": "Specialized", "model": "Turbo Como 3.0","bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "62.00"},
    {"make": "Specialized", "model": "Turbo Vado 3.0","bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "68.00"},
    {"make": "Cannondale",  "model": "Tesoro Neo X 3","bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "58.00"},
    {"make": "Rad Power",   "model": "RadCity 5 Plus","bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "52.00"},
    {"make": "Rad Power",   "model": "RadMission 1",  "bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "48.00"},
    {"make": "Gazelle",     "model": "Ultimate C380", "bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "70.00"},
    {"make": "Riese&Müller","model": "Supercharger3", "bike_type": "EBIKE",    "has_motor": True,  "daily_rate": "75.00"},
    {"make": "Cube",        "model": "Kathmandu Hybrid","bike_type": "EBIKE",  "has_motor": True,  "daily_rate": "63.00"},
]

_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]

# Expand: each base model × each year
BIKES = [
    {**b, "year": y}
    for b in _BASE_BIKES
    for y in _YEARS
]


class Command(BaseCommand):
    help = "Seeds the database with bike data (~144 bikes across 6 cities)"

    def handle(self, *args, **kwargs):
        from booking.models import Bike
        factory = ProviderFactoryB()
        created = 0
        for data in BIKES:
            if Bike.objects.filter(make=data["make"], model=data["model"], year=data["year"]).exists():
                continue
            bike = factory.create_bike(
                make=data["make"],
                model=data["model"],
                year=data["year"],
                bike_type=data["bike_type"],
                has_motor=data["has_motor"],
                daily_rate=Decimal(data["daily_rate"]),
                rating=round(3.5 + (created % 5) * 0.3, 1),
                review_count=10 + created * 2,
                total_trips=20 + created * 3,
            )
            bike.city = _CITIES[created % len(_CITIES)]
            bike.save(update_fields=["city"])
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} bikes."))
