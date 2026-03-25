<div align="center">
  <a href="https://github.com/ItsMavey/soen343">
    <img src=".github/assets/logo.png" alt="Logo" width="200" height="200">
  </a>

  <h3 align="center">TABAC DRIVE</h3>
  <p align="center">Smart Urban Mobility Management System — SOEN 343 Term Project</p>
</div>

---

## Table of Contents

- [About](#about)
- [Team](#team)
- [Tech Stack](#tech-stack)
- [Project Setup](#project-setup)
- [Common Commands](#common-commands)
- [Contributors](#contributors)

---

## About

TABAC DRIVE is a Django-based urban mobility platform that unites public and private transportation for commuters, mobility providers, and city admins.

**Three user roles:**
- **Commuter** — search and reserve vehicles, access parking and transit info, earn loyalty rewards
- **Mobility Provider** — manage a vehicle fleet, view rental analytics
- **City Admin** — monitor system activity, view analytics and external services

**GOF Design Patterns implemented:** Strategy, State, Observer, Factory, Adapter

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

# 5. Seed vehicle data
python manage.py seed_cars ../../dataset/CarRentalData.csv
python manage.py seed_bikes
python manage.py seed_scooters

# 6. (Optional) Seed user accounts
python manage.py seed_user ../../dataset/person_10000.csv

# 7. (Optional) Create a superuser
python manage.py createsuperuser

# 8. Start the dev server
python manage.py runserver
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Common Commands

All commands run from `src/Rentals-root/`.

```bash
# Run the server
python manage.py runserver

# Database
python manage.py makemigrations
python manage.py migrate

# Assign City Admin role to a user
python manage.py set_role <username> admin
# Other roles: commuter, provider

# Run tests
python manage.py test
```

---

## Contributors

<a href="https://github.com/ItsMavey/soen343/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ItsMavey/soen343" />
</a>
