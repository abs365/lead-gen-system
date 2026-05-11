import requests
from datetime import datetime
from sqlalchemy.orm import Session
from models import DemandProspect
import os

COMPANIES_HOUSE_API_KEY = os.getenv("COMPANIES_HOUSE_API_KEY")

CITIES = [
    "London", "Birmingham", "Manchester", "Bristol", "Leicester",
    "Sheffield", "Newcastle", "Nottingham", "Leeds", "Liverpool",
    "Oldham", "Bolton", "Coventry", "Solihull", "Stockport",
    "Wolverhampton", "Salford",
]

# Expanded business types — high plumbing need
BUSINESS_TYPES = [
    # Food & hospitality (original)
    "restaurant", "cafe", "takeaway", "hotel",
    # Property & facilities (original)
    "property maintenance", "facilities management", "landlord",
    # NEW — high commercial plumbing demand
    "care home", "nursing home", "residential home",
    "pub", "bar", "nightclub",
    "gym", "leisure centre", "sports centre",
    "school", "academy", "college",
    "office building", "commercial property",
    "serviced apartments", "guest house",
    "laundry", "laundrette",
    "car wash", "garage",
]


def _build_search_terms():
    terms = []
    for city in CITIES:
        for btype in BUSINESS_TYPES:
            terms.append((f"{btype} {city}", city))
    return terms


def _score_company(title: str, description: str) -> int:
    text = f"{title} {description}".lower()
    score = 0
    # High value
    if "hotel" in text: score += 40
    if "care home" in text or "nursing home" in text: score += 40
    if "gym" in text or "leisure" in text: score += 35
    if "school" in text or "academy" in text or "college" in text: score += 35
    # Medium value
    if "restaurant" in text: score += 30
    if "pub" in text or "bar" in text: score += 30
    if "cafe" in text or "coffee" in text: score += 25
    if "takeaway" in text: score += 25
    if "serviced apartment" in text or "guest house" in text: score += 30
    # Maintenance types
    if "property" in text: score += 20
    if "maintenance" in text: score += 20
    if "facilities" in text: score += 20
    if "office" in text or "commercial" in text: score += 20
    if "laundry" in text or "laundrette" in text: score += 15
    return min(score, 100)


def _detect_city(address: str, title: str) -> str:
    text = f"{address} {title}".lower()
    for city in CITIES:
        if city.lower() in text:
            return city
    return "Unknown"


def collect_companies_house(db: Session, max_per_term: int = 10) -> dict:
    if not COMPANIES_HOUSE_API_KEY:
        return {
            "success": False,
            "message": "Missing COMPANIES_HOUSE_API_KEY",
            "inserted": 0,
            "skipped": 0,
        }

    inserted = 0
    skipped = 0
    search_terms = _build_search_terms()

    for term, city_hint in search_terms:
        try:
            response = requests.get(
                "https://api.company-information.service.gov.uk/search/companies",
                auth=(COMPANIES_HOUSE_API_KEY, ""),
                params={"q": term, "items_per_page": max_per_term},
                timeout=30,
            )
        except Exception:
            continue

        if response.status_code != 200:
            continue

        items = response.json().get("items", [])

        for item in items:
            company_number = item.get("company_number")
            title = item.get("title")
            address = item.get("address_snippet", "")
            description = item.get("description", "")

            if not company_number or not title:
                skipped += 1
                continue

            existing = db.query(DemandProspect).filter(
                DemandProspect.source == "companies_house",
                DemandProspect.source_record_id == company_number,
            ).first()
            if existing:
                skipped += 1
                continue

            city = _detect_city(address, title)
            if city == "Unknown":
                city = city_hint

            score = _score_company(title, description)

            prospect = DemandProspect(
                name=title,
                category="companies_house",
                address=address,
                city=city,
                source="companies_house",
                source_record_id=company_number,
                demand_score=score,
                score_breakdown=f"companies_house_search:{term}",
                status="new",
                is_high_priority=1 if score >= 25 else 0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(prospect)
            inserted += 1

    db.commit()
    return {
        "success": True,
        "source": "companies_house",
        "inserted": inserted,
        "skipped": skipped,
    }