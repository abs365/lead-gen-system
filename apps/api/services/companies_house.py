import requests
from datetime import datetime
from sqlalchemy.orm import Session
from config import settings
from models import DemandProspect

CITIES = [
    "London",
    "Birmingham",
    "Manchester",
    "Bristol",
    "Leicester",
    "Sheffield",
    "Newcastle",
    "Nottingham",
    "Leeds",
    "Liverpool",
    "Oldham",
    "Bolton",
    "Coventry",
    "Solihull",
    "Stockport",
    "Wolverhampton",
    "Salford",
]

BUSINESS_TYPES = [
    "restaurant",
    "cafe",
    "takeaway",
    "hotel",
    "property maintenance",
    "facilities management",
    "landlord",
]

def _build_search_terms(cities: list, business_types: list) -> list:
    terms = []
    for city in cities:
        for btype in business_types:
            terms.append(f"{btype} {city}")
    return terms

def _score_company(title: str, description: str) -> int:
    text = f"{title} {description}".lower()
    score = 0
    if "restaurant" in text: score += 35
    if "cafe" in text or "coffee" in text: score += 30
    if "takeaway" in text: score += 30
    if "hotel" in text: score += 35
    if "property" in text: score += 25
    if "maintenance" in text: score += 25
    if "facilities" in text: score += 25
    return min(score, 100)

def _detect_city(address: str, title: str) -> str:
    text = f"{address} {title}".lower()
    for city in CITIES:
        if city.lower() in text:
            return city
    return "Unknown"

def collect_companies_house(db: Session, max_per_term: int = 10) -> dict:
    if not settings.COMPANIES_HOUSE_API_KEY: