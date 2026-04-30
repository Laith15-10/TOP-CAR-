# TOP CAR — Automotive Services Platform

## Overview
A full-stack Django automotive services platform where customers book mobile car services and drivers accept and fulfill them.

## Features
- **Splash Screen**: 2-second animated splash → login/signup
- **Customer Registration**: name, email, phone, password
- **Driver Registration**: full documents (ID front/back, license, face photo, vehicle license, car info) + admin approval workflow
- **Admin Approval**: Drivers start as "pending" → can't access app until admin approves
- **Service Booking**: 5 services (Body Wash, Full Wash, Dry Clean, Oil Change, Oil & Filter) with Leaflet map pin, date/time picker, payment (Cash / QLIQ)
- **Real-Time Dispatch**: WebSockets (Django Channels) dispatch orders to nearest online driver
- **Driver Accept/Reject**: Drivers see customer location on map; rejection requires reason + logs it
- **Live Tracking**: Customer sees driver's moving pin on map with ETA countdown
- **Service Status Flow**: Arrived → Picking Up → In Progress → Finished
- **Payment Summary + Rating**: Price summary, 5-star rating widget
- **Admin Dashboard**: Django admin with driver approval actions, rejection log, photo previews
- **Bilingual**: Arabic (default, RTL) / English (LTR) switchable at runtime
- **Dark/Neon Theme**: #0d0d0d background, #00ffcc and #00e5ff neon accents, glow effects

## Architecture
- **Backend**: Django 5.2 + Django Channels + Daphne (ASGI)
- **Real-Time**: WebSockets via Django Channels (InMemoryChannelLayer)
- **Database**: SQLite
- **Maps**: Leaflet.js (OpenStreetMap tiles)
- **Frontend**: Bootstrap 5 + custom CSS, mobile-first layout
- **i18n**: Django i18n with gettext, Arabic + English locale files

## Key Files
- `accounts/models.py` — CustomerProfile, Driver, ServiceOrder, RejectionLog, Rating
- `accounts/views.py` — All views (auth, booking, driver dashboard, tracking, payment, rating)
- `accounts/consumers.py` — WebSocket consumers (OrderConsumer, DriverConsumer)
- `accounts/routing.py` — WebSocket URL routing
- `accounts/forms.py` — CustomerSignupForm, DriverSignupForm, BookingForm, RatingForm
- `accounts/admin.py` — Full admin with driver approval actions and photo previews
- `car_wash_pro/asgi.py` — ASGI routing with Channels
- `car_wash_pro/settings.py` — Full config with channels, i18n, media
- `accounts/templates/` — All templates (splash, login, home, booking, tracking, driver dashboard, payment, etc.)
- `locale/ar/` — Arabic translations
- `locale/en/` — English translations

## Running
```
daphne -b 0.0.0.0 -p 5000 car_wash_pro.asgi:application
```

## Admin Access
- URL: /admin/
- Username: admin
- Password: admin123

## Services & Prices
| Service | Price (JD) |
|---------|-----------|
| Body Wash | 5 |
| Full Wash | 10 |
| Dry Clean | 15 |
| Oil Change | 12 |
| Oil & Filter Change | 18 |
