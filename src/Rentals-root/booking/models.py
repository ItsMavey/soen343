from django.db import models
from django.conf import settings


class Vehicle(models.Model):
    KIND_CAR = "CAR"
    KIND_BIKE = "BIKE"
    KIND_SCOOTER = "SCOOTER"
    KIND_CHOICES = [
        (KIND_CAR, "Car"),
        (KIND_BIKE, "Bike"),
        (KIND_SCOOTER, "Scooter"),
    ]

    STATUS_AVAILABLE = "AVAILABLE"
    STATUS_RESERVED = "RESERVED"
    STATUS_IN_USE = "IN_USE"
    STATUS_MAINTENANCE = "MAINTENANCE"
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Available"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_IN_USE, "In Use"),
        (STATUS_MAINTENANCE, "Maintenance"),
    ]

    vehicle_kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    vehicle_status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_AVAILABLE)
    provider = models.CharField(max_length=100, blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_vehicles",
    )

    make = models.CharField(max_length=50)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()

    daily_rate = models.DecimalField(max_digits=8, decimal_places=2)
    rating = models.FloatField(default=0.0)
    review_count = models.PositiveIntegerField(default=0)
    total_trips = models.PositiveIntegerField(default=0)

    @property
    def is_available(self):
        return self.vehicle_status == self.STATUS_AVAILABLE

    def get_subtype(self):
        for attr in ("car", "bike", "scooter"):
            try:
                return getattr(self, attr)
            except Exception:
                pass
        return self

    def reserve(self):
        self.vehicle_status = self.STATUS_RESERVED
        self.save(update_fields=["vehicle_status"])

    def confirm(self):
        self.vehicle_status = self.STATUS_IN_USE
        self.save(update_fields=["vehicle_status"])

    def return_vehicle(self):
        self.vehicle_status = self.STATUS_AVAILABLE
        self.total_trips += 1
        self.save(update_fields=["vehicle_status", "total_trips"])

    def send_to_maintenance(self):
        self.vehicle_status = self.STATUS_MAINTENANCE
        self.save(update_fields=["vehicle_status"])

    def display_name(self):
        return f"{self.year} {self.make} {self.model}"

    def __str__(self):
        return f"{self.display_name()} - ${self.daily_rate}/day"

    class Meta:
        indexes = [
            models.Index(fields=["make", "model"]),
            models.Index(fields=["daily_rate"]),
            models.Index(fields=["vehicle_kind"]),
        ]


class Car(Vehicle):
    FUEL_CHOICES = [
        ("GASOLINE", "Gasoline"),
        ("ELECTRIC", "Electric"),
        ("HYBRID", "Hybrid"),
        ("DIESEL", "Diesel"),
    ]

    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES)
    body_style = models.CharField(max_length=50, blank=True, default="")  # e.g. SUV, Sedan

    def save(self, *args, **kwargs):
        self.vehicle_kind = Vehicle.KIND_CAR
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Car"


class Bike(Vehicle):
    BIKE_TYPE_CHOICES = [
        ("STANDARD", "Standard"),
        ("EBIKE", "E-Bike"),
    ]

    bike_type = models.CharField(max_length=10, choices=BIKE_TYPE_CHOICES, default="STANDARD")
    has_motor = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.vehicle_kind = Vehicle.KIND_BIKE
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Bike"


class Scooter(Vehicle):
    engine_cc = models.PositiveIntegerField(default=50)
    is_electric = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.vehicle_kind = Vehicle.KIND_SCOOTER
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Scooter"


class Reservation(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_RETURNED = "RETURNED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending Payment"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_RETURNED, "Returned"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    PRICING_STANDARD = "STANDARD"
    PRICING_WEEKEND = "WEEKEND"
    PRICING_SURGE = "SURGE"
    PRICING_CHOICES = [
        (PRICING_STANDARD, "Standard Rate"),
        (PRICING_WEEKEND, "Weekend Rate"),
        (PRICING_SURGE, "Surge Pricing"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    pricing_strategy = models.CharField(max_length=10, choices=PRICING_CHOICES, default=PRICING_STANDARD)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["vehicle", "start_date", "end_date"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"Reservation #{self.id} - {self.user} - {self.vehicle}"
