"""
One-shot seeder: runs seed_bikes, seed_scooters, then seed_demo.
Does NOT seed cars from CSV (requires the dataset file).

Usage:
    python manage.py seed_all
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run all seed commands in order: bikes → scooters → demo"

    def handle(self, *args, **kwargs):
        self.stdout.write("── Seeding cars ──")
        call_command("seed_cars_local")
        self.stdout.write("── Seeding bikes ──")
        call_command("seed_bikes")
        self.stdout.write("── Seeding scooters ──")
        call_command("seed_scooters")
        self.stdout.write("── Seeding demo data ──")
        call_command("seed_demo")
        self.stdout.write(self.style.SUCCESS("\nAll done. Run the server and log in as qwer2 / qwerqwer!"))
