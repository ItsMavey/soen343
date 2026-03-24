from address.models import AddressField
from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class User(AbstractUser):
    ROLE_COMMUTER = "COMMUTER"
    ROLE_PROVIDER = "PROVIDER"
    ROLE_ADMIN = "ADMIN"
    ROLE_CHOICES = [
        (ROLE_COMMUTER, "Commuter"),
        (ROLE_PROVIDER, "Mobility Provider"),
        (ROLE_ADMIN, "City Admin"),
    ]

    email = models.EmailField(unique=True)
    address = AddressField(null=True, blank=True, on_delete=models.SET_NULL)
    phone_number = PhoneNumberField(region="CA", blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_COMMUTER)

    @property
    def is_commuter(self):
        return self.role == self.ROLE_COMMUTER

    @property
    def is_provider(self):
        return self.role == self.ROLE_PROVIDER

    @property
    def is_city_admin(self):
        return self.role == self.ROLE_ADMIN

    def __str__(self):
        return self.username
