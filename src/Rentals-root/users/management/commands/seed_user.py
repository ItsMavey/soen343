import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from address.models import Address
from phonenumber_field.phonenumber import PhoneNumber

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds the database with user data from the Synthetic Person Records CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the synthetic person CSV file')

    def handle(self, *args, **kwargs):
        path = kwargs['csv_file']

        with open(path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # 1. Construct the raw address string from CSV columns
                # Columns in dataset: streetnumber, street, city, postalcode
                raw_address_str = f"{row['streetnumber']} {row['street']}, {row['city']}, {row['postalcode']}, Canada"

                # 2. Handle AddressField (django-address)
                # This creates or retrieves the Address object required by AddressField
                address_obj = Address.objects.get_or_create(raw=raw_address_str)[0]

                # 3. Clean Phone Number
                # PhoneNumberField(region="CA") expects valid formats
                raw_phone = row.get('phone', '')
                try:
                    # We force it to a CA-parsable format if not already E.164
                    phone_obj = PhoneNumber.from_string(raw_phone, region="CA")
                except Exception:
                    phone_obj = None

                # 4. Create the User
                # Using get_or_create on username to avoid duplicates
                username = f"{row['firstname'].lower()}.{row['lastname'].lower()}.{row.get('person_id', '0')}"

                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'first_name': row.get('firstname'),
                        'last_name': row.get('lastname'),
                        'email': row.get('email'),
                        'phone_number': phone_obj,
                        'address': address_obj,
                        'is_active': True,
                    }
                )

                if created:
                    user.set_password('TemporaryPass123!')  # Required for AbstractUser
                    user.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded users from {path}!'))