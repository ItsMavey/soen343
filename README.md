<div align="center">
  <h3 align="center">Team TABAC — SOEN 343</h3>
  <p align="center">Smart Urban Mobility Management System (SUMMS)</p>
</div>

---

## About

Django-based urban mobility platform with three user roles:

| Role | Capabilities |
|---|---|
| **Commuter** | Search/reserve vehicles, plan multimodal trips, view parking & transit, loyalty rewards |
| **Mobility Provider** | Manage fleet, view rental analytics, receive maintenance/overdue alerts |
| **City Admin** | Platform analytics, user oversight, rental and gateway dashboards |

---

## Architecture

Layered MVC monolith — two Django apps (`users`, `booking`) sharing one SQLite database.

| Layer | What's in it |
|---|---|
| Presentation | `booking/views/`, `users/views.py` — function-based views + DTL templates |
| Service | `booking/services/` — ReservationService, VehicleService, AnalyticsService, RewardsService |
| Domain / Patterns | `booking/models.py`, `states.py`, `pricing.py`, `observers.py`, `factories.py`, `trip_strategies.py` |
| External Integration | `booking/external_services.py` — Overpass, OSRM, Nominatim via Adapter + Facade |
| Persistence | Django ORM → SQLite |

---

## GOF Design Patterns

| Pattern | File | Role |
|---|---|---|
| **Strategy** (pricing) | `booking/pricing.py` | StandardPricing ×1.00 / WeekendPricing ×1.25 / SurgePricing ×1.50 — selected at reservation time |
| **Strategy** (itinerary) | `booking/trip_strategies.py` | TransitFirstStrategy and VehicleOnlyStrategy — trip planner runs both, returns feasible options |
| **State** | `booking/states.py` | AvailableState / ReservedState / InUseState / MaintenanceState — invalid transitions raise InvalidTransitionError |
| **Observer** | `booking/observers.py` | Vehicle fires MAINTENANCE / AVAILABLE / RETURNED events to UserNotifier, AdminDashboard, RecommendationService |
| **Factory Method** | `booking/factories.py` | ProviderFactoryA (cars) and ProviderFactoryB (bikes/scooters) |
| **Adapter + Facade** | `booking/external_services.py` | GTFSAdapter + CityAPIAdapter implement TransitProvider; TransitFacade aggregates both |

Diagrams and descriptions: `artifacts/DesignPatterns/`

---

## Tech Stack

| | |
|---|---|
| Python 3.10+ / Django 6.0.2 | Backend framework, ORM, auth |
| SQLite3 | Database |
| Leaflet.js 1.9.4 | Interactive maps (no API key) |
| Bootstrap 5 | UI layout |
| Overpass API | Live parking lots and transit stops (OpenStreetMap) |
| Nominatim | Address geocoding |
| OSRM | Walk/drive route geometry |
| Browser Geolocation API | "Use my location" in trip planner |

---

## Setup

**Requirements:** Python 3.10+

```bash
python -m venv venv
.\venv\Scripts\Activate          # Windows
source venv/bin/activate         # macOS/Linux

pip install -r requirements.txt
cd src/Rentals-root
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open [http://localhost:8000](http://localhost:8000).

---

## Demo Credentials

| Role | Username | Password |
|---|---|---|
| City Admin | `qwer` | `qwerqwer!` |
| Mobility Provider | `qwer1` | `qwerqwer!` |
| Commuter | `qwer2` | `qwerqwer!` |

`seed_demo` creates these accounts with 10 vehicles, 14 reservations across all statuses, and pre-built notifications.

---

## Common Commands

All from `src/Rentals-root/`.

```bash
python manage.py runserver
python manage.py migrate

# Seed
python manage.py seed_demo           # demo data (idempotent)
python manage.py seed_all            # full fleet — 60 cars + 60 bikes + 60 scooters
python manage.py unseed_vehicles     # wipe vehicles, reservations, notifications

# Utilities
python manage.py set_role <username> admin   # or: commuter, provider

# Tests (190 tests)
python manage.py test booking.tests users.tests
```

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

<a href="https://github.com/ItsMavey/soen343/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ItsMavey/soen343" />
</a>
