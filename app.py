
from __future__ import annotations

import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Tuple
import math
import datetime as dt

from providers.booking_demand import BookingDemandClient, BookingSearchRequest
from providers.airbnb_partner import AirbnbPartnerClient, AirbnbSearchRequest
from providers.mock import MOCK_LISTINGS, StayListing

app = FastAPI(title="AI Trip Planner MVP (Ifrane)", version="0.2.0")

# If you want WordPress (different domain) to call your API directly (no iframe), enable CORS:
# Set WP_ORIGIN to your WordPress site URL, e.g. https://your-site.com
wp_origin = os.getenv("WP_ORIGIN")
if wp_origin:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[wp_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


class TripInput(BaseModel):
    destination: str = Field("Ifrane, Morocco")
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    travelers: int = Field(1, ge=1, le=20)
    nightly_budget: float = Field(..., ge=10, description="Budget per night")
    style: str = Field("balanced", description="relaxed | packed | foodie | culture | nightlife | balanced")
    must_haves: List[str] = Field(default_factory=list)
    dealbreakers: List[str] = Field(default_factory=list)
    prefer_areas: List[str] = Field(default_factory=list)


class ItineraryDay(BaseModel):
    date: str
    morning: str
    afternoon: str
    evening: str
    est_cost: float


class ItineraryResponse(BaseModel):
    destination: str
    days: List[ItineraryDay]
    total_est_cost: float
    notes: List[str]


class StayRecommendation(BaseModel):
    listing: StayListing
    match_score: float
    why: List[str]
    est_total_price: float


class StaysResponse(BaseModel):
    destination: str
    nights: int
    currency_note: str
    recommendations: List[StayRecommendation]


def parse_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def nights_between(start: str, end: str) -> int:
    a = parse_date(start)
    b = parse_date(end)
    return max(1, (b - a).days)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def normalize_rating(platform: str, rating: float) -> float:
    return clamp(rating / (10.0 if platform == "booking" else 5.0), 0.0, 1.0)


def budget_fit_score(nightly_price: float, nightly_budget: float) -> float:
    if nightly_price <= nightly_budget:
        return clamp(0.85 + 0.15 * (1 - (nightly_price / max(nightly_budget, 1e-6))), 0.0, 1.0)
    over = (nightly_price - nightly_budget) / max(nightly_budget, 1e-6)
    return clamp(1.0 - 1.4 * over, 0.0, 1.0)


def location_score(distance_km: float) -> float:
    return clamp(1.0 / (1.0 + 0.35 * distance_km), 0.0, 1.0)


def quality_score(platform: str, rating: float, reviews: int) -> float:
    r = normalize_rating(platform, rating)
    conf = clamp(math.log10(max(reviews, 1)) / 3.0, 0.0, 1.0)
    return clamp(0.75 * r + 0.25 * conf, 0.0, 1.0)


def amenities_score(listing_amenities: List[str], must_haves: List[str]) -> float:
    if not must_haves:
        return 0.7
    have = set(a.lower() for a in listing_amenities)
    need = [m.lower() for m in must_haves]
    hit = sum(1 for m in need if m in have)
    return clamp(hit / max(len(need), 1), 0.0, 1.0)


def dealbreaker_ok(room_type: str, dealbreakers: List[str]) -> bool:
    db = set(d.lower() for d in dealbreakers)
    if "shared_room" in db and room_type == "shared_room":
        return False
    if "private_room" in db and room_type == "private_room":
        return False
    return True


def area_bonus(area: str, prefer_areas: List[str]) -> float:
    if not prefer_areas:
        return 0.0
    p = [x.lower() for x in prefer_areas]
    return 0.12 if area.lower() in p else 0.0


def score_listing(l: StayListing, trip: TripInput) -> Tuple[float, Dict[str, float]]:
    b = budget_fit_score(l.nightly_price, trip.nightly_budget)
    q = quality_score(l.platform, l.rating, l.reviews)
    loc = location_score(l.distance_km_to_center)
    a = amenities_score(l.amenities, trip.must_haves)
    base = 0.40 * b + 0.25 * q + 0.20 * loc + 0.15 * a
    base = clamp(base + area_bonus(l.area, trip.prefer_areas), 0.0, 1.0)
    return base * 100.0, {"budget": b, "quality": q, "location": loc, "amenities": a}


def explain_listing(l: StayListing, trip: TripInput, parts: Dict[str, float]) -> List[str]:
    why: List[str] = []
    if l.nightly_price <= trip.nightly_budget:
        why.append(f"Within your nightly budget ({l.nightly_price:.0f} ≤ {trip.nightly_budget:.0f}).")
    else:
        why.append(f"Over budget by {l.nightly_price - trip.nightly_budget:.0f} per night (stretch option).")

    if parts["quality"] >= 0.8:
        why.append(f"Strong quality signals (rating {l.rating} with {l.reviews} reviews).")
    elif l.reviews < 50:
        why.append("Fewer reviews than ideal—treat this option with a bit more caution.")
    else:
        why.append(f"Solid rating ({l.rating}) and review count ({l.reviews}).")

    if parts["location"] >= 0.6:
        why.append(f"Convenient location (~{l.distance_km_to_center:.1f} km to center).")
    else:
        why.append(f"Farther from the center (~{l.distance_km_to_center:.1f} km)—better if you have transport.")

    if trip.must_haves:
        missing = [m for m in trip.must_haves if m.lower() not in set(x.lower() for x in l.amenities)]
        if not missing:
            why.append("Meets all your must-have amenities.")
        else:
            why.append(f"Missing: {', '.join(missing)}.")
    return why


def generate_itinerary(trip: TripInput) -> ItineraryResponse:
    start = parse_date(trip.start_date)
    end = parse_date(trip.end_date)
    n_days = max(1, (end - start).days)

    style = trip.style.lower().strip()
    morning_opts = {
        "relaxed": "Slow breakfast + cedar forest walk",
        "packed": "Early start: viewpoints + town highlights",
        "foodie": "Local café + pastry stop",
        "culture": "Azrou day trip idea + cedar forest history",
        "nightlife": "Café hopping + evening stroll",
        "balanced": "Town center walk + scenic stop",
    }
    afternoon_opts = {
        "relaxed": "Lakeside chill time + coffee",
        "packed": "Outdoor activity (hike / excursion)",
        "foodie": "Try local tagine + tea time",
        "culture": "Local crafts + heritage walk",
        "nightlife": "Rooftop lunch + downtime",
        "balanced": "Lunch + one planned activity",
    }
    evening_opts = {
        "relaxed": "Sunset viewpoint + easy dinner",
        "packed": "Dinner + night walk loop",
        "foodie": "Dinner + dessert tasting",
        "culture": "Traditional dinner + mint tea",
        "nightlife": "Lounge/café + late tea",
        "balanced": "Dinner + optional stroll",
    }

    base_pp = {
        "relaxed": 30,
        "packed": 50,
        "foodie": 55,
        "culture": 45,
        "nightlife": 55,
        "balanced": 40,
    }.get(style, 40)

    notes = [
        "MVP itinerary is heuristic (no live attraction data yet).",
        "Add maps + opening hours later for a production version.",
    ]

    days: List[ItineraryDay] = []
    for i in range(n_days):
        d = start + dt.timedelta(days=i)
        bump = (i % 3) * 3
        est = (base_pp + bump) * trip.travelers
        days.append(ItineraryDay(
            date=d.isoformat(),
            morning=morning_opts.get(style, morning_opts["balanced"]),
            afternoon=afternoon_opts.get(style, afternoon_opts["balanced"]),
            evening=evening_opts.get(style, evening_opts["balanced"]),
            est_cost=float(round(est, 2)),
        ))
    total = round(sum(x.est_cost for x in days), 2)
    return ItineraryResponse(destination=trip.destination, days=days, total_est_cost=total, notes=notes)


def fetch_listings(trip: TripInput) -> List[StayListing]:
    booking_token = os.getenv("BOOKING_DEMAND_TOKEN")
    booking_affiliate_id = os.getenv("BOOKING_AFFILIATE_ID")
    booking_listings: List[StayListing] = []
    if booking_token and booking_affiliate_id:
        client = BookingDemandClient(token=booking_token, affiliate_id=booking_affiliate_id)
        booking_listings = client.search_stays(BookingSearchRequest(
            city=trip.destination,
            checkin=trip.start_date,
            checkout=trip.end_date,
            adults=trip.travelers,
        ))

    airbnb_token = os.getenv("AIRBNB_PARTNER_TOKEN")
    airbnb_listings: List[StayListing] = []
    if airbnb_token:
        aclient = AirbnbPartnerClient(token=airbnb_token)
        airbnb_listings = aclient.search_stays(AirbnbSearchRequest(
            query=trip.destination,
            checkin=trip.start_date,
            checkout=trip.end_date,
            adults=trip.travelers,
        ))

    combined = booking_listings + airbnb_listings
    return combined if combined else MOCK_LISTINGS


def recommend_stays(trip: TripInput) -> StaysResponse:
    n = nights_between(trip.start_date, trip.end_date)
    listings = [l for l in fetch_listings(trip) if dealbreaker_ok(l.room_type, trip.dealbreakers)]

    scored = []
    for l in listings:
        score, parts = score_listing(l, trip)
        scored.append((score, l, parts))
    scored.sort(key=lambda x: x[0], reverse=True)

    recs: List[StayRecommendation] = []
    for score, l, parts in scored[:10]:
        recs.append(StayRecommendation(
            listing=l,
            match_score=float(round(score, 1)),
            why=explain_listing(l, trip, parts),
            est_total_price=float(round(l.nightly_price * n, 2)),
        ))

    return StaysResponse(
        destination=trip.destination,
        nights=n,
        currency_note="Set keys in .env to use Booking Demand API / Airbnb partner stub; otherwise mock data.",
        recommendations=recs,
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/plan", response_model=ItineraryResponse)
def api_plan(payload: TripInput):
    return generate_itinerary(payload)


@app.post("/api/stays", response_model=StaysResponse)
def api_stays(payload: TripInput):
    return recommend_stays(payload)


@app.get("/health")
def health():
    return {"ok": True, "version": app.version}
