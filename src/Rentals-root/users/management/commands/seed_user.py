import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

User = get_user_model()

_HASHED_PW = None  # computed once


def _get_hashed_pw():
    global _HASHED_PW
    if _HASHED_PW is None:
        _HASHED_PW = make_password("TemporaryPass123!")
    return _HASHED_PW


class Command(BaseCommand):
    help = "Seeds the database with user data from the Synthetic Person Records CSV"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the synthetic person CSV file")
        parser.add_argument(
            "--limit", type=int, default=0,
            help="Maximum number of users to create (0 = all)",
        )

    def handle(self, *args, **kwargs):
        path = kwargs["csv_file"]
        limit = kwargs["limit"]

        existing_emails = set(User.objects.values_list("email", flat=True))
        existing_usernames = set(User.objects.values_list("username", flat=True))

        to_create = []
        count = 0

        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if limit and count >= limit:
                    break

                email = row.get("email", "").strip().lower()
                username = f"{row['firstname'].lower()}.{row['lastname'].lower()}.{row.get('person_id', '0')}"

                if email in existing_emails or username in existing_usernames:
                    continue

                existing_emails.add(email)
                existing_usernames.add(username)

                to_create.append(User(
                    username=username,
                    first_name=row.get("firstname", ""),
                    last_name=row.get("lastname", ""),
                    email=email,
                    password=_get_hashed_pw(),
                    is_active=True,
                    role=User.ROLE_COMMUTER,
                ))
                count += 1

        # Batch insert in chunks of 500
        chunk = 500
        created = 0
        for i in range(0, len(to_create), chunk):
            batch = User.objects.bulk_create(to_create[i:i + chunk], ignore_conflicts=True)
            created += len(batch)

        self.stdout.write(self.style.SUCCESS(f"Created {created} users from {path}"))
