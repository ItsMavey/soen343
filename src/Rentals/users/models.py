from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField
from address.models import AddressField
from django.db import models

class User(AbstractUser):

    address = AddressField()
    phone_number = PhoneNumberField(region="CA")


    def __str__(self):
        return self.username
