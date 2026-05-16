"""
Checkatrade scraper service.
Collects plumber (and other trade) listings from Checkatrade public search.
Returns name, phone, website, city — no API key required.
"""
import requests
import logging
import re
from datetime import datetime
from sqlalchemy.orm import Session
from models import Plumber

logger = logging.getLogger(__name__)

CHECKATRADE_SEARCH_URL = "https://search.checkatrade.com/api/v2/search"

CITIES = [
    "London", "Birmingham", "Manchester", "Bristol", "Leicester",
    "Sheffield", "Newcastle", "Nottingham", "Leeds", "Liverpool",
    "Glasgow", "Edinburgh", "Cardiff", "Brighton", "Southampton",
    "Coventry", "Oxford", "Cambridge", "Norwich", "Exeter",
]

TRADE_CATEGORIES = {
    "plumber": "plumber",
    "electrician": "electrician",
    "gas_engineer": "gas-engineer",
    "hvac": "heating-engineer",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.checkatrade.com/",
}


def _clean_phone(phone: str) -> str | None:
    if not phone:
        return None
    cleaned = re.sub(r"[^\d+]", "", phone)
    if len(cleaned) < 10:
        return None
    if cleaned.startswith("0"):
        return "+44" + cleaned[1:]
    if not cleaned.startswith("+"):
        return "+44" + cleaned
    return cleaned


def _extract_city(location: str) -> str:
    if not location:
        return "London"
    location_lower = location.lower()
    for city in CITIES:
        if city.lower() in location_lower:
            return city
    return location.split(",")[0].strip() if "," in location else location.strip()


def collect_checkatrade(
    db: Session,
    trade: str = "plumber",
    cities: list = None,
    max_per_city: int = 50,
) -> dict:
    """
    Collect trade listings from Checkatrade for given cities.
    Saves new records to Plumber table.
    """
    if cities is None:
        cities = CITIES

    trade_param = TRADE_CATEGORIES.get(trade, trade)
    inserted = 0
    skipped = 0
    total_checked = 0

    for city in cities:
        page = 1
        city_count = 0

        while city_count < max_per_city:
            try:
                params = {
                    "q": trade_param,
                    "location": city,
                    "page": page,
                    "pageSize": 20,
                }

                resp = requests.get(
                    CHECKATRADE_SEARCH_URL,
                    params=params,
                    headers=HEADERS,
                    timeout=15,
                )

                if resp.status_code == 403:
                    logger.warning(f"Checkatrade blocked for {city} — stopping")
                    break

                if resp.status_code != 200:
                    logger.error(f"Checkatrade error {resp.status_code} for {city}")
                    break

                data = resp.json()
                members = data.get("members", []) or data.get("results", []) or data.get("data", [])

                if not members:
                    break

                for member in members:
                    total_checked += 1
                    city_count += 1

                    name = (
                        member.get("name") or
                        member.get("tradeName") or
                        member.get("company_name") or ""
                    ).strip()

                    if not name:
                        skipped += 1
                        continue

                    phone_raw = (
                        member.get("phone") or
                        member.get("telephone") or
                        member.get("contact_number") or ""
                    )
                    phone = _clean_phone(phone_raw)

                    website = (
                        member.get("website") or
                        member.get("websiteUrl") or ""
                    ).strip() or None

                    location = (
                        member.get("location") or
                        member.get("address") or
                        member.get("town") or
                        city
                    )
                    detected_city = _extract_city(str(location))

                    postcode = (member.get("postcode") or "").strip().upper() or None
                    address = (member.get("address") or str(location)).strip()

                    member_id = str(
                        member.get("id") or
                        member.get("memberId") or
                        member.get("slug") or
                        name
                    )

                    # Check for duplicates by name + city
                    existing = db.query(Plumber).filter(
                        Plumber.name == name,
                        Plumber.city == detected_city,
                    ).first()

                    if existing:
                        # Update phone/website if we have better data
                        updated = False
                        if phone and not existing.phone:
                            existing.phone = phone
                            updated = True
                        if website and not existing.website:
                            existing.website = website
                            updated = True
                        if updated:
                            existing.updated_at = datetime.utcnow()
                        skipped += 1
                        continue

                    plumber = Plumber(
                        name=name,
                        phone=phone,
                        website=website,
                        address=address[:500] if address else None,
                        postcode=postcode,
                        city=detected_city,
                        source="checkatrade",
                        category=trade,
                        is_commercial=1,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(plumber)
                    inserted += 1

                db.commit()

                # Check if there are more pages
                total = data.get("total") or data.get("totalResults") or 0
                if city_count >= total or len(members) < 20:
                    break

                page += 1

            except Exception as e:
                logger.error(f"Checkatrade error for {city}: {e}")
                break

    return {
        "success": True,
        "source": "checkatrade",
        "trade": trade,
        "inserted": inserted,
        "skipped": skipped,
        "total_checked": total_checked,
    }