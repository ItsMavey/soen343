from decimal import Decimal

from django.core.management.base import BaseCommand

from booking.factories import ProviderFactoryB
from booking.models import Vehicle

_CITIES = [c[0] for c in Vehicle.CITY_CHOICES]

SCOOTERS = [
    {"make": "Vespa", "model": "Primavera 50", "year": 2023, "engine_cc": 50, "is_electric": False, "daily_rate": "35.00"},
    {"make": "Vespa", "model": "GTS 300", "year": 2023, "engine_cc": 300, "is_electric": False, "daily_rate": "55.00"},
    {"make": "Honda", "model": "Metropolitan", "year": 2023, "engine_cc": 49, "is_electric": False, "daily_rate": "30.00"},
    {"make": "Honda", "model": "PCX 150", "year": 2022, "engine_cc": 150, "is_electric": False, "daily_rate": "45.00"},
    {"make": "Yamaha", "model": "Zuma 125", "year": 2023, "engine_cc": 125, "is_electric": False, "daily_rate": "40.00"},
    {"make": "Yamaha", "model": "SMAX", "year": 2022, "engine_cc": 155, "is_electric": False, "daily_rate": "48.00"},
    {"make": "NIU", "model": "NQi GT", "year": 2023, "engine_cc": 0, "is_electric": True, "daily_rate": "42.00"},
    {"make": "NIU", "model": "MQi+ Sport", "year": 2023, "engine_cc": 0, "is_electric": True, "daily_rate": "38.00"},
    {"make": "Segway", "model": "E110SE", "year": 2023, "engine_cc": 0, "is_electric": True, "daily_rate": "35.00"},
    {"make": "Gogoro", "model": "VIVA MIX", "year": 2023, "engine_cc": 0, "is_electric": True, "daily_rate": "40.00"},
]


class Command(BaseCommand):
    help = "Seeds the database with scooter data"

    def handle(self, *args, **kwargs):
        from booking.models import Scooter
        factory = ProviderFactoryB()
        created = 0
        for data in SCOOTERS:
            if Scooter.objects.filter(make=data["make"], model=data["model"], year=data["year"]).exists():
                continue
            scooter = factory.create_scooter(
                make=data["make"],
                model=data["model"],
                year=data["year"],
                engine_cc=data["engine_cc"],
                is_electric=data["is_electric"],
                daily_rate=Decimal(data["daily_rate"]),
                rating=round(3.5 + (created % 4) * 0.4, 1),
                review_count=created * 2,
                total_trips=created * 4,
            )
            scooter.city = _CITIES[created % len(_CITIES)]
            scooter.save(update_fields=["city"])
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} scooters."))
