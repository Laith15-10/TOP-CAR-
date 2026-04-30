# Car Wash Pro — TOP CAR

A full-stack Django automotive services platform connecting customers with drivers. Arabic-first, mobile-first design with real-time WebSocket communication.

## Tech Stack

- **Backend**: Django 5.2 (Python 3.11)
- **ASGI Server**: Daphne (WebSocket support via Django Channels)
- **Database**: SQLite (`db.sqlite3`)
- **Real-time**: Django Channels + InMemoryChannelLayer (WebSockets)
- **Static Files**: WhiteNoise
- **Language**: Arabic (ar) + English (en), Jordan timezone (Asia/Amman)

## Project Structure

```
car_wash_pro/        - Django project config (settings, urls, asgi, wsgi)
accounts/            - Main app
  models.py          - CustomerProfile, Driver, ServiceOrder, RejectionLog, Rating
  views.py           - All views (auth, booking, order flow, driver, admin)
  forms.py           - Signup, booking, rejection, rating forms
  consumers.py       - OrderConsumer + DriverConsumer (WebSocket handlers)
  routing.py         - WebSocket URL routing
  admin.py           - Django admin with approval actions & photo previews
  migrations/        - Database migrations
  templates/         - All HTML templates
locale/              - i18n .po/.mo files (ar + en)
staticfiles/         - Collected static files (WhiteNoise served)
media/               - Uploaded driver verification images
```

## Key Features

1. **Auth**: Customer/Driver signup with separate flows, driver document uploads
2. **Booking**: Leaflet map pin-drop, 5 service types, datetime picker, Cash/QLIQ payment
3. **Dispatch**: Nearest driver assignment via Euclidean distance, WebSocket notification
4. **Driver Dashboard**: Accept/Reject orders, rejection reason logging, re-dispatch on reject
5. **Live Tracking**: Customer sees moving driver pin on map, ETA countdown, location updates every 5s
6. **Order Status Flow**: Arrived → Picking Up Car → Service in Progress → Service Finished
7. **Payment & Rating**: Price summary, 5-star rating widget
8. **Admin**: Approve/reject drivers with reason, photo previews for all documents
9. **i18n**: Arabic + English, language toggle
10. **Dark/Neon Theme**: #0d0d0d background, #00ffcc/#00e5ff neon accents, splash screen

## Running the App

```bash
python3.11 manage.py migrate && daphne -b 0.0.0.0 -p 5000 car_wash_pro.asgi:application
```

## Workflow

- **Start application**: Daphne ASGI server on port 5000 (supports HTTP + WebSocket)

## Default Credentials

- **Admin**: `admin` / `admin123` (at `/admin/`)

## Deployment

- Target: autoscale
- Run: `daphne -b 0.0.0.0 -p 5000 car_wash_pro.asgi:application`
- Note: For production, upgrade InMemoryChannelLayer to Redis for multi-instance WebSocket support
