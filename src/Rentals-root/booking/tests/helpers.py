import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from booking.models import Vehicle, Car, Reservation

User = get_user_model()


def make_user(username="testuser", role="COMMUTER"):
    return User.objects.create_user(
        username=username, password="pass", email=f"{username}@test.com", role=role
    )


def make_car(make="Toyota", model="Corolla", year=2022, daily_rate="50.00", fuel_type="GASOLINE"):
    return Car.objects.create(
        make=make, model=model, year=year,
        daily_rate=Decimal(daily_rate),
        fuel_type=fuel_type,
        vehicle_kind=Vehicle.KIND_CAR,
    )


def make_reservation(user, vehicle, start_offset=1, days=3, status=Reservation.STATUS_CONFIRMED):
    today = timezone.localdate()
    start = today + datetime.timedelta(days=start_offset)
    end = start + datetime.timedelta(days=days - 1)
    return Reservation.objects.create(
        user=user, vehicle=vehicle,
        start_date=start, end_date=end,
        total_amount=vehicle.daily_rate * days,
        status=status,
    )


def _dates(days):
    """Return (start, end) date pair spanning `days` days starting 2024-01-01."""
    start = datetime.date(2024, 1, 1)
    end = start + datetime.timedelta(days=days - 1)
    return start, end
