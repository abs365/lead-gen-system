"""
Google Places API integration — buyer-side (plumber) collection.

SECURITY NOTES:
- API key is loaded from environment only; never logged or returned to callers.
- place_id is validated with a strict regex before use in Detail calls.
- All HTTP calls have explicit timeouts.
- We only request the minimum field mask needed (least-privilege API usage).
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional

import httpx

import os

class _Settings:
    google_api_key = os.getenv("GOOGLE_API_KEY")
    max_places_pages = 3

def get_settings():
    return _Settings()

class _Settings:
    google_api_key = os.getenv("GOOGLE_API_KEY")
    max_places_pages = 3

def get_settings():
    return _Settings()

logger = logging.getLogger(__name__)

# Google Places legacy Text Search endpoint
_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
# Google Places legacy Details endpoint
_DETAILS_URL     = "https://maps.googleapis.com/maps/api/place/details/json"

# Regex to validate a Google place_id before sending it back to the API.
# Place IDs are alphanumeric + underscores/colons/hyphens only.
_PLACE_ID_RE = re.compile(r'^[A-Za-z0-9_:\-]+$')

# London borough names extracted from address_components
_LONDON_BOROUGHS = {
    "city of london", "barking and dagenham", "barnet", "bexley", "brent",
    "bromley", "camden", "croydon", "ealing", "enfield", "greenwich",
    "hackney", "hammersmith and fulham", "haringey", "harrow", "havering",
    "hillingdon", "hounslow", "islington", "kensington and chelsea",
    "kingston upon thames", "lambeth", "lewisham", "merton", "newham",
    "redbridge", "richmond upon thames", "southwark", "sutton", "tower hamlets",
    "waltham forest", "wandsworth", "westminster",
}


def search_plumbers(keyword: str) -> List[Dict[str, Any]]:
    """
    Run a Google Places Text Search for plumbing businesses in London.
    Returns a list of normalised place dicts (no API key fields included).

    Returns an empty list (rather than raising) if the API key is missing,
    so the system degrades gracefully during local development.
    """
    settings = get_settings()

    if not settings.google_api_key:
        logger.warning(
            "GOOGLE_API_KEY not configured — plumber collection skipped. "
            "Set GOOGLE_API_KEY in .env to enable."
        )
        return []

    results: List[Dict[str, Any]] = []
    next_page_token: Optional[str] = None

    for page_num in range(settings.max_places_pages):
        params: Dict[str, Any] = {
            "query":  keyword,
            "region": "gb",
            # SECURITY: API key is passed as a query param (Google requirement).
            # It is never echoed back in responses or logged.
            "key":    settings.google_api_key,
        }
        if next_page_token:
            params["pagetoken"] = next_page_token

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(_TEXT_SEARCH_URL, params=params)
                resp.raise_for_status()
                data: Dict[str, Any] = resp.json()
        except httpx.HTTPStatusError as exc:
            # Log status without including the URL (which contains the API key)
            logger.error("Google Places HTTP error: %s", exc.response.status_code)
            break
        except httpx.RequestError as exc:
            logger.error("Google Places request error: %s", type(exc).__name__)
            break

        api_status = data.get("status")
        if api_status == "ZERO_RESULTS":
            break
        if api_status != "OK":
            logger.error("Google Places API returned status: %s", api_status)
            break

        for place in data.get("results", []):
            parsed = _parse_text_result(place)
            if parsed:
                results.append(parsed)

        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break

        # Google requires a short delay before the next_page_token becomes active
        if page_num < settings.max_places_pages - 1:
            time.sleep(2)

    logger.info("Google Places: collected %d plumber records", len(results))
    return results


def fetch_place_details(place_id: str) -> Dict[str, Any]:
    """
    Fetch website and phone number for a single place via the Details API.
    Returns an empty dict if the API key is missing or the call fails.

    SECURITY: place_id is validated against a strict allowlist regex.
    """
    settings = get_settings()

    if not settings.google_api_key:
        return {}

    # Validate place_id before sending to the external API
    if not _PLACE_ID_RE.match(place_id):
        logger.warning("fetch_place_details: invalid place_id format, skipping")
        return {}

    params = {
        # Request only the fields we actually use (least-privilege field mask)
        "place_id": place_id,
        "fields":   "name,formatted_address,formatted_phone_number,website,geometry,address_components",
        "key":      settings.google_api_key,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(_DETAILS_URL, params=params)
            resp.raise_for_status()
            return resp.json().get("result", {})
    except (httpx.HTTPError, Exception) as exc:
        logger.error("Place details fetch failed: %s", type(exc).__name__)
        return {}


# --------------------------------------------------------------------------- #
# Private helpers                                                              #
# --------------------------------------------------------------------------- #

def _parse_text_result(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalise a single Google Places text-search result."""
    place_id = raw.get("place_id", "")
    name     = raw.get("name", "").strip()

    if not name:
        return None

    location = raw.get("geometry", {}).get("location", {})
    address  = raw.get("formatted_address", "")

    return {
        "place_id": place_id,
        "name":     name,
        "address":  address,
        "postcode": _extract_postcode(address),
        "borough":  _extract_borough_from_address(address),
        "lat":      location.get("lat"),
        "lng":      location.get("lng"),
        # Phone and website are only in Details — populated during enrichment
        "website":  None,
        "phone":    None,
    }


def _extract_postcode(address: str) -> str:
    """Extract a UK postcode from a free-text address string."""
    match = re.search(
        r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b',
        address,
        re.IGNORECASE,
    )
    return match.group(1).upper() if match else ""


def _extract_borough_from_address(address: str) -> str:
    """
    Best-effort extraction of a London borough name from a formatted address.
    Falls back to empty string if none of the known borough names match.
    """
    addr_lower = address.lower()
    for borough in _LONDON_BOROUGHS:
        if borough in addr_lower:
            return borough.title()
    return ""
