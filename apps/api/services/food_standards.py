"""
UK Food Standards Agency (FSA) Open Data API integration.
Provides demand-side prospects: restaurants, cafes, pubs, hotels, takeaways.
Public API - no API key required.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

FSA_BASE_URL = "https://api.ratings.food.gov.uk"
FSA_HEADERS  = {"x-api-version": "2", "Accept": "application/json"}

BUSINESS_TYPE_MAP: Dict[str, str] = {
    "5":  "pub",
    "7":  "restaurant",
    "13": "takeaway",
    "14": "hotel",
    "3":  "other_hospitality",
}

TARGET_CITIES = [
    "London",
    "Birmingham",
    "Manchester",
    "Leeds",
    "Sheffield",
    "Bristol",
    "Liverpool",
    "Newcastle",
    "Nottingham",
    "Leicester",
]

def fetch_london_establishments(
    category: str = "all",
    page: int = 1,
    city: str = "London",
) -> List[Dict[str, Any]]:
    page_size = 100
    type_ids = list(BUSINESS_TYPE_MAP.keys())
    results: List[Dict[str, Any]] = []

    for type_id in type_ids:
        fetched = _fetch_page(type_id=type_id, page=page, page_size=page_size, city=city)
        results.extend(fetched)

    logger.info("FSA: collected %d prospects (city=%s)", len(results), city)
    return results


def fetch_all_cities(page: int = 1) -> List[Dict[str, Any]]:
    all_results = []
    for city in TARGET_CITIES:
        results = fetch_london_establishments(page=page, city=city)
        all_results.extend(results)
    return all_results


def _fetch_page(
    type_id: Optional[str],
    page: int,
    page_size: int,
    city: str = "London",
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "address":    city,
        "pageNumber": page,
        "pageSize":   min(page_size, 500),
    }
    if type_id:
        params["businessTypeId"] = type_id

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(
                f"{FSA_BASE_URL}/Establishments",
                params=params,
                headers=FSA_HEADERS,
            )
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()
    except Exception as exc:
        logger.error("FSA API error: %s", exc)
        return []

    establishments = data.get("establishments", [])
    parsed = []
    for e in establishments:
        p = _parse_establishment(e, city)
        if p:
            parsed.append(p)
    return parsed


def _parse_establishment(raw: Dict[str, Any], city: str = "London") -> Optional[Dict[str, Any]]:
    name = (raw.get("BusinessName") or "").strip()
    if not name:
        return None

    address_parts = [
        raw.get("AddressLine1", ""),
        raw.get("AddressLine2", ""),
        raw.get("AddressLine3", ""),
        raw.get("AddressLine4", ""),
    ]
    address = ", ".join(p.strip() for p in address_parts if p and p.strip())
    postcode = (raw.get("PostCode") or "").strip().upper()
    borough = (raw.get("LocalAuthorityName") or "").strip()
    type_id = str(raw.get("BusinessTypeID", ""))
    category = BUSINESS_TYPE_MAP.get(type_id, "hospitality")

    freshness_label = _build_freshness_label(raw.get("RatingDate"))

    geocode = raw.get("geocode") or {}
    try:
        lat = float(geocode.get("latitude") or 0) or None
        lng = float(geocode.get("longitude") or 0) or None
    except (ValueError, TypeError):
        lat, lng = None, None

    return {
        "fsa_establishment_id": str(raw.get("FHRSID", "")),
        "name":            name,
        "category":        category,
        "address":         address,
        "postcode":        postcode,
        "borough":         borough,
        "city":            city,
        "fsa_rating":      str(raw.get("RatingValue", "")),
        "freshness_label": freshness_label,
        "lat":             lat,
        "lng":             lng,
        "website":         None,
        "phone":           None,
    }


def _build_freshness_label(rating_date_str: Optional[str]) -> str:
    if not rating_date_str:
        return "Unknown"
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(rating_date_str[:19], fmt)
            months_ago = (
                (datetime.now(timezone.utc).year - dt.year) * 12
                + datetime.now(timezone.utc).month - dt.month
            )
            label = f"Inspected {dt.strftime('%b %Y')}"
            if months_ago <= 12:
                label += " (recent)"
            return label
        except (ValueError, IndexError):
            continue
    return "Unknown"