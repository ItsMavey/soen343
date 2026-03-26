from decimal import Decimal

from django.core.management.base import BaseCommand

from booking.factories import ProviderFactoryB
from booking.models import Vehicle

_CITIES = [c[0] for c in Vehicle.CITY_CHOICES]

_BASE_SCOOTERS = [
    # Gas scooters
    {"make": "Vespa",   "model": "Primavera 50",   "engine_cc": 50,  "is_electric": False, "daily_rate": "35.00"},
    {"make": "Vespa",   "model": "GTS 300",         "engine_cc": 300, "is_electric": False, "daily_rate": "55.00"},
    {"make": "Vespa",   "model": "Sprint 150",      "engine_cc": 150, "is_electric": False, "daily_rate": "45.00"},
    {"make": "Honda",   "model": "Metropolitan",    "engine_cc": 49,  "is_electric": False, "daily_rate": "30.00"},
    {"make": "Honda",   "model": "PCX 150",         "engine_cc": 150, "is_electric": False, "daily_rate": "45.00"},
    {"make": "Honda",   "model": "Ruckus",          "engine_cc": 49,  "is_electric": False, "daily_rate": "28.00"},
    {"make": "Yamaha",  "model": "Zuma 125",        "engine_cc": 125, "is_electric": False, "daily_rate": "40.00"},
    {"make": "Yamaha",  "model": "SMAX",            "engine_cc": 155, "is_electric": False, "daily_rate": "48.00"},
    {"make": "Yamaha",  "model": "Vino 125",        "engine_cc": 125, "is_electric": False, "daily_rate": "38.00"},
    {"make": "Kymco",   "model": "Like 150i",       "engine_cc": 150, "is_electric": False, "daily_rate": "36.00"},
    {"make": "Kymco",   "model": "Downtown 350i",   "engine_cc": 350, "is_electric": False, "daily_rate": "52.00"},
    {"make": "Piaggio", "model": "Liberty 150",     "engine_cc": 150, "is_electric": False, "daily_rate": "40.00"},
    {"make": "Piaggio", "model": "MP3 300",         "engine_cc": 300, "is_electric": False, "daily_rate": "58.00"},
    # Electric scooters
    {"make": "NIU",     "model": "NQi GT",          "engine_cc": 0,   "is_electric": True,  "daily_rate": "42.00"},
    {"make": "NIU",     "model": "MQi+ Sport",      "engine_cc": 0,   "is_electric": True,  "daily_rate": "38.00"},
    {"make": "NIU",     "model": "UQi Pro",         "engine_cc": 0,   "is_electric": True,  "daily_rate": "35.00"},
    {"make": "Segway",  "model": "E110SE",          "engine_cc": 0,   "is_electric": True,  "daily_rate": "35.00"},
    {"make": "Segway",  "model": "E300SE",          "engine_cc": 0,   "is_electric": True,  "daily_rate": "45.00"},
    {"make": "Gogoro",  "model": "VIVA MIX",        "engine_cc": 0,   "is_electric": True,  "daily_rate": "40.00"},
    {"make": "Gogoro",  "model": "SuperSport",      "engine_cc": 0,   "is_electric": True,  "daily_rate": "48.00"},
    {"make": "Vmoto",   "model": "Super Soco TC",   "engine_cc": 0,   "is_electric": True,  "daily_rate": "43.00"},
    {"make": "Vmoto",   "model": "Super Soco CPx",  "engine_cc": 0,   "is_electric": True,  "daily_rate": "50.00"},
    {"make": "Silence", "model": "S01",             "engine_cc": 0,   "is_electric": True,  "daily_rate": "46.00"},
    {"make": "Niu",     "model": "RQi",             "engine_cc": 0,   "is_electric": True,  "daily_rate": "55.00"},
]

_YEARS = [2020, 2021, 2022, 2023, 2024]

SCOOTERS = [
    {**s, "year": y}
    for s in _BASE_SCOOTERS
    for y in _YEARS
]


class Command(BaseCommand):
    help = "Seeds the database with scooter data (~120 scooters across 6 cities)"

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
                rating=round(3.5 + (created % 5) * 0.3, 1),
                review_count=10 + created * 2,
                total_trips=15 + created * 3,
            )
            scooter.city = _CITIES[created % len(_CITIES)]
            scooter.save(update_fields=["city"])
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} scooters."))
