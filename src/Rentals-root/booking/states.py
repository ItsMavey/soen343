"""
Vehicle state machine — State pattern.

VehicleState defines the interface. Each concrete state implements only
the transitions it permits and raises InvalidTransitionError for the rest.
Vehicle delegates all status-change calls to its current state object.
"""

from abc import ABC, abstractmethod


class InvalidTransitionError(Exception):
    pass


class VehicleState(ABC):
    @abstractmethod
    def reserve(self, vehicle): pass

    @abstractmethod
    def confirm(self, vehicle): pass

    @abstractmethod
    def return_vehicle(self, vehicle): pass

    @abstractmethod
    def send_to_maintenance(self, vehicle): pass


class AvailableState(VehicleState):
    def reserve(self, vehicle):
        vehicle.vehicle_status = "RESERVED"
        vehicle.save(update_fields=["vehicle_status"])

    def confirm(self, vehicle):
        raise InvalidTransitionError("Vehicle must be reserved before it can be confirmed in-use.")

    def return_vehicle(self, vehicle):
        raise InvalidTransitionError("Vehicle is not currently in use.")

    def send_to_maintenance(self, vehicle):
        vehicle.vehicle_status = "MAINTENANCE"
        vehicle.save(update_fields=["vehicle_status"])


class ReservedState(VehicleState):
    def reserve(self, vehicle):
        raise InvalidTransitionError("Vehicle is already reserved.")

    def confirm(self, vehicle):
        vehicle.vehicle_status = "IN_USE"
        vehicle.save(update_fields=["vehicle_status"])

    def return_vehicle(self, vehicle):
        raise InvalidTransitionError("Vehicle must be in use before it can be returned.")

    def send_to_maintenance(self, vehicle):
        raise InvalidTransitionError("Cannot send a reserved vehicle to maintenance.")


class InUseState(VehicleState):
    def reserve(self, vehicle):
        raise InvalidTransitionError("Vehicle is currently in use.")

    def confirm(self, vehicle):
        raise InvalidTransitionError("Vehicle is already in use.")

    def return_vehicle(self, vehicle):
        vehicle.vehicle_status = "AVAILABLE"
        vehicle.total_trips += 1
        vehicle.save(update_fields=["vehicle_status", "total_trips"])

    def send_to_maintenance(self, vehicle):
        raise InvalidTransitionError("Cannot send an in-use vehicle to maintenance.")


class MaintenanceState(VehicleState):
    def reserve(self, vehicle):
        raise InvalidTransitionError("Vehicle is under maintenance and cannot be reserved.")

    def confirm(self, vehicle):
        raise InvalidTransitionError("Vehicle is under maintenance.")

    def return_vehicle(self, vehicle):
        raise InvalidTransitionError("Vehicle is under maintenance.")

    def send_to_maintenance(self, vehicle):
        raise InvalidTransitionError("Vehicle is already under maintenance.")

    def complete_maintenance(self, vehicle):
        """Transition back to available once servicing is done."""
        vehicle.vehicle_status = "AVAILABLE"
        vehicle.save(update_fields=["vehicle_status"])


_STATE_MAP = {
    "AVAILABLE":   AvailableState,
    "RESERVED":    ReservedState,
    "IN_USE":      InUseState,
    "MAINTENANCE": MaintenanceState,
}


def get_state(vehicle_status: str) -> VehicleState:
    """Return the state object for the given vehicle_status string."""
    cls = _STATE_MAP.get(vehicle_status, AvailableState)
    return cls()
