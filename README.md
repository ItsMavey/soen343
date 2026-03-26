<div align="center">
  <h3 align="center">TABAC DRIVE</h3>
  <p align="center">Smart Urban Mobility Management System — SOEN 343 Phase III</p>
</div>

---

## Table of Contents

- [About](#about)
- [Architecture](#architecture)
- [GOF Design Patterns](#gof-design-patterns)
- [Team](#team)
- [Tech Stack](#tech-stack)
- [Project Setup](#project-setup)
- [Demo Credentials](#demo-credentials)
- [Common Commands](#common-commands)
- [Contributors](#contributors)

---

## About

TABAC DRIVE is a Django-based urban mobility platform that unites private vehicle rentals and public transportation services for three user roles:

| Role | Capabilities |
|---|---|
| **Commuter** | Browse/search/reserve vehicles, pay, return, view parking & transit, earn loyalty rewards |
| **Mobility Provider** | Add/edit/remove vehicles, view rental analytics, receive maintenance and overdue notifications |
| **City Admin** | Monitor platform activity, view rental and gateway analytics, manage all users |

**Sprint 3 implemented features:**
- Complete rental lifecycle: search → reserve → payment (simulated) → return
- Role-based dashboards with analytics
- Overdue detection and notification system
- External services: parking (city-filtered, time-varying occupancy) and public transit (live stop data from OpenStreetMap via Overpass API)
- Loyalty/gamification: reliability score, CO₂ savings, tiered discounts
- 31 unit tests covering all GOF patterns and sustainability module

---

## Architecture

**Architectural style:** MVC — Django templates (View), Django views/forms (Controller), Django models (Model).

**Django apps:**

| App | Responsibility |
|---|---|
| `users/` | Custom `User` model, registration, login/logout, role-based dashboard routing, profile settings |
| `booking/` | Vehicle models, reservation lifecycle, pricing, state machine, observer/notification system, analytics, external services |
| `core/` | Reserved for shared utilities |

**Key source files:**

| Concern | File |
|---|---|
| Models (Vehicle, Reservation, Notification) | `booking/models.py` |
| GOF — Strategy (pricing) | `booking/pricing.py` |
| GOF — State (vehicle lifecycle) | `booking/states.py` |
| GOF — Observer (notifications) | `booking/observers.py` |
| GOF — Factory (vehicle creation) | `booking/factories.py` |
| GOF — Adapter (parking + transit) | `booking/services.py` |
| Pure Fabrication — Gamification | `booking/sustainability.py` |
| All views / controllers | `booking/views.py`, `users/views.py` |
| URL routing | `booking/urls.py`, `users/urls.py` |

---

## GOF Design Patterns

All five patterns are fully implemented and wired into the live application.

### 1. Strategy — Dynamic Pricing (`booking/pricing.py`)

**Problem:** Rental pricing varies by demand and date (standard, weekend surcharge, surge pricing). Hard-coding conditionals in the reservation view violates Open/Closed Principle.

**Solution:** `PricingStrategy` ABC with three concrete strategies — `StandardPricing`, `WeekendPricing`, `SurgePricing`. The `reserve_vehicle` view calls `select_strategy()` at runtime; adding a new pricing rule requires no changes to existing code.

**Without it:** One large conditional block in the view; every new pricing rule modifies existing logic and risks regressions.

```
PricingStrategy (ABC)
  ├── StandardPricing   ×1.00
  ├── WeekendPricing    ×1.25
  └── SurgePricing      ×1.50
```

---

### 2. State — Vehicle Lifecycle (`booking/states.py`)

**Problem:** A vehicle transitions between Available → Reserved → In Use → Maintenance. Without structure, every transition requires checking current status with conditionals scattered across the codebase.

**Solution:** `VehicleState` ABC with `AvailableState`, `ReservedState`, `InUseState`, `MaintenanceState`. `Vehicle` delegates all transitions to its current state object; invalid transitions raise `InvalidTransitionError`.

**Without it:** Long `if vehicle_status == X` chains in every view that touches vehicle state; illegal transitions go unchecked.

---

### 3. Observer — Notification System (`booking/observers.py`)

**Problem:** When a vehicle changes state (maintenance, return, available), multiple parties need to be notified — the renter, city admins, and the recommendation engine — without the vehicle model knowing about them.

**Solution:** `Subject`/`Observer` ABCs. `Vehicle._notify_observers(event)` fires `UserNotifier`, `AdminDashboard`, and `RecommendationService`. Each creates `Notification` DB records independently. `fire_overdue_notifications()` extends this for overdue rental detection (idempotent).

**Without it:** Vehicle model directly imports and calls notification logic; tight coupling prevents independent extension.

---

### 4. Factory — Vehicle Instantiation (`booking/factories.py`)

**Problem:** Two provider fleets (ProviderA — cars/EVs, ProviderB — bikes/scooters) create vehicles differently. Client code should not need to know the concrete vehicle class.

**Solution:** `VehicleFactory` base with `ProviderFactoryA` and `ProviderFactoryB` concrete factories. Each factory encapsulates `Car`, `Bike`, or `Scooter` creation with provider-specific defaults.

**Without it:** Seeding and creation logic directly instantiate concrete model classes; switching provider strategies requires editing call sites.

---

### 5. Adapter — External Services (`booking/services.py`)

**Problem:** Parking and transit data come from incompatible external sources (OpenStreetMap Overpass API for transit stops, hardcoded city data for parking). The rest of the app should talk to a single interface regardless of source.

**Solution:** `TransitProvider` interface adapted by `GTFSAdapter` (real bus stops from Overpass API) and `CityAPIAdapter` (real metro stations from Overpass API). `TransitFacade` aggregates both. `ParkingService` follows the same abstraction. Swapping data sources requires only a new adapter class.

**Without it:** Views directly contain HTTP calls and parsing logic; changing data sources breaks view code.

---

### Pure Fabrication — Gamification (`booking/sustainability.py`)

A stateless service class with no corresponding domain entity — justified by GRASP Pure Fabrication to avoid bloating `User` or `Reservation` models with unrelated computation:

- `reliability_score(user)` — % of reservations properly returned
- `co2_saved_kg(vehicle, days)` — CO₂ saved vs gasoline baseline
- `total_co2_saved(user)` — aggregate across all completed rentals
- `loyalty_discount(score)` — tiered discount rate (0%, 5%, 10%, 15%)
- `apply_discount(amount, score)` — applies discount to a reservation total

---

## Team

| Name | Student ID |
|---|---|
| Adam Ousmeer | 40246695 |
| Daniel Ganchev | 40315755 |
| Abed-Elmouhsen Cherkawi | 40323359 |
| Emre Emuler | 40212481 |
| Dylan Bourret | 40287207 |
| Yanis Djeridi | 40227313 |

---

## Tech Stack

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)

---

## Project Setup

**Requirements:** Python 3.10+

```bash
# 1. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate        # Windows
source venv/bin/activate       # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Move into the Django project
cd src/Rentals-root

# 4. Apply migrations
python manage.py migrate

# 5. Seed demo data (creates all demo users + vehicles + reservations)
python manage.py seed_demo

# 6. Start the dev server
python manage.py runserver
```

Open [http://localhost:8000](http://localhost:8000) in your browser and log in with the demo credentials below.

### Optional: full fleet + user seed

```bash
python manage.py seed_cars ../../dataset/CarRentalData.csv
python manage.py seed_bikes
python manage.py seed_scooters
python manage.py seed_user ../../dataset/person_10000.csv --limit 200
```

---

## Demo Credentials

| Role | Username | Password |
|---|---|---|
| City Admin | `qwer` | `qwerqwer!` |
| Mobility Provider | `qwer1` | `qwerqwer!` |
| Commuter | `qwer2` | `qwerqwer!` |

The `seed_demo` command creates these accounts and pre-populates:
- 10 vehicles (7 cars, 2 bikes, 1 scooter) owned by the provider
- 14 reservations spanning all statuses: returned, confirmed, **overdue** (edge case), pending, cancelled
- Notifications, maintenance vehicle, extra commuter users for richer analytics

---

## Common Commands

All commands run from `src/Rentals-root/`.

```bash
# Run the server
python manage.py runserver

# Database
python manage.py makemigrations
python manage.py migrate

# Seed demo data (idempotent, safe to re-run)
python manage.py seed_demo

# Assign role to a user
python manage.py set_role <username> admin      # or: commuter, provider

# Run all tests (31 tests)
python manage.py test booking

# Run a specific test class
python manage.py test booking.tests.PricingStrategyTests
python manage.py test booking.tests.VehicleStateTests
python manage.py test booking.tests.ObserverNotificationTests
```

---

## Contributors

<a href="https://github.com/ItsMavey/soen343/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ItsMavey/soen343" />
</a>
