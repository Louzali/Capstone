
from __future__ import annotations

"""
Booking.com integration (compliant): Demand API (Affiliate Partners).

Official docs:
- Demand API: https://developers.booking.com/demand/docs/open-api/demand-api
- Availability endpoint example: https://developers.booking.com/demand/docs/open-api/demand-api/accommodations/accommodations/availability

This module is a minimal skeleton. Different partners have different access and preferred flows.
Implement your granted endpoints and map results into StayListing.
"""

from dataclasses import dataclass
from typing import List
import requests

from .mock import StayListing

@dataclass
class BookingSearchRequest:
    city: str
    checkin: str
    checkout: str
    adults: int = 2


class BookingDemandClient:
    def __init__(self, token: str, affiliate_id: str):
        self.token = token
        self.affiliate_id = affiliate_id
        self.base_url = "https://developers.booking.com/demand"  # docs base; your actual API host may differ by program

    def search_stays(self, req: BookingSearchRequest) -> List[StayListing]:
        # Placeholder: return empty until you implement your exact partner search flow.
        return []

    def _post(self, url: str, payload: dict) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "X-Affiliate-Id": self.affiliate_id,
        }
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()
