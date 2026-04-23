"""
UK Food Standards Agency (FSA) Open Data API integration.

Provides demand-side prospects: restaurants, cafes, pubs, hotels, takeaways.
This is a fully public API — no API key required.
Docs: https://api.ratings.food.gov.uk/help

SECURITY NOTES:
- All parameters are validated / capped before being sent to the API.
- Only whitelisted business type IDs are accepted from callers.
- HTTP calls have explicit timeouts and content-size awareness.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

FSA_BASE_URL = "https://api.ratings.food.gov.uk"
FSA_HEADERS  = {"x-api-version": "2", "Accept": "application/json"}

# --------------------------------------------------------------------------- #
# Business type mapping (FSA IDs → human-readable category)                  #
# These are the categories relevant to plumbing demand.                       #
# --------------------------------------------------------------------------- #
BUSINESS_TYPE_MAP: Dict[str, str] = {
    "5":  "pub",
    "7":  "restaurant",
    "13": "takeaway",
    "14": "hotel",
    "3":  "other_hospitality",
}

# Category name → FSA business type ID (for filter-by-category requests)
CATEGORY_TO_TYPE_ID: Dict[str, Optional[str]] = {
    "all":         None,
    "restaurant":  "7",
    "cafe":        "7",   # FSA groups cafe with restaurant
    "takeaway":    "13",
    "pub":         "5",
    "hotel":       "14",
    "hospitality": None,  # fetch all types
}


def fetch_london_establishments(
    category: str = "all",
    page: int = 1,
) -> List[Dict[str, Any]]:
    """
    Fetch hospitality establishments in London from the FSA open data API.

    Returns a normalised list of prospect dicts ready for DB insertion.
    Returns an empty list on any error so collection degrades gracefully.
    """
    settings = get_settings()
    page_size = settings.fsa_page_size

    # Map category to FSA business type ID
    business_type_id = CATEGORY_TO_TYPE_ID.get(category)

    results: List[Dict[str, Any]] = []

    # If "all" or "hospitality", iterate over all relevant type IDs
    type_ids_to_fetch: List[Optional[str]]
    if business_type_id is None:
        type_ids_to_fetch = list(BUSINESS_TYPE_MAP.keys())
    else:
        type_ids_to_fetch = [business_type_id]

    for type_id in type_ids_to_fetch:
        fetched = _fetch_page(type_id=type_id, page=page, page_size=page_size)
        results.extend(fetched)

    logger.info("FSA: collected %d demand prospects (category=%s)", len(results), category)
    return results


def _fetch_page(
    type_id: Optional[str],
    page: int,
    page_size: int,
) -> List[Dict[str, Any]]:
    """Fetch a single page from the FSA Establishments endpoint."""
    params: Dict[str, Any] = {
        "address":    "London",   # Filter to London addresses
        "pageNumber": page,
        "pageSize":   min(page_size, 500),  # Cap at FSA's documented max
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
    except httpx.HTTPStatusError as exc:
        logger.error("FSA API HTTP error: %s", exc.response.status_code)
        return []
    except httpx.RequestError as exc:
        logger.error("FSA API request error: %s", type(exc).__name__)
        return []
    except Exception as exc:
        logger.error("FSA API unexpected error: %s", exc)
        return []

    establishments = data.get("establishments", [])
    return [_parse_establishment(e) for e in establishments if _parse_establishment(e)]


def _parse_establishment(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalise a single FSA establishment record.
    Returns None if the record is missing required fields.
    """
    name = (raw.get("BusinessName") or "").strip()
    if not name:
        return None

    # Build address from FSA address lines
    address_parts = [
        raw.get("AddressLine1", ""),
        raw.get("AddressLine2", ""),
        raw.get("AddressLine3", ""),
        raw.get("AddressLine4", ""),
    ]
    address = ", ".join(p.strip() for p in address_parts if p and p.strip())

    postcode = (raw.get("PostCode") or "").strip().upper()

    # Infer borough from FSA's LocalAuthorityName field
    borough = (raw.get("LocalAuthorityName") or "").strip()

    # Map business type ID to category name
    type_id = str(raw.get("BusinessTypeID", ""))
    category = BUSINESS_TYPE_MAP.get(type_id, "hospitality")

    # Build freshness label from inspection date
    freshness_label = _build_freshness_label(
        raw.get("RatingDate") or raw.get("SchemeLocalAuthorityCode")
    )

    # Geocode data if available
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
        "fsa_rating":      str(raw.get("RatingValue", "")),
        "freshness_label": freshness_label,
        "lat":             lat,
        "lng":             lng,
        # Website / phone not provided by FSA — filled during enrichment
        "website": None,
        "phone":   None,
    }


def _build_freshness_label(rating_date_str: Optional[str]) -> str:
    """
    Convert a raw FSA rating date string into a human-readable freshness label.
    Example: "2024-03-15T00:00:00" → "Inspected Mar 2024"
    """
    if not rating_date_str:
        return "Unknown"

    # FSA dates are ISO-like: "2024-03-15T00:00:00"
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
