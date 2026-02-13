from address.models import AddressField
from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class User(AbstractUser):
    address = AddressField(null=True, blank=True, on_delete=models.SET_NULL)
    phone_number = PhoneNumberField(region="CA")

    def __str__(self):
        return self.username
