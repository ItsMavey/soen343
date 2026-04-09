"""
Demo data seeder.

Run:  python manage.py seed_demo

Requires qwer / qwer1 / qwer2 to already exist (created manually).
Idempotent — safe to re-run; won't duplicate vehicles or reservations.
"""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from booking.models import Vehicle, Car, Bike, Scooter, Reservation, Notification

User = get_user_model()

today = datetime.date.today()


def _days(n):
    return today + datetime.timedelta(days=n)


def _car(owner, make, model, year, daily_rate, fuel_type, city, status=Vehicle.STATUS_AVAILABLE):
    obj, created = Car.objects.get_or_create(
        make=make, model=model, year=year, owner=owner,
        defaults=dict(
            daily_rate=Decimal(str(daily_rate)),
            fuel_type=fuel_type,
            city=city,
            vehicle_kind=Vehicle.KIND_CAR,
            vehicle_status=status,
            provider="TABAC Provider",
        ),
    )
    return obj


def _bike(owner, make, model, year, daily_rate, bike_type, city):
    obj, created = Bike.objects.get_or_create(
        make=make, model=model, year=year, owner=owner,
        defaults=dict(
            daily_rate=Decimal(str(daily_rate)),
            bike_type=bike_type,
            city=city,
            vehicle_kind=Vehicle.KIND_BIKE,
            provider="TABAC Provider",
            has_motor=(bike_type == "EBIKE"),
        ),
    )
    return obj


def _scooter(owner, make, model, year, daily_rate, city):
    obj, created = Scooter.objects.get_or_create(
        make=make, model=model, year=year, owner=owner,
        defaults=dict(
            daily_rate=Decimal(str(daily_rate)),
            city=city,
            vehicle_kind=Vehicle.KIND_SCOOTER,
            provider="TABAC Provider",
            is_electric=True,
        ),
    )
    return obj


def _reservation(user, vehicle, start, end, status, pricing="STANDARD",
                 paid=True, returned_at=None):
    days = (end - start).days + 1
    amount = vehicle.daily_rate * days
    if Reservation.objects.filter(user=user, vehicle=vehicle, start_date=start, end_date=end).exists():
        return Reservation.objects.get(user=user, vehicle=vehicle, start_date=start, end_date=end)

    r = Reservation.objects.create(
        user=user,
        vehicle=vehicle,
        start_date=start,
        end_date=end,
        total_amount=amount,
        status=status,
        pricing_strategy=pricing,
        paid_at=timezone.now() if paid and status != Reservation.STATUS_PENDING else None,
        returned_at=returned_at,
    )
    if status == Reservation.STATUS_RETURNED:
        vehicle.total_trips = vehicle.total_trips + 1
        vehicle.save(update_fields=["total_trips"])
    return r


