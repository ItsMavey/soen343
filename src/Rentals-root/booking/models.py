from django.db import models
from django.conf import settings


class Car(models.Model):
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()

    FUEL_CHOICES = [('GASOLINE', 'Gasoline'), ('ELECTRIC', 'Electric'), ('HYBRID', 'Hybrid'), ('DIESEL', 'Diesel'), ]

    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES)
    vehicle_type = models.CharField(max_length=50)  # e.g., SUV, Sedan

    daily_rate = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True)

    rating = models.FloatField(default=0.0)
    review_count = models.PositiveIntegerField(default=0)
    total_trips = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.year} {self.make} {self.model} - ${self.daily_rate}/day"

    class Meta:
        indexes = [models.Index(fields=['make', 'model']), models.Index(fields=['daily_rate']), ]


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
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["car", "start_date", "end_date"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"Reservation #{self.id} - {self.user} - {self.car}"
