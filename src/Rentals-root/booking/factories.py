from .models import Car, Bike, Scooter

"""
Vehicle Factory Class
"""
class VehicleFactory:
    provider_name = ""

    def create_car(self, **kwargs):
        kwargs.setdefault("provider", self.provider_name)
        kwargs["vehicle_kind"] = "CAR"
        return Car.objects.create(**kwargs)

    def create_bike(self, **kwargs):
        kwargs.setdefault("provider", self.provider_name)
        kwargs["vehicle_kind"] = "BIKE"
        return Bike.objects.create(**kwargs)

    def create_scooter(self, **kwargs):
        kwargs.setdefault("provider", self.provider_name)
        kwargs["vehicle_kind"] = "SCOOTER"
        return Scooter.objects.create(**kwargs)


class ProviderFactoryA(VehicleFactory):
    """Primary fleet provider — cars and EVs."""
    provider_name = "ProviderA"


class ProviderFactoryB(VehicleFactory):
    """Urban mobility provider — bikes and scooters."""
    provider_name = "ProviderB"