class Command(BaseCommand):
    help = "Seed demo reservations and vehicles for qwer / qwer1 / qwer2"

    def handle(self, *args, **kwargs):
        # ── Users ──────────────────────────────────────────────────────────
        admin, _ = User.objects.get_or_create(
            username="qwer",
            defaults=dict(email="admin@demo.com", first_name="Admin", last_name="User"),
        )
        admin.set_password("qwerqwer!")
        admin.role = User.ROLE_ADMIN
        admin.save()

        provider, _ = User.objects.get_or_create(
            username="qwer1",
            defaults=dict(email="provider@demo.com", first_name="Provider", last_name="User"),
        )
        provider.set_password("qwerqwer!")
        provider.role = User.ROLE_PROVIDER
        provider.save()

        commuter, _ = User.objects.get_or_create(
            username="qwer2",
            defaults=dict(email="commuter@demo.com", first_name="Commuter", last_name="User"),
        )
        commuter.set_password("qwerqwer!")
        commuter.role = User.ROLE_COMMUTER
        commuter.preferred_city = "MTL"
        commuter.preferred_mobility_type = "CAR"
        commuter.save()

        self.stdout.write("  OK Roles set on qwer / qwer1 / qwer2")

        # ── Extra commuters (richer analytics) ────────────────────────────
        alice, _ = User.objects.get_or_create(
            username="demo_alice",
            defaults=dict(email="alice@demo.com", role=User.ROLE_COMMUTER,
                          first_name="Alice", last_name="Tremblay",
                          preferred_city="MTL"),
        )
        alice.set_password("demopass1!")
        alice.save()

        bob, _ = User.objects.get_or_create(
            username="demo_bob",
            defaults=dict(email="bob@demo.com", role=User.ROLE_COMMUTER,
                          first_name="Bob", last_name="Gagnon",
                          preferred_city="LAV"),
        )
        bob.set_password("demopass1!")
        bob.save()

        self.stdout.write("  OK Extra commuters: demo_alice, demo_bob")

        # ── Vehicles (owned by provider qwer1) ────────────────────────────
        # MTL
        tesla   = _car(provider, "Tesla",      "Model 3",        2023, 95,  "ELECTRIC", "MTL")
        corolla = _car(provider, "Toyota",     "Corolla",         2022, 55,  "GASOLINE", "MTL")
        civic   = _car(provider, "Honda",      "Civic",           2021, 60,  "HYBRID",   "MTL",
                       status=Vehicle.STATUS_RESERVED)
        bmw     = _car(provider, "BMW",        "M3",              2023, 150, "GASOLINE", "MTL",
                       status=Vehicle.STATUS_MAINTENANCE)
        trek    = _bike(provider, "Trek",      "FX 3 Disc",       2023, 35,  "STANDARD", "MTL")
        giant   = _bike(provider, "Giant",     "FastRoad E+1 Pro",2023, 48,  "EBIKE",    "MTL")
        seg     = _scooter(provider, "Segway", "Ninebot Max G2",  2023, 30,  "MTL")
        _bike(provider,    "Specialized", "Sirrus 2.0",           2022, 30,  "STANDARD", "MTL")
        _scooter(provider, "NIU",         "NQi GT",               2022, 42,  "MTL")

        # LAV
        ioniq   = _car(provider, "Hyundai",   "Ioniq 5",          2022, 85,  "ELECTRIC", "LAV")
        _car(provider,     "Toyota",    "RAV4",                    2021, 70,  "HYBRID",   "LAV")
        _bike(provider,    "Trek",      "Allant+ 7",               2023, 55,  "EBIKE",    "LAV")
        _scooter(provider, "Vespa",     "GTS 300",                 2021, 55,  "LAV")

        # LON
        _car(provider,     "Kia",       "EV6",                     2023, 80,  "ELECTRIC", "LON")
        _car(provider,     "Honda",     "CR-V",                    2022, 65,  "GASOLINE", "LON")
        _bike(provider,    "Giant",     "Escape 3",                2022, 20,  "STANDARD", "LON")
        _scooter(provider, "Honda",     "PCX 150",                 2022, 45,  "LON")

        # QC
        mazda   = _car(provider, "Mazda",     "CX-5",              2021, 65,  "GASOLINE", "QC")
        _car(provider,     "Volkswagen", "ID.4",                    2023, 90,  "ELECTRIC", "QC")
        _bike(provider,    "Cannondale", "Quick 3",                 2022, 26,  "STANDARD", "QC")
        _scooter(provider, "Yamaha",     "Zuma 125",                2021, 40,  "QC")

        # GAT
        _car(provider,     "Ford",      "Escape Hybrid",           2022, 72,  "HYBRID",   "GAT")
        _car(provider,     "Chevrolet", "Bolt EV",                 2023, 78,  "ELECTRIC", "GAT")
        _bike(provider,    "Norco",     "Search S2",               2022, 24,  "STANDARD", "GAT")
        _scooter(provider, "NIU",       "MQi+ Sport",              2022, 38,  "GAT")

        # SHE
        mustang = _car(provider, "Ford",      "Mustang",           2020, 110, "GASOLINE", "SHE")
        _car(provider,     "Subaru",    "Outback",                  2022, 68,  "GASOLINE", "SHE")
        _bike(provider,    "Rad Power", "RadCity 5 Plus",           2023, 52,  "EBIKE",    "SHE")
        _scooter(provider, "Gogoro",    "SuperSport",               2022, 48,  "SHE")

        self.stdout.write("  OK 31 vehicles across all 6 cities created/verified")

        # ── Reservations for qwer2 (commuter) ─────────────────────────────
        # 1. RETURNED — 1 month ago, standard rate
        _reservation(commuter, corolla, _days(-35), _days(-31),
                     Reservation.STATUS_RETURNED,
                     returned_at=timezone.make_aware(
                         datetime.datetime.combine(_days(-31), datetime.time(14, 0))))

        # 2. RETURNED — 2 weeks ago, electric car, surge pricing
        _reservation(commuter, ioniq, _days(-18), _days(-14),
                     Reservation.STATUS_RETURNED,
                     pricing="SURGE",
                     returned_at=timezone.make_aware(
                         datetime.datetime.combine(_days(-14), datetime.time(11, 30))))

        # 3. RETURNED — yesterday (shows in "trips today" area / recent)
        _reservation(commuter, tesla, _days(-3), _days(-1),
                     Reservation.STATUS_RETURNED,
                     returned_at=timezone.make_aware(
                         datetime.datetime.combine(_days(-1), datetime.time(16, 45))))

        # 4. CONFIRMED + OVERDUE — end date was 2 days ago (key edge case)
        _reservation(commuter, civic, _days(-5), _days(-2),
                     Reservation.STATUS_CONFIRMED)

        # 5. CONFIRMED — active upcoming rental
        _reservation(commuter, mazda, _days(2), _days(6),
                     Reservation.STATUS_CONFIRMED)

        # 6. PENDING — not paid yet
        _reservation(commuter, trek, _days(4), _days(6),
                     Reservation.STATUS_PENDING, paid=False)

        # 7. CANCELLED
        _reservation(commuter, bmw, _days(-10), _days(-8),
                     Reservation.STATUS_CANCELLED, paid=False)

        # 8. RETURNED — e-bike rental
        _reservation(commuter, giant, _days(-7), _days(-6),
                     Reservation.STATUS_RETURNED,
                     returned_at=timezone.make_aware(
                         datetime.datetime.combine(_days(-6), datetime.time(18, 0))))

        self.stdout.write("  OK 8 reservations for qwer2 (returned ×4, confirmed ×2 [1 overdue], pending, cancelled)")

        # ── Reservations for demo_alice ────────────────────────────────────
        _reservation(alice, tesla, _days(-22), _days(-19),
                     Reservation.STATUS_RETURNED,
                     returned_at=timezone.make_aware(
                         datetime.datetime.combine(_days(-19), datetime.time(10, 0))))

        _reservation(alice, corolla, _days(1), _days(5),
                     Reservation.STATUS_CONFIRMED)

        _reservation(alice, seg, _days(-3), _days(-2),
                     Reservation.STATUS_RETURNED,
                     returned_at=timezone.make_aware(
                         datetime.datetime.combine(_days(-2), datetime.time(9, 15))))

        # ── Reservations for demo_bob ──────────────────────────────────────
        _reservation(bob, ioniq, _days(-12), _days(-9),
                     Reservation.STATUS_RETURNED,
                     returned_at=timezone.make_aware(
                         datetime.datetime.combine(_days(-9), datetime.time(13, 0))))

        _reservation(bob, mustang, _days(-6), _days(-4),
                     Reservation.STATUS_CANCELLED, paid=False)

        _reservation(bob, trek, _days(3), _days(5),
                     Reservation.STATUS_CONFIRMED)

        self.stdout.write("  OK Reservations for demo_alice and demo_bob")

        # ── Maintenance notification for admin ─────────────────────────────
        if not Notification.objects.filter(user=admin, event_type="MAINTENANCE", vehicle=bmw).exists():
            Notification.objects.create(
                user=admin,
                vehicle=bmw,
                message=f"{bmw.display_name()} was sent to maintenance.",
                event_type="MAINTENANCE",
            )

        self.stdout.write(self.style.SUCCESS(
            "\nDemo data ready!\n"
            "  admin    -> qwer       / qwerqwer!\n"
            "  provider -> qwer1      / qwerqwer!\n"
            "  commuter -> qwer2      / qwerqwer!\n"
            "  extras   -> demo_alice / demopass1!   demo_bob / demopass1!\n"
        ))
