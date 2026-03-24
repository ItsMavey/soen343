# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SUMMS** (Smart Urban Mobility Management System) — SOEN 343 Phase 3 project by team TABAC. A Django-based platform uniting public and private transportation for commuters. The working Django project lives at `src/Rentals-root/`. All `manage.py` commands must be run from that directory.

**Three user roles:**
- **Commuters** — search/reserve vehicles (cars/EVs/bikes/scooters), access parking and transit
- **Mobility Providers** — manage their vehicle fleet, view rental analytics
- **City Admins** — monitor traffic, view external services and rental analytics

## Common Commands

```bash
# From src/Rentals-root/
python manage.py runserver          # Start dev server at http://localhost:8000
python manage.py migrate            # Apply migrations
python manage.py makemigrations     # Generate new migrations after model changes
python manage.py createsuperuser    # Create admin user
python manage.py collectstatic      # Collect static files

# Seed car data from CSV
python manage.py seed_cars ../../dataset/CarRentalData.csv

# Run tests
python manage.py test               # All tests
python manage.py test booking       # Single app
python manage.py test booking.tests.SomeTestClass.test_method  # Single test
```

## Architecture

**MVC** — Django templates are the View, Django views/forms are the Controller, Django models are the Model. Each component communicates through the Controller layer, which exposes APIs to the View.

### System Components

| Component | Django App | Status |
|---|---|---|
| User Access Service | `users/` | Complete |
| Rental System | `booking/` | Complete |
| Vehicle Management | `booking/` | Complete |
| External Services (Parking, Transit) | TBD | Navigation stub needed |
| Analytics (Rental, Gateway, Sustainability) | TBD | Partial — Sprint 3 |
| Gamification / Reliability Score | TBD | Partial — Sprint 3 |

### Django Apps

- **`users/`** — Custom `User` model (extends `AbstractUser`) with unique email, optional Canadian phone number, and optional address. Handles registration, login, logout.
- **`booking/`** — Core rental logic: `Car` and `Reservation` models, car search/filter, reservation flow (create → payment → return), and a `seed_cars` management command.
- **`core/`** — Placeholder for future shared utilities; currently empty.

### Custom User Model

`AUTH_USER_MODEL = 'users.User'` — always use `get_user_model()` rather than importing `User` directly.

### Rental Lifecycle

1. `POST /cars/<id>/reserve/` — Creates a `PENDING` reservation; checks for date overlaps.
2. `POST /reservations/<id>/payment/` — Simulated payment; transitions to `CONFIRMED`.
3. `POST /reservations/<id>/return/` — Marks returned; updates `car.total_trips` and `car.is_available`.

All booking views require `@login_required`. Users can only access their own reservations.

### URL Layout

Root `urls.py` includes both `users.urls` and `booking.urls` under `''`. No conflicts because each app owns non-overlapping prefixes (`login/`, `register/` vs. `cars/`, `reservations/`).

### Data Seeding

`booking/management/commands/seed_cars.py` reads CSV columns (`vehicle.make`, `vehicle.model`, `vehicle.year`, `fuelType`, `vehicle.type`, `daily_rate`, `is_available`, `rating`, `reviewCount`, `renterTripsTaken`) and uses `get_or_create` to avoid duplicates. Datasets at `dataset/`.

## GOF Design Patterns (Phase 3)

These patterns are specified in the design doc and must be reflected in implementation:

1. **Strategy** — `PricingStrategy` interface with `StandardPricing`, `WeekendPricing`, `SurgePricing`. `Trip`/`Reservation` delegates fare calculation to the selected strategy at runtime.
2. **Factory** — `VehicleFactory` (and provider-specific `ProviderFactoryA/B`) abstracts vehicle instantiation away from `MobilityProvider`.
3. **State** — `VehicleState` interface with `AvailableState`, `ReservedState`, `InUseState`, `MaintenanceState`. `Vehicle` delegates `reserve()`, `startUsage()`, etc. to its current state object instead of using conditionals on a status field.
4. **Observer** — `Subject`/`Observer` interfaces. `VehicleSubject` and `ParkingSpotSubject` notify `UserNotifier`, `AdminDashboard`, `RecommendationService` on state changes.
5. **Adapter** — `TransitFacade` aggregates `TransitProvider` adapters (`GTFSAdapter`, `CityAPIAdapter`) so `PublicTransportService` talks to a unified interface regardless of external API format.

## Sprint 3 Remaining TODOs

From the doc (see GitHub issues):
- Navigation to External Services (#12) — Parking and Public Transit pages must be navigable even if backed by stub/abstracted services
- Analytics (#13) — at least one rental analytic and one gateway analytic working
- Gamification — Carbon Footprint per Rental, Vehicle Return Points, Rewards/Discounts

## Dependencies

- Django 6.0.2
- `django-phonenumber-field` — phone number input/validation
- `django-address` — structured address field on `User`

Install: `pip install -r requirements.txt`

## Database

SQLite3 (`src/Rentals-root/db.sqlite3`). For schema changes always run `makemigrations` then `migrate`.
