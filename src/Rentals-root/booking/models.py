from django.db import models


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
