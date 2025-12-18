
from __future__ import annotations

"""
Airbnb integration note (important):
- Airbnb offers developer APIs for approved partners / host services programs.
- It is not a general public consumer inventory search API for everyone.

Docs portal: https://developer.airbnb.com/
API Terms: https://www.airbnb.com/help/article/3418

This module is a stub. Once you have approved access, implement the calls here.
"""

from dataclasses import dataclass
from typing import List
from .mock import StayListing

@dataclass
class AirbnbSearchRequest:
    query: str
    checkin: str
    checkout: str
    adults: int = 2


class AirbnbPartnerClient:
    def __init__(self, token: str):
        self.token = token

    def search_stays(self, req: AirbnbSearchRequest) -> List[StayListing]:
        return []
