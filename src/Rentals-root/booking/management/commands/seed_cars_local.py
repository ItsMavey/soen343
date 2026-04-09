"""
Seed exactly 10 cars per city (6 cities = 60 cars total).
Usage: python manage.py seed_cars_local
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from booking.factories import ProviderFactoryA
from booking.models import Vehicle

_CITIES = [c[0] for c in Vehicle.CITY_CHOICES]

# Exactly 10 models — each created in every city
_CARS = [
    {"make": "Toyota",     "model": "Corolla",       "year": 2023, "fuel_type": "GASOLINE", "daily_rate": "55.00"},
    {"make": "Toyota",     "model": "RAV4 Hybrid",   "year": 2023, "fuel_type": "HYBRID",   "daily_rate": "85.00"},
    {"make": "Honda",      "model": "Civic",          "year": 2023, "fuel_type": "GASOLINE", "daily_rate": "58.00"},
    {"make": "Honda",      "model": "CR-V Hybrid",   "year": 2022, "fuel_type": "HYBRID",   "daily_rate": "78.00"},
    {"make": "Tesla",      "model": "Model 3",        "year": 2023, "fuel_type": "ELECTRIC", "daily_rate": "95.00"},
    {"make": "Tesla",      "model": "Model Y",        "year": 2023, "fuel_type": "ELECTRIC", "daily_rate": "105.00"},
    {"make": "Hyundai",    "model": "Ioniq 5",        "year": 2022, "fuel_type": "ELECTRIC", "daily_rate": "90.00"},
    {"make": "Kia",        "model": "EV6",            "year": 2023, "fuel_type": "ELECTRIC", "daily_rate": "88.00"},
    {"make": "Mazda",      "model": "CX-5",           "year": 2022, "fuel_type": "GASOLINE", "daily_rate": "68.00"},
    {"make": "Volkswagen", "model": "ID.4",           "year": 2023, "fuel_type": "ELECTRIC", "daily_rate": "85.00"},
]


class Command(BaseCommand):
    help = "Seed 10 cars per city (60 total)"

    def handle(self, *args, **kwargs):
        from booking.models import Car
        factory = ProviderFactoryA()
        created = 0
        for city in _CITIES:
            for i, data in enumerate(_CARS):
                if Car.objects.filter(make=data["make"], model=data["model"],
                                      year=data["year"], city=city).exists():
                    continue
                car = factory.create_car(
                    make=data["make"],
                    model=data["model"],
                    year=data["year"],
                    fuel_type=data["fuel_type"],
                    daily_rate=Decimal(data["daily_rate"]),
                    rating=round(3.5 + (i % 5) * 0.3, 1),
                    review_count=5 + i * 3,
                    total_trips=10 + i * 4,
                )
                car.city = city
                car.save(update_fields=["city"])
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} cars ({created // max(len(_CITIES), 1)} per city)."))
