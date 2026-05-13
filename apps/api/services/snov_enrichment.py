"""
Snov.io enrichment service for demand prospects.
Uses v2 domain-emails-with-info API to find emails by domain.
No Google Places calls - cost controlled.
"""
import os
import re
import logging
import requests
from datetime import datetime
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from models import DemandProspect, OutreachLog

logger = logging.getLogger(__name__)

SNOV_TOKEN_URL = "https://api.snov.io/v1/oauth/access_token"
SNOV_DOMAIN_URL = "https://api.snov.io/v2/domain-emails-with-info"

CLIENT_ID = os.getenv("SNOV_CLIENT_ID", "5521b7e25624003db25ce351f5a3b67b")
CLIENT_SECRET = os.getenv("SNOV_CLIENT_SECRET", "cac595c12884d987add46ccdffa9b53c")

JUNK_PATTERNS = [
    "example.", "test@", "noreply", "no-reply", "placeholder",
    "domain.com", "user@", "admin@admin", "info@info", "none@",
]

SKIP_DOMAINS = [
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
    "youtube.com", "google.com", "yell.com", "checkatrade.com",
    "companieshouse.gov.uk", "gov.uk",
]

PRIORITY_PREFIXES = [
    "info", "contact", "hello", "enquiries", "enquiry",
    "sales", "admin", "bookings", "reservations", "manager",
]


def _get_token() -> str | None:
    try:
        resp = requests.post(SNOV_TOKEN_URL, data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("access_token")
        logger.error(f"Snov token error: {resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"Snov token failed: {e}")
        return None


def _is_valid_email(email: str) -> bool:
    if not email or "@" not in email:
        return False
    email = email.lower().strip()
    local, domain = email.rsplit("@", 1)
    if "." not in domain:
        return False
    tld = domain.split(".")[-1]
    if tld.isdigit() or len(tld) < 2 or not tld.isalpha():
        return False
    if any(s in domain for s in SKIP_DOMAINS):
        return False
    if any(p in email for p in JUNK_PATTERNS):
        return False
    return True


def _extract_domain(website: str) -> str | None:
    if not website:
        return None
    try:
        if not website.startswith("http"):
            website = "https://" + website
        domain = urlparse(website).netloc.lower().lstrip("www.")
        if domain and "." in domain and not any(s in domain for s in SKIP_DOMAINS):
            return domain
    except Exception:
        pass
    return None


def _get_emails_for_domain(token: str, domain: str) -> list[str]:
    try:
        resp = requests.get(SNOV_DOMAIN_URL, params={
            "access_token": token,
            "domain": domain,
            "type": "all",
            "limit": 10,
        }, timeout=15)

        if resp.status_code != 200:
            logger.error(f"Snov v2 error {resp.status_code} for {domain}")
            return []

        data = resp.json()
        emails_raw = data.get("emails", [])
        valid = []
        for item in emails_raw:
            email = item.get("email", "")
            if _is_valid_email(email):
                valid.append(email)
        return valid

    except Exception as e:
        logger.error(f"Snov domain search failed for {domain}: {e}")
        return []


def _pick_best_email(emails: list[str]) -> str | None:
    if not emails:
        return None
    for prefix in PRIORITY_PREFIXES:
        for email in emails:
            if email.lower().startswith(prefix + "@"):
                return email
    return emails[0]


def _estimate_value(prospect: DemandProspect) -> int:
    text = f"{prospect.name or ''} {prospect.category or ''}".lower()
    if "hotel" in text:
        return 500
    if "restaurant" in text or "cafe" in text:
        return 300
    if "takeaway" in text:
        return 200
    if "property" in text or "facilities" in text or "maintenance" in text:
        return 400
    return 150


def _clean_name(name: str) -> str:
    suffixes = [
        r'\bLIMITED\b', r'\bLTD\b', r'\bPLC\b', r'\bLLP\b',
        r'\bLLC\b', r'\bCIC\b', r'\(.*?\)',
    ]
    cleaned = name
    for s in suffixes:
        cleaned = re.sub(s, '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip().strip('-').strip()


def find_prospect_websites(db: Session, limit: int = 50) -> dict:
    """
    Disabled - Google Places removed due to cost.
    Returns empty result to avoid breaking existing calls.
    """
    return {
        "success": False,
        "error": "Google Places disabled - use enrich_demand_with_snov directly",
        "found_websites": 0,
        "not_found": 0,
        "total_checked": 0,
    }


def enrich_demand_with_snov(db: Session, limit: int = 25) -> dict:
    """
    Enrich demand prospects using Snov.io domain email search.
    Only processes prospects that already have a website.
    No Google Places calls.
    """
    token = _get_token()
    if not token:
        return {"success": False, "error": "Failed to get Snov.io access token"}

    # Only fetch prospects that already have a website
    prospects = db.query(DemandProspect).filter(
        DemandProspect.status.in_(["new", "needs_contact"]),
        DemandProspect.email.is_(None),
        DemandProspect.website.isnot(None),
    ).limit(limit * 4).all()

    seen_domains = set()
    seen_names = set()
    unique = []

    for p in prospects:
        name_key = _clean_name(p.name or "").upper()
        domain = _extract_domain(p.website)

        if name_key in seen_names:
            continue
        if domain and domain in seen_domains:
            continue

        seen_names.add(name_key)
        if domain:
            seen_domains.add(domain)
            unique.append(p)

        if len(unique) >= limit:
            break

    checked = enriched = no_contact = outreach_created = 0

    for prospect in unique:
        checked += 1
        email = None

        domain = _extract_domain(prospect.website)
        if domain:
            emails = _get_emails_for_domain(token, domain)
            email = _pick_best_email(emails)

        if email and _is_valid_email(email):
            prospect.email = email
            prospect.status = "enriched"
            enriched += 1

            existing = db.query(OutreachLog).filter(
                OutreachLog.email == email
            ).first()

            if not existing:
                db.add(OutreachLog(
                    email=email,
                    subject=f"Commercial plumbing opportunity - {prospect.name}",
                    status="new",
                    lead_score=25,
                    estimated_value=_estimate_value(prospect),
                    close_probability=35,
                    sent_at=None,
                ))
                outreach_created += 1

            logger.info(f"Enriched: {prospect.name} -> {email}")
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
        "credits_used_approx": checked,
    }