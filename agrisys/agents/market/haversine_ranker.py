"""Haversine geodesic distance calculation and net realization APMC mandi ranker."""

from __future__ import annotations
import math
from typing import Dict, List, Tuple
from agrisys.agents.market.models import MandiRecord

# Reference Registry of Major Indian Agricultural APMC Mandis
# Format: mandi_id -> {name, district, state, lat, lon}
MANDI_DIRECTORY: list[dict[str, Any]] = [
    {"name": "Lucknow APMC (Sitapur Road)", "district": "Lucknow", "state": "Uttar Pradesh", "lat": 26.8900, "lon": 80.9300},
    {"name": "Barabanki Mandi", "district": "Barabanki", "state": "Uttar Pradesh", "lat": 26.9270, "lon": 81.1834},
    {"name": "Kanpur APMC (Naubasta)", "district": "Kanpur Nagar", "state": "Uttar Pradesh", "lat": 26.4100, "lon": 80.3300},
    {"name": "Varanasi APMC (Raja Ka Talab)", "district": "Varanasi", "state": "Uttar Pradesh", "lat": 25.3176, "lon": 82.9739},
    {"name": "Agra APMC", "district": "Agra", "state": "Uttar Pradesh", "lat": 27.1767, "lon": 78.0081},
    {"name": "Khanna Grain Market", "district": "Ludhiana", "state": "Punjab", "lat": 30.7020, "lon": 76.2160},
    {"name": "Ludhiana APMC", "district": "Ludhiana", "state": "Punjab", "lat": 30.9010, "lon": 75.8573},
    {"name": "Karnal Mandi", "district": "Karnal", "state": "Haryana", "lat": 29.6857, "lon": 76.9905},
    {"name": "Indore APMC (Choithram)", "district": "Indore", "state": "Madhya Pradesh", "lat": 22.6800, "lon": 75.8500},
    {"name": "Bhopal APMC (Karond)", "district": "Bhopal", "state": "Madhya Pradesh", "lat": 23.3000, "lon": 77.4100},
    {"name": "Lasalgaon Mandi", "district": "Nashik", "state": "Maharashtra", "lat": 20.1450, "lon": 74.2300},
    {"name": "Pune APMC (Gultekdi)", "district": "Pune", "state": "Maharashtra", "lat": 18.4900, "lon": 73.8600},
    {"name": "Vashi APMC Navi Mumbai", "district": "Thane", "state": "Maharashtra", "lat": 19.0760, "lon": 73.0030},
    {"name": "Guntur Mirchi Yard", "district": "Guntur", "state": "Andhra Pradesh", "lat": 16.3067, "lon": 80.4365},
    {"name": "Hubli APMC", "district": "Dharwad", "state": "Karnataka", "lat": 15.3647, "lon": 75.1240},
]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates great-circle distance between two geographic coordinates in kilometers.
    """
    R = 6371.0  # Earth's radius in kilometers
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2) + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


class HaversineMandiRanker:
    """Ranks regional APMC mandis by net farmer profit realization factoring in distance and freight."""

    def __init__(self, freight_per_quintal_km: float = 0.25):
        """
        Default transport freight: ₹0.25 / quintal / km (equivalent to ~₹2.50 / tonne / km
        in medium commercial vehicles / pickups).
        """
        self.freight_rate = freight_per_quintal_km

    def rank_mandis(
        self,
        origin_lat: float,
        origin_lon: float,
        commodity: str,
        price_lookup: dict[str, float] | None = None,
        top_k: int = 5,
    ) -> list[MandiRecord]:
        """
        Computes distances, estimates freight deductions, and ranks candidate mandis by
        descending net realization price.
        """
        candidates: list[MandiRecord] = []
        base_prices = price_lookup or {}

        for entry in MANDI_DIRECTORY:
            dist = haversine_distance(origin_lat, origin_lon, entry["lat"], entry["lon"])

            # Retrieve or synthesize realistic commodity price at this mandi
            mandi_key = entry["name"]
            if mandi_key in base_prices:
                modal = float(base_prices[mandi_key])
            else:
                # Baseline variation based on distance & commodity
                comm_lower = commodity.lower()
                if "tomato" in comm_lower:
                    base = 1800.0  # ₹18/kg
                elif "wheat" in comm_lower:
                    base = 2350.0
                elif "paddy" in comm_lower or "rice" in comm_lower:
                    base = 2400.0
                elif "potato" in comm_lower or "onion" in comm_lower:
                    base = 1600.0
                else:
                    base = 2500.0

                # Slight localized price spread (±8%)
                spread = ((hash(mandi_key + commodity) % 17) - 8) * 15.0
                modal = max(500.0, base + spread)

            transport_cost = round(dist * self.freight_rate, 2)
            net_realization = round(modal - transport_cost, 2)

            candidates.append(
                MandiRecord(
                    mandi_name=entry["name"],
                    district=entry["district"],
                    state=entry["state"],
                    commodity=commodity,
                    arrival_date="2026-09-14",
                    min_price=round(modal * 0.90, 2),
                    max_price=round(modal * 1.12, 2),
                    modal_price=round(modal, 2),
                    latitude=entry["lat"],
                    longitude=entry["lon"],
                    distance_km=dist,
                    estimated_transport_cost=transport_cost,
                    net_realization_price=net_realization,
                )
            )

        # Rank by net realization price descending (highest profit after logistics first)
        candidates.sort(key=lambda m: m.net_realization_price, reverse=True)
        return candidates[:top_k]
