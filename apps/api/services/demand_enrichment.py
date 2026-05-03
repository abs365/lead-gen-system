import re
import requests
from datetime import datetime
from sqlalchemy.orm import Session

from config import settings
from models import DemandProspect, OutreachLog


EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"


def _estimate_value(prospect: DemandProspect) -> int:
    text = f"{prospect.name or ''} {prospect.category or ''}".lower()

    if "hotel" in text:
        return 500
    if "restaurant" in text:
        return 300
    if "cafe" in text or "takeaway" in text:
        return 250
    if "property" in text or "facilities" in text or "maintenance" in text:
        return 400

    return 150


def _is_valid_email(email: str) -> bool:
    """
    Returns True only if the email looks like a real business address.
    Rejects npm package names, versioned domains, known junk patterns.
    """
    if not email or "@" not in email:
        return False

    email = email.lower().strip()
    local, domain = email.rsplit("@", 1)

    # Must have a dot in domain
    if "." not in domain:
        return False

    tld = domain.split(".")[-1]

    # Reject TLDs that are version numbers e.g. .10, .4, .2
    if tld.isdigit():
        return False

    # Reject domains that look like versioned npm packages e.g. 4.4.4, 11.7.10
    version_pattern = re.compile(r"^\d+\.\d+(\.\d+)?$")
    if version_pattern.match(domain):
        return False

    # Reject domains starting with digits
    if domain[0].isdigit():
        return False

    # Reject known junk keywords
    junk_keywords = [
        "example", "test@", "noreply", "no-reply", "user@",
        "flatpickr", "intl-", "simple-line", "node_modules",
        "webpack", "babel", "jquery", "lodash", "moment",
        "bootstrap", "fontawesome", "animate", "leaflet",
    ]
    for kw in junk_keywords:
        if kw in email:
            return False

    # Reject if local part looks like a package name (contains digits mixed with dashes)
    if re.search(r"\d+\.\d+", local):
        return False

    # Domain must have valid TLD (at least 2 chars, all alpha)
    if len(tld) < 2 or not tld.isalpha():
        return False

    return True


def _find_google_place(prospect: DemandProspect) -> dict | None:
    if not settings.GOOGLE_API_KEY:
        return None

    query = f"{prospect.name} {prospect.city or 'London'}"

    response = requests.get(
        "https://maps.googleapis.com/maps/api/place/textsearch/json",
        params={"query": query, "key": settings.GOOGLE_API_KEY},
        timeout=20,
    )

    if response.status_code != 200:
        return None

    results = response.json().get("results", [])
    return results[0] if results else None


def _get_place_details(place_id: str) -> dict:
    response = requests.get(
        "https://maps.googleapis.com/maps/api/place/details/json",
        params={
            "place_id": place_id,
            "fields": "name,website,formatted_phone_number,formatted_address",
            "key": settings.GOOGLE_API_KEY,
        },
        timeout=20,
    )

    if response.status_code != 200:
        return {}

    return response.json().get("result", {})


def _extract_email_from_website(url: str | None) -> str | None:
    if not url:
        return None

    try:
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )

        if response.status_code != 200:
            return None

        emails = re.findall(EMAIL_REGEX, response.text)

        for email in emails:
            email = email.lower().strip()

            # Skip image file extensions
            if email.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                continue

            if _is_valid_email(email):
                return email

    except Exception:
        return None

    return None


def enrich_demand_prospects(db: Session, limit: int = 25) -> dict:
    prospects = db.query(DemandProspect).filter(
        DemandProspect.status != "enriched"
    ).limit(limit).all()

    checked = 0
    enriched = 0
    outreach_created = 0
    no_contact = 0

    for prospect in prospects:
        checked += 1

        website = prospect.website
        phone = prospect.phone
        email = prospect.email

        place = _find_google_place(prospect)

        if place:
            place_id = place.get("place_id")

            if place_id:
                details = _get_place_details(place_id)

                website = website or details.get("website")
                phone = phone or details.get("formatted_phone_number")

                if not prospect.address:
                    prospect.address = details.get("formatted_address")

        # TRY EXTRACT EMAIL
        if not email and website:
            email = _extract_email_from_website(website)

        # FINAL CLEAN — use strict validator
        if email and not _is_valid_email(email):
            email = None

        # SAVE DATA
        if website:
            prospect.website = website

        if phone:
            prospect.phone = phone

        if email:
            prospect.email = email
            prospect.status = "enriched"
            enriched += 1

            existing = db.query(OutreachLog).filter(
                OutreachLog.email == email
            ).first()

            if not existing:
                outreach = OutreachLog(
                    email=email,
                    subject=f"Commercial plumbing opportunity - {prospect.name}",
                    status="new",
                    lead_score=20,
                    estimated_value=_estimate_value(prospect),
                    close_probability=30,
                    sent_at=None,
                )

                db.add(outreach)
                outreach_created += 1
        else:
            prospect.status = "needs_contact"
            no_contact += 1

        prospect.updated_at = datetime.utcnow()

    db.commit()

    return {
        "success": True,
        "checked": checked,
        "enriched": enriched,
        "outreach_created": outreach_created,
        "no_contact": no_contact,
    }