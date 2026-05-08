import os
import re
import time
import logging
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from models import Plumber

logger = logging.getLogger(__name__)

PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

BAD_EMAIL_PATTERNS = [
    "example.", "test.", "placeholder", "yourname", "yourdomain",
    "domain.com", "email.com", "noreply", "no-reply", "none",
    "info@info", "admin@admin",
]

SKIP_DOMAINS = [
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
    "youtube.com", "google.com", "yell.com", "checkatrade.com",
    "mybuilder.com", "trustatrader.com", "ratedpeople.com", "tiktok.com",
]


def derive_email_from_website(website: str):
    if not website:
        return None
    try:
        parsed = urlparse(website)
        domain = parsed.netloc.lower().lstrip("www.")
        if not domain or "." not in domain:
            return None
        if any(s in domain for s in SKIP_DOMAINS):
            return None
        return f"info@{domain}"
    except Exception:
        return None


def is_valid_email(email: str) -> bool:
    if not email or "@" not in email:
        return False
    local, domain = email.split("@", 1)
    if not local or "." not in domain:
        return False
    if any(p in email.lower() for p in BAD_EMAIL_PATTERNS):
        return False
    if re.search(r'\d', domain):
        return False
    return True


def get_place_details(api_key: str, place_id: str) -> dict:
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(PLACES_DETAILS_URL, params={
                "place_id": place_id,
                "fields": "website,formatted_phone_number,business_status",
                "key": api_key,
            })
            return resp.json().get("result", {})
    except Exception as e:
        logger.error(f"Places details error for {place_id}: {e}")
        return {}


def collect_plumber_emails(db: Session, limit: int = 100) -> dict:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        return {"success": False, "error": "GOOGLE_API_KEY not set"}

    plumbers = (
        db.query(Plumber)
        .filter(Plumber.email == None)
        .filter(Plumber.place_id != None)
        .limit(limit)
        .all()
    )

    updated = 0
    skipped = 0
    errors = 0

    for plumber in plumbers:
        try:
            details = get_place_details(GOOGLE_API_KEY, plumber.place_id)

            if details.get("business_status") == "CLOSED_PERMANENTLY":
                skipped += 1
                continue

            website = details.get("website") or plumber.website
            phone = details.get("formatted_phone_number")

            email = derive_email_from_website(website)

            if not email or not is_valid_email(email):
                skipped += 1
                continue

            plumber.email = email
            if phone and not plumber.phone:
                plumber.phone = phone
            if website and not plumber.website:
                plumber.website = website

            db.commit()
            updated += 1
            logger.info(f"Updated {plumber.name} -> {email}")

            time.sleep(0.3)

        except Exception as e:
            logger.error(f"Error processing plumber {plumber.id}: {e}")
            db.rollback()
            errors += 1
            continue

    return {
        "success": True,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "message": f"Updated {updated} plumber emails from Google Places"
    }