import csv
from decimal import Decimal
from django.core.management.base import BaseCommand

from booking.models import Car



class Command(BaseCommand):
    help = 'Seeds the database with car data from a CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the cars CSV file')

    def handle(self, *args, **kwargs):
        path = kwargs['csv_file']

        with open(path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Helper function to handle empty strings for numbers
                def safe_float(val, default=0.0):
                    return float(val) if val and val.strip() else default

                def safe_int(val, default=0):
                    return int(val) if val and val.strip() else default

                Car.objects.get_or_create(
                    make=row.get('vehicle.make'),  # Updated to match your CSV screenshot
                    model=row.get('vehicle.model'),
                    year=safe_int(row.get('vehicle.year')),
                    defaults={
                        'fuel_type': row.get('fuelType', 'GASOLINE'),
                        'vehicle_type': row.get('vehicle.type', 'Sedan'),
                        'daily_rate': Decimal(row.get('daily_rate', '0.00') or '0.00'),
                        'is_available': row.get('is_available', 'True') == 'True',
                        'rating': safe_float(row.get('rating')),
                        'review_count': safe_int(row.get('reviewCount')),
                        'total_trips': safe_int(row.get('renterTripsTaken')),
                    }
                )

        self.stdout.write(self.style.SUCCESS('Successfully seeded car data!'))