# AI Trip Planner MVP – Ifrane (API-ready)

## What changed vs the first MVP
- Default destination: **Ifrane, Morocco**
- Mock stays updated to Ifrane-themed listings
- Added provider stubs for:
  - Booking.com **Demand API** (affiliate/partner) integration
  - Airbnb **Partner API** (approved access) stub
- Automatic fallback to mock data if keys are not set

## Run locally (Windows)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Open: http://127.0.0.1:8000

## Enable real providers
Copy `.env.example` to `.env` and fill keys.

### Booking.com (Demand API)
You need affiliate/partner credentials (affiliate id + token).

### Airbnb
Airbnb’s APIs are generally for approved partners / host services programs (not an open public inventory search API).
This project includes a stub (`providers/airbnb_partner.py`) you can wire once you have access.

## WordPress
- Fastest: deploy this backend and embed the homepage with an iframe.
- Native: set `WP_ORIGIN` and call `/api/plan` and `/api/stays` from WordPress with JS.
