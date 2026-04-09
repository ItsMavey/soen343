<div align="center">
  <h3 align="center">Team TABAC</h3>
  <p align="center">Smart Urban Mobility Management System — SOEN 343</p>
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
| **Commuter** | Browse/search/reserve vehicles, plan multimodal trips, view live parking & transit, earn loyalty rewards |
| **Mobility Provider** | Add/edit/remove vehicles, view rental analytics, receive maintenance and overdue notifications |
| **City Admin** | Monitor platform activity, view rental and gateway analytics, manage all users |

**Implemented features:**
- Complete rental lifecycle: search → reserve → payment (simulated) → return
- Role-based dashboards with analytics
- Interactive maps: vehicle fleet map, parking map with live OSM data, transit stop map
- Multimodal trip planner: combines public transit + shared vehicles with OSRM-routed legs
- External services: parking (live data via Overpass API, time-varying occupancy) and public transit (real stop data from OpenStreetMap)
- Loyalty/gamification: reliability score, CO₂ savings, tiered discounts
- Overdue detection and notification system

---

## Architecture

**Architectural style:** MVC — Django templates (View), Django views/forms (Controller), Django models (Model).

**Django apps:**

| App | Responsibility |
|---|---|
| `users/` | Custom `User` model, registration, login/logout, role-based dashboard routing, profile settings |
| `booking/` | Vehicle models, reservation lifecycle, pricing, state machine, observer/notification system, analytics, external services, maps, trip planning |

**Key source files:**

| Concern | File |
|---|---|
| Models (Vehicle, Reservation, Notification) | `booking/models.py` |
| GOF — Strategy (pricing) | `booking/pricing.py` |
| GOF — Strategy (itinerary planning) | `booking/trip_strategies.py` |
| GOF — State (vehicle lifecycle) | `booking/states.py` |
| GOF — Observer (notifications) | `booking/observers.py` |
| GOF — Factory (vehicle creation) | `booking/factories.py` |
| GOF — Adapter + Facade (parking, transit) | `booking/external_services.py` |
| Pure Fabrication — Gamification | `booking/sustainability.py` |
| Views / controllers | `booking/views/` |
| URL routing | `booking/urls.py`, `users/urls.py` |

---

## GOF Design Patterns

All patterns are fully implemented and wired into the live application.

| Pattern | File | Description |
|---|---|---|
| **Strategy** | `booking/pricing.py` | `PricingStrategy` ABC — `StandardPricing` (×1.00), `WeekendPricing` (×1.25), `SurgePricing` (×1.50) selected at reservation time |
| **Strategy** | `booking/trip_strategies.py` | `ItineraryStrategy` ABC — `TransitFirstStrategy` (transit + vehicle) and `VehicleOnlyStrategy`; trip planner runs both and returns all feasible options |
| **State** | `booking/states.py` | `VehicleState` ABC — `AvailableState`, `ReservedState`, `InUseState`, `MaintenanceState`; invalid transitions raise `InvalidTransitionError` |
| **Observer** | `booking/observers.py` | `Vehicle._notify_observers()` fires `UserNotifier`, `AdminDashboard`, `RecommendationService`; `fire_overdue_notifications()` for overdue detection |
| **Factory** | `booking/factories.py` | `ProviderFactoryA` (cars/EVs) and `ProviderFactoryB` (bikes/scooters) encapsulate vehicle creation |
| **Adapter + Facade** | `booking/external_services.py` | `GTFSAdapter` + `CityAPIAdapter` implement `TransitProvider`; `TransitFacade` aggregates both. `OSMParkingAdapter` wraps Overpass API with `ParkingService` fallback |

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
![Leaflet](https://img.shields.io/badge/Leaflet.js-1.9-199900?style=for-the-badge&logo=leaflet&logoColor=white)
![OpenStreetMap](https://img.shields.io/badge/OpenStreetMap-7EBC6F?style=for-the-badge&logo=openstreetmap&logoColor=white)

**Backend**
| | |
|---|---|
| Python 3.10+ / Django 6.0.2 | Web framework, ORM, auth |
| SQLite3 | Development database |
| django-phonenumber-field | Phone number validation |
| django-address | Structured address field on User |

**Frontend**
| | |
|---|---|
| Leaflet.js 1.9.4 | Interactive maps (no API key required) |
| OpenStreetMap | Map tile layer |
| Bootstrap 5 | Responsive grid and layout |

**External APIs** (all free, no API key required)
| API | Used for |
|---|---|
| [Overpass API](https://overpass-api.de) | Live parking lots and transit stops from OpenStreetMap data |
| [Nominatim](https://nominatim.org) | Address geocoding in the trip planner |
| [OSRM](https://router.project-osrm.org) | Turn-by-turn walk and drive route geometry |
| Browser Geolocation API | "Use my location" in trip planner and fleet browse |

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

### Optional: full fleet seed

```bash
# Seed 60 cars + 60 bikes + 60 scooters across all 6 cities, then demo data
python manage.py seed_all

# Or individually:
python manage.py seed_cars_local     # 60 cars (no CSV needed)
python manage.py seed_bikes          # 60 bikes
python manage.py seed_scooters       # 60 scooters

# Wipe all vehicles, reservations, and notifications
python manage.py unseed_vehicles
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
- 14 reservations spanning all statuses: returned, confirmed, overdue, pending, cancelled
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

# Seed / unseed
python manage.py seed_demo           # demo users + vehicles (idempotent)
python manage.py seed_all            # full fleet across all cities
python manage.py unseed_vehicles     # wipe vehicles, reservations, notifications

# Assign role to a user
python manage.py set_role <username> admin      # or: commuter, provider

# Run all tests
python manage.py test booking
```

---

## Contributors

<a href="https://github.com/ItsMavey/soen343/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ItsMavey/soen343" />
</a>
