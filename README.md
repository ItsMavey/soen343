[forks-shield]: https://img.shields.io/github/forks/ItsMavey/soen343.svg?style=for-the-badge

[forks-url]: https://github.com/ItsMavey/soen343/network/members

[stars-shield]: https://img.shields.io/github/stars/ItsMavey/soen343.svg?style=for-the-badge

[stars-url]: https://github.com/ItsMavey/soen343/stargazers

[issues-shield]: https://img.shields.io/github/issues/ItsMavey/soen343.svg?style=for-the-badge

[issues-url]: https://github.com/ItsMavey/soen343/issues

<div align="center">

[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]

<h3 align="center">Team TABAC — SOEN 343</h3>

  <p align="center">
    Smart Urban Mobility Management System (SUMMS)
    <br />
    <br />
    <a href="https://soen343.adam-ousmer.dev"><strong>View Live Project »</strong></a>
    &middot;
    <a href="https://github.com/ItsMavey/soen343"><strong>Explore the docs »</strong></a>
    <br />
    <a href="https://github.com/ItsMavey/soen343/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    &middot;
    <a href="https://github.com/ItsMavey/soen343/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>

</div>

---

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about">About</a></li>
    <li><a href="#architecture">Architecture</a></li>
    <li><a href="#gof-design-patterns">GOF Design Patterns</a></li>
    <li><a href="#tech-stack">Tech Stack</a>
      <ul>
        <li><a href="#infrastructure--security">Infrastructure & Security</a></li>
        <li><a href="#monitoring--logging">Monitoring & Logging</a></li>
      </ul>
    </li>
    <li><a href="#setup">Setup</a></li>
    <li><a href="#demo-credentials">Demo Credentials</a></li>
    <li><a href="#common-commands">Common Commands</a></li>
    <li><a href="#team">Team</a></li>
  </ol>
</details>

---

## About

Django-based urban mobility platform with three user roles:

| Role                  | Capabilities                                                                            |
|-----------------------|-----------------------------------------------------------------------------------------|
| **Commuter**          | Search/reserve vehicles, plan multimodal trips, view parking & transit, loyalty rewards |
| **Mobility Provider** | Manage fleet, view rental analytics, receive maintenance/overdue alerts                 |
| **City Admin**        | Platform analytics, user oversight, rental and gateway dashboards                       |

---

## Architecture

Layered MVC monolith — two Django apps (`users`, `booking`) sharing one SQLite database.

| Layer                | What's in it                                                                                         |
|----------------------|------------------------------------------------------------------------------------------------------|
| Presentation         | `booking/views/`, `users/views.py` — function-based views + DTL templates                            |
| Service              | `booking/services/` — ReservationService, VehicleService, AnalyticsService, RewardsService           |
| Domain / Patterns    | `booking/models.py`, `states.py`, `pricing.py`, `observers.py`, `factories.py`, `trip_strategies.py` |
| External Integration | `booking/external_services.py` — Overpass, OSRM, Nominatim via Adapter + Facade                      |
| Persistence          | Django ORM → SQLite                                                                                  |

---

## GOF Design Patterns

| Pattern                  | File                           | Role                                                                                                              |
|--------------------------|--------------------------------|-------------------------------------------------------------------------------------------------------------------|
| **Strategy** (pricing)   | `booking/pricing.py`           | StandardPricing ×1.00 / WeekendPricing ×1.25 / SurgePricing ×1.50 — selected at reservation time                  |
| **Strategy** (itinerary) | `booking/trip_strategies.py`   | TransitFirstStrategy and VehicleOnlyStrategy — trip planner runs both, returns feasible options                   |
| **State**                | `booking/states.py`            | AvailableState / ReservedState / InUseState / MaintenanceState — invalid transitions raise InvalidTransitionError |
| **Observer**             | `booking/observers.py`         | Vehicle fires MAINTENANCE / AVAILABLE / RETURNED events to UserNotifier, AdminDashboard, RecommendationService    |
| **Factory Method**       | `booking/factories.py`         | ProviderFactoryA (cars) and ProviderFactoryB (bikes/scooters)                                                     |
| **Adapter + Facade**     | `booking/external_services.py` | GTFSAdapter + CityAPIAdapter implement TransitProvider; TransitFacade aggregates both                             |

Diagrams and descriptions: `artifacts/DesignPatterns/`

---

## Tech Stack

#### Languages

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

#### Backend & Framework

![Django](https://img.shields.io/badge/django-%23092E20.svg?style=for-the-badge&logo=django&logoColor=white)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)

#### Frontend

![Bootstrap](https://img.shields.io/badge/bootstrap-%238511FA.svg?style=for-the-badge&logo=bootstrap&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=Leaflet&logoColor=white)

#### External APIs

![OpenStreetMap](https://img.shields.io/badge/OpenStreetMap-7EBC6F?style=for-the-badge&logo=openstreetmap&logoColor=white)

Overpass API (live parking lots and transit stops), Nominatim (address geocoding), OSRM (walk/drive route geometry),
Browser Geolocation API ("use my location" in trip planner).

#### Infrastructure & Security

![Oracle](https://img.shields.io/badge/Oracle-F80000?style=for-the-badge&logo=oracle&logoColor=white)
![Cloudflare](https://img.shields.io/badge/Cloudflare-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)
![Tailscale](https://img.shields.io/badge/Tailscale-121212?style=for-the-badge&logo=tailscale&logoColor=white)
![k3s](https://img.shields.io/badge/k3s-%23FFC61C.svg?style=for-the-badge&logo=k3s&logoColor=black)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Podman](https://img.shields.io/badge/Podman-%23892CA0.svg?style=for-the-badge&logo=podman&logoColor=white)

The infrastructure uses a Zero Trust model on Oracle ARM nodes, routing all traffic through Cloudflare Tunnels to hide
the origin server from the public internet. We replaced standard Kubernetes with k3s for better resource efficiency on
ARM, using Podman for secure, rootless container execution. Management is handled via Tailscale for identity-based SSH
and New Relic for firewall-friendly monitoring.

#### Monitoring & Logging

![New Relic](https://img.shields.io/badge/newrelic-%2300b1cc.svg?style=for-the-badge&logo=newrelic&logoColor=white)

**New Relic** is deployed as a k3s agent, providing full-stack telemetry without needing to punch any holes in our
firewall.

> **Note:** The entirety of the code and configuration for the node has been managed directly on the node via SSH due to
> the nature of the files. The files contain private keys and certificates that cannot be pushed to GitHub.

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

| Role              | Username | Password    |
|-------------------|----------|-------------|
| City Admin        | `qwer`   | `qwerqwer!` |
| Mobility Provider | `qwer1`  | `qwerqwer!` |
| Commuter          | `qwer2`  | `qwerqwer!` |

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

| Name                    | Student ID |
|-------------------------|------------|
| Adam Ousmeer            | 40246695   |
| Daniel Ganchev          | 40315755   |
| Abed-Elmouhsen Cherkawi | 40323359   |
| Emre Emuler             | 40212481   |
| Dylan Bourret           | 40287207   |
| Yanis Djeridi           | 40227313   |

---

<a href="https://github.com/ItsMavey/soen343/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ItsMavey/soen343" />
</a>