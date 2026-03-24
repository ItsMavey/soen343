from decimal import Decimal

from django.core.management.base import BaseCommand

from booking.factories import ProviderFactoryB

BIKES = [
    {"make": "Trek", "model": "FX 3", "year": 2023, "bike_type": "STANDARD", "has_motor": False, "daily_rate": "25.00"},
    {"make": "Trek", "model": "FX 3", "year": 2022, "bike_type": "STANDARD", "has_motor": False, "daily_rate": "22.00"},
    {"make": "Giant", "model": "Escape 3", "year": 2023, "bike_type": "STANDARD", "has_motor": False, "daily_rate": "20.00"},
    {"make": "Giant", "model": "Escape 3", "year": 2022, "bike_type": "STANDARD", "has_motor": False, "daily_rate": "18.00"},
    {"make": "Cannondale", "model": "Quick 4", "year": 2023, "bike_type": "STANDARD", "has_motor": False, "daily_rate": "28.00"},
    {"make": "Specialized", "model": "Sirrus 2.0", "year": 2023, "bike_type": "STANDARD", "has_motor": False, "daily_rate": "30.00"},
    {"make": "Trek", "model": "Allant+ 7", "year": 2023, "bike_type": "EBIKE", "has_motor": True, "daily_rate": "55.00"},
    {"make": "Trek", "model": "Allant+ 7", "year": 2022, "bike_type": "EBIKE", "has_motor": True, "daily_rate": "50.00"},
    {"make": "Giant", "model": "Explore E+ 2", "year": 2023, "bike_type": "EBIKE", "has_motor": True, "daily_rate": "60.00"},
    {"make": "Specialized", "model": "Turbo Como 3.0", "year": 2023, "bike_type": "EBIKE", "has_motor": True, "daily_rate": "65.00"},
    {"make": "Cannondale", "model": "Tesoro Neo X 3", "year": 2022, "bike_type": "EBIKE", "has_motor": True, "daily_rate": "58.00"},
    {"make": "Rad Power", "model": "RadCity 5 Plus", "year": 2023, "bike_type": "EBIKE", "has_motor": True, "daily_rate": "52.00"},
]


class Command(BaseCommand):
    help = "Seeds the database with bike data"

    def handle(self, *args, **kwargs):
        from booking.models import Bike
        factory = ProviderFactoryB()
        created = 0
        for data in BIKES:
            if Bike.objects.filter(make=data["make"], model=data["model"], year=data["year"]).exists():
                continue
            factory.create_bike(
                make=data["make"],
                model=data["model"],
                year=data["year"],
                bike_type=data["bike_type"],
                has_motor=data["has_motor"],
                daily_rate=Decimal(data["daily_rate"]),
                rating=round(3.5 + (created % 4) * 0.4, 1),
                review_count=created * 3,
                total_trips=created * 5,
            )
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} bikes."))
