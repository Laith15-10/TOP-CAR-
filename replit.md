# Car Wash Pro

A Django-based car wash service platform that connects customers with drivers.

## Overview

This application allows customers to create car wash service orders, which are then assigned to the nearest available driver based on geolocation (latitude/longitude).

## Tech Stack

- **Backend**: Django 5.2 (Python 3.11)
- **Database**: SQLite (`db.sqlite3`)
- **Language**: Arabic (ar) / Jordan timezone (Asia/Amman)
- **Server**: Django dev server (dev), Gunicorn (production)

## Project Structure

```
car_wash_pro/        - Django project configuration (settings, urls, wsgi/asgi)
accounts/            - Main app (models, views, forms, templates, migrations)
  templates/         - HTML templates (home, order, order_success, registration)
  migrations/        - Database migration files
media/               - Uploaded media files (driver images)
staticfiles/         - Collected static files
```

## Key Features

- Customer order creation with location input
- Driver management with verification images (ID card, license)
- Nearest driver assignment using Euclidean distance calculation
- Session-based authentication (1-year session duration)
- Arabic UI

## Running the App

```bash
python3.11 manage.py runserver 0.0.0.0:5000
```

## Workflow

- **Start application**: `python3.11 manage.py runserver 0.0.0.0:5000` on port 5000

## Settings Notes

- `ALLOWED_HOSTS = ['*']` — allows all hosts for Replit proxy
- `CSRF_TRUSTED_ORIGINS` — configured for Replit domains
- `MEDIA_ROOT` / `MEDIA_URL` — for uploaded driver verification images
- `DEFAULT_AUTO_FIELD = BigAutoField`
