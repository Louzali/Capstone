
from __future__ import annotations
from pydantic import BaseModel
from typing import List

class StayListing(BaseModel):
    id: str
    platform: str  # booking | airbnb
    name: str
    area: str
    nightly_price: float
    rating: float
    reviews: int
    amenities: List[str]
    url: str
    distance_km_to_center: float
    room_type: str  # entire_place | private_room | shared_room | hotel_room

MOCK_LISTINGS: List[StayListing] = [
    StayListing(
        id="bkg-ifr-001",
        platform="booking",
        name="Ifrane Mountain Hotel (Mock)",
        area="City Center",
        nightly_price=65,
        rating=8.4,
        reviews=780,
        amenities=["wifi", "heating", "parking"],
        url="https://example.com/booking/bkg-ifr-001",
        distance_km_to_center=0.6,
        room_type="hotel_room",
    ),
    StayListing(
        id="bkg-ifr-002",
        platform="booking",
        name="Cozy Chalet Near Cedar Forest (Mock)",
        area="Outskirts",
        nightly_price=92,
        rating=8.9,
        reviews=214,
        amenities=["wifi", "kitchen", "heating", "parking"],
        url="https://example.com/booking/bkg-ifr-002",
        distance_km_to_center=3.2,
        room_type="entire_place",
    ),
    StayListing(
        id="bnb-ifr-101",
        platform="airbnb",
        name="Private Room w/ Fireplace (Mock)",
        area="City Center",
        nightly_price=45,
        rating=4.78,
        reviews=133,
        amenities=["wifi", "heating"],
        url="https://example.com/airbnb/bnb-ifr-101",
        distance_km_to_center=0.9,
        room_type="private_room",
    ),
    StayListing(
        id="bnb-ifr-102",
        platform="airbnb",
        name="Family Apartment (Mock)",
        area="City Center",
        nightly_price=72,
        rating=4.86,
        reviews=89,
        amenities=["wifi", "kitchen", "heating"],
        url="https://example.com/airbnb/bnb-ifr-102",
        distance_km_to_center=1.1,
        room_type="entire_place",
    ),
]
