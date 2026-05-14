"""
Contracts Finder service — collects live UK public sector tenders
for plumbing, maintenance and facilities management.
Free public API, no key required.
Tenders are real jobs worth £10k-£500k with named contacts.
"""
import requests
import logging
import re
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import DemandProspect

logger = logging.getLogger(__name__)

CONTRACTS_FINDER_URL = "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"

# Keywords that indicate plumbing/maintenance opportunity
PLUMBING_KEYWORDS = [
    "plumbing", "plumber", "drainage", "heating", "boiler",
    "mechanical", "hvac", "water", "gas engineer", "gas safe",
    "building services", "facilities management", "facilities maintenance",
    "property maintenance", "building maintenance", "M&E", "mechanical electrical",
    "hard FM", "hard facilities", "maintenance contract",
]

# Cities we cover
TARGET_CITIES = [
    "London", "Birmingham", "Manchester", "Bristol", "Leicester",
    "Sheffield", "Newcastle", "Nottingham", "Leeds", "Liverpool",
    "Glasgow", "Edinburgh", "Cardiff", "Brighton", "Southampton",
    "Coventry", "Oxford", "Cambridge",
]


def _is_relevant(title: str, description: str) -> bool:
    text = f"{title} {description}".lower()
    return any(kw.lower() in text for kw in PLUMBING_KEYWORDS)


def _extract_city(text: str) -> str:
    text_lower = text.lower()
    for city in TARGET_CITIES:
        if city.lower() in text_lower:
            return city
    return "London"


def _extract_contact_email(release: dict) -> str | None:
    """Extract contact email from tender release."""
    parties = release.get("parties", [])
    for party in parties:
        contact = party.get("contactPoint", {})
        email = contact.get("email", "")
        if email and "@" in email and "." in email:
            return email.lower().strip()
    return None


def _extract_contact_name(release: dict) -> str | None:
    parties = release.get("parties", [])
    for party in parties:
        contact = party.get("contactPoint", {})
        name = contact.get("name", "")
        if name:
            return name.strip()
    return None


def _extract_value(release: dict) -> int:
    try:
        tender = release.get("tender", {})
        value = tender.get("value", {})
        amount = value.get("amount", 0)
        return int(amount) if amount else 0
    except Exception:
        return 0


def _extract_deadline(release: dict) -> str | None:
    try:
        tender = release.get("tender", {})
        period = tender.get("tenderPeriod", {})
        end_date = period.get("endDate", "")
        if end_date:
            return end_date[:10]  # YYYY-MM-DD
    except Exception:
        pass
    return None


def _extract_buyer_name(release: dict) -> str:
    parties = release.get("parties", [])
    for party in parties:
        roles = party.get("roles", [])
        if "buyer" in roles or "procuringEntity" in roles:
            return party.get("name", "Unknown Buyer")
    return "UK Public Sector"


def _extract_address(release: dict) -> str:
    parties = release.get("parties", [])
    for party in parties:
        roles = party.get("roles", [])
        if "buyer" in roles or "procuringEntity" in roles:
            addr = party.get("address", {})
            parts = [
                addr.get("streetAddress", ""),
                addr.get("locality", ""),
                addr.get("postalCode", ""),
            ]
            return ", ".join(p for p in parts if p)
    return ""


def collect_contracts_finder(db: Session, days_back: int = 2, limit: int = 100) -> dict:
    """
    Fetch recent plumbing/maintenance tenders from Contracts Finder.
    Stores them as high-priority DemandProspects.
    """
    published_from = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")
    published_to = datetime.utcnow().strftime("%Y-%m-%dT23:59:59")

    inserted = 0
    skipped = 0
    cursor = None
    total_checked = 0

    while total_checked < limit:
        params = {
            "publishedFrom": published_from,
            "publishedTo": published_to,
            "stages": "tender",
            "limit": 100,
        }
        if cursor:
            params["cursor"] = cursor

        try:
            resp = requests.get(
                CONTRACTS_FINDER_URL,
                params=params,
                timeout=30,
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 403:
                logger.warning("Contracts Finder rate limit hit — stopping")
                break
            if resp.status_code != 200:
                logger.error(f"Contracts Finder error: {resp.status_code}")
                break

            data = resp.json()
            releases = data.get("releases", [])

            if not releases:
                break

            for release in releases:
                total_checked += 1

                tender = release.get("tender", {})
                title = tender.get("title", "") or ""
                description = tender.get("description", "") or ""

                # Skip if not relevant to plumbing/maintenance
                if not _is_relevant(title, description):
                    skipped += 1
                    continue

                ocid = release.get("ocid", "")
                if not ocid:
                    skipped += 1
                    continue

                # Check if already in DB
                existing = db.query(DemandProspect).filter(
                    DemandProspect.source_record_id == ocid
                ).first()
                if existing:
                    skipped += 1
                    continue

                # Extract data
                buyer_name = _extract_buyer_name(release)
                address = _extract_address(release)
                city = _extract_city(f"{title} {description} {address}")
                contact_email = _extract_contact_email(release)
                contact_name = _extract_contact_name(release)
                value = _extract_value(release)
                deadline = _extract_deadline(release)

                # Build description for score_breakdown
                value_str = f"£{value:,}" if value else "Value TBC"
                deadline_str = f"Deadline: {deadline}" if deadline else ""
                breakdown = f"contracts_finder | {value_str} | {deadline_str} | Contact: {contact_name or 'See tender'}"

                # Score based on value
                if value >= 100000:
                    score = 95
                elif value >= 50000:
                    score = 85
                elif value >= 20000:
                    score = 75
                elif value >= 10000:
                    score = 65
                else:
                    score = 55

                prospect = DemandProspect(
                    name=title[:255] if title else buyer_name,
                    category="tender",
                    address=address[:500] if address else "",
                    city=city,
                    email=contact_email,
                    source="contracts_finder",
                    source_record_id=ocid,
                    demand_score=score,
                    score_breakdown=breakdown[:500],
                    status="enriched" if contact_email else "new",
                    is_high_priority=1,
                    website=f"https://www.contractsfinder.service.gov.uk/Notice/{ocid.split('-')[-1]}" if ocid else None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(prospect)
                inserted += 1

            db.commit()

            # Pagination
            cursor = data.get("cursor")
            if not cursor or len(releases) < 100:
                break

        except Exception as e:
            logger.error(f"Contracts Finder collection error: {e}")
            break

    return {
        "success": True,
        "source": "contracts_finder",
        "inserted": inserted,
        "skipped": skipped,
        "total_checked": total_checked,
    }