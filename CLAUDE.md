# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**TABAC DRIVE** (Smart Urban Mobility Management System) — SOEN 343 Phase 3 project by team TABAC. A Django-based platform uniting public and private transportation for commuters. The working Django project lives at `src/Rentals-root/`. All `manage.py` commands must be run from that directory.

**Three user roles:**
- **Commuters** — search/reserve vehicles (cars/EVs/bikes/scooters), access parking and transit, earn loyalty rewards
- **Mobility Providers** — manage their vehicle fleet, view rental analytics
- **City Admins** — monitor activity, view external services and rental analytics

## Common Commands

```bash
# From src/Rentals-root/
python manage.py runserver          # Start dev server at http://localhost:8000
python manage.py migrate            # Apply migrations
python manage.py makemigrations     # Generate new migrations after model changes
python manage.py createsuperuser    # Create admin user
python manage.py collectstatic      # Collect static files

# Seed data
python manage.py seed_cars ../../dataset/CarRentalData.csv
python manage.py seed_bikes
python manage.py seed_scooters
python manage.py seed_user ../../dataset/person_10000.csv

# Assign roles
python manage.py set_role <username> admin      # or: commuter, provider

# Run tests
python manage.py test               # All tests
python manage.py test booking       # Single app
python manage.py test booking.tests.SomeTestClass.test_method  # Single test
```

## Architecture

**MVC** — Django templates are the View, Django views/forms are the Controller, Django models are the Model.

### System Components

| Component | Django App | Status |
|---|---|---|
| User Access Service | `users/` | Complete |
| Rental System | `booking/` | Complete |
| Vehicle Management | `booking/` | Complete |
| External Services (Parking, Transit) | `booking/` | Complete (stub + Adapter pattern) |
| Analytics (Rental, Gateway) | `booking/` | Complete |
| Gamification / Reliability Score | `booking/` | Complete |
| Notifications (Observer) | `booking/` | Complete |

### Django Apps

- **`users/`** — Custom `User` model (extends `AbstractUser`) with unique email, optional Canadian phone number, and optional address. Handles registration, login, logout, and role-based dashboard routing.
- **`booking/`** — Core rental logic: `Vehicle`, `Reservation`, `Notification` models; reservation flow (create → payment → return); analytics; gamification; notifications; fleet management; external services.
- **`core/`** — Placeholder for future shared utilities; currently empty.

### Custom User Model

`AUTH_USER_MODEL = 'users.User'` — always use `get_user_model()` rather than importing `User` directly.

### Rental Lifecycle

1. `POST /vehicles/<id>/reserve/` — Creates a `PENDING` reservation; checks for date overlaps; applies loyalty discount.
2. `POST /reservations/<id>/payment/` — Simulated payment; transitions to `CONFIRMED`.
3. `POST /reservations/<id>/return/` — Marks returned; fires RETURNED observer event.

All booking views require `@login_required`. Users can only access their own reservations.

### URL Layout

Root `urls.py` includes both `users.urls` and `booking.urls` under `''`. No conflicts because each app owns non-overlapping prefixes.

### Data Seeding

`booking/management/commands/seed_cars.py` reads CSV columns and uses `get_or_create` to avoid duplicates. `seed_bikes` and `seed_scooters` use hardcoded fleets. Datasets at `dataset/`.

## GOF Design Patterns (Phase 3) — All Implemented

1. **Strategy** (`booking/pricing.py`) — `PricingStrategy` ABC with `StandardPricing`, `WeekendPricing`, `SurgePricing`. `reserve_vehicle` view selects the active strategy at runtime.
2. **Factory** (`booking/factories.py`) — `VehicleFactory` with `ProviderFactoryA`/`ProviderFactoryB` abstracts vehicle instantiation.
3. **State** (`booking/states.py`) — `VehicleState` ABC with `AvailableState`, `ReservedState`, `InUseState`, `MaintenanceState`. `Vehicle` delegates state transitions instead of using conditionals.
4. **Observer** (`booking/observers.py`) — `Subject`/`Observer` ABCs. `Vehicle._notify_observers()` fires MAINTENANCE / AVAILABLE / RETURNED events to `UserNotifier`, `AdminDashboard`, `RecommendationService`. Creates `Notification` records with optional reservation FK for deep-linking.
5. **Adapter** (`booking/adapters.py`) — `TransitFacade` aggregates `GTFSAdapter` and `CityAPIAdapter` so views talk to a unified `PublicTransportService` interface.

### Pure Fabrication

**`booking/sustainability.py`** — stateless service for gamification. No new model fields; all computed from existing `Reservation` data:
- `reliability_score(user)` — (returned / total non-pending) × 100
- `co2_saved_kg(vehicle, days)` — CO₂ saved vs gasoline baseline per rental
- `total_co2_saved(user)` — aggregate across all completed rentals
- `loyalty_discount(score)` — returns `(rate, label)` based on score tiers
- `apply_discount(amount, score)` — applies discount rate to a price

### Notification System

`Notification` model: `user`, `vehicle` (nullable FK), `reservation` (nullable FK), `message`, `event_type`, `is_read`, `created_at`.

Context processor (`booking/context_processors.py`) injects `unread_notifications` count into every template. Navbar shows a bell icon with badge. Notifications page marks all as read; each notification links to its reservation if the FK is set.

## Dependencies

- Django 6.0.2
- `django-phonenumber-field` — phone number input/validation
- `django-address` — structured address field on `User`

Install: `pip install -r requirements.txt` (from repo root)

## Database

SQLite3 (`src/Rentals-root/db.sqlite3`) — not committed to git. For schema changes always run `makemigrations` then `migrate`.
