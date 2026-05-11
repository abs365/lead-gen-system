"""
Snov.io enrichment service for demand prospects.
Uses Company Search API to find verified emails by company name.
Deduplicates by company name to avoid wasting credits.
"""
import os
import re
import logging
import requests
from datetime import datetime
from sqlalchemy.orm import Session
from models import DemandProspect, OutreachLog

logger = logging.getLogger(__name__)

SNOV_TOKEN_URL = "https://api.snov.io/v1/oauth/access_token"
SNOV_DOMAIN_SEARCH_URL = "https://api.snov.io/v2/domain-emails-with-info"
SNOV_COMPANY_SEARCH_URL = "https://api.snov.io/v1/get-company-profile-by-name"
SNOV_ADD_DOMAIN_URL = "https://api.snov.io/v1/add-emails-from-domain"
SNOV_GET_DOMAIN_URL = "https://api.snov.io/v1/get-emails-from-domain"

CLIENT_ID = os.getenv("SNOV_CLIENT_ID", "5521b7e25624003db25ce351f5a3b67b")
CLIENT_SECRET = os.getenv("SNOV_CLIENT_SECRET", "cac595c12884d987add46ccdffa9b53c")

JUNK_EMAIL_PATTERNS = [
    "example.", "test@", "noreply", "no-reply", "placeholder",
    "domain.com", "yourname", "user@", "admin@admin",
    "info@info", "none@", "null@",
]

SKIP_DOMAINS = [
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
    "youtube.com", "google.com", "yell.com", "checkatrade.com",
    "companieshouse.gov.uk", "gov.uk", "hmrc.gov.uk",
]


def _get_access_token() -> str | None:
    try:
        resp = requests.post(SNOV_TOKEN_URL, data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("access_token")
        logger.error(f"Snov.io token error: {resp.status_code} {resp.text}")
        return None
    except Exception as e:
        logger.error(f"Snov.io token request failed: {e}")
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
    if any(p in email for p in JUNK_EMAIL_PATTERNS):
        return False
    if re.search(r'\d+\.\d+', domain):
        return False
    return True


def _extract_domain_from_website(website: str) -> str | None:
    if not website:
        return None
    try:
        from urllib.parse import urlparse
        parsed = urlparse(website)
        domain = parsed.netloc.lower().lstrip("www.")
        if domain and "." in domain and not any(s in domain for s in SKIP_DOMAINS):
            return domain
    except Exception:
        pass
    return None


def _search_domain_emails(token: str, domain: str) -> list[str]:
    """Search for emails on a domain using Snov.io."""
    try:
        # Step 1: Add domain to search queue
        resp = requests.post(SNOV_ADD_DOMAIN_URL, data={
            "access_token": token,
            "domain": domain,
            "type": "all",
            "limit": 5,
        }, timeout=15)

        if resp.status_code != 200:
            return []

        # Step 2: Get results
        resp2 = requests.get(SNOV_GET_DOMAIN_URL, params={
            "access_token": token,
            "domain": domain,
            "type": "all",
            "limit": 5,
        }, timeout=15)

        if resp2.status_code != 200:
            return []

        emails_data = resp2.json().get("emails", [])
        emails = []
        for item in emails_data:
            email = item.get("email", "")
            if _is_valid_email(email):
                emails.append(email)
        return emails

    except Exception as e:
        logger.error(f"Snov domain search error for {domain}: {e}")
        return []


def _pick_best_email(emails: list[str]) -> str | None:
    """Pick the best email — prefer info/contact/hello over personal."""
    if not emails:
        return None

    priority_prefixes = ["info", "contact", "hello", "enquiries", "enquiry", "sales", "admin"]

    for prefix in priority_prefixes:
        for email in emails:
            if email.lower().startswith(prefix + "@"):
                return email

    # Fall back to first valid email
    return emails[0] if emails else None


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


def _clean_company_name(name: str) -> str:
    """Remove Ltd, Limited, PLC etc for cleaner search."""
    suffixes = [
        r'\bLIMITED\b', r'\bLTD\b', r'\bPLC\b', r'\bLLP\b',
        r'\bLLC\b', r'\bCIC\b', r'\bCIO\b', r'\(.*?\)',
    ]
    cleaned = name.upper()
    for suffix in suffixes:
        cleaned = re.sub(suffix, '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip().strip('-').strip()


def enrich_demand_with_snov(db: Session, limit: int = 25) -> dict:
    """
    Enrich demand prospects using Snov.io domain search.
    Deduplicates by company name to avoid burning credits on duplicates.
    """
    token = _get_access_token()
    if not token:
        return {"success": False, "error": "Failed to get Snov.io access token"}

    # Get prospects that need enrichment
    prospects = db.query(DemandProspect).filter(
        DemandProspect.status.in_(["new", "needs_contact"]),
        DemandProspect.email.is_(None),
    ).limit(limit * 3).all()  # Fetch more to account for deduplication

    # Deduplicate by cleaned company name — don't hit Snov.io twice for same company
    seen_names = set()
    seen_domains = set()
    unique_prospects = []

    for p in prospects:
        cleaned = _clean_company_name(p.name or "")
        domain = _extract_domain_from_website(p.website)

        # Skip if we've already processed this company name or domain
        if cleaned in seen_names:
            # Mark as needs_contact so we don't keep retrying
            p.status = "needs_contact"
            continue
        if domain and domain in seen_domains:
            p.status = "needs_contact"
            continue

        seen_names.add(cleaned)
        if domain:
            seen_domains.add(domain)
        unique_prospects.append(p)

        if len(unique_prospects) >= limit:
            break

    db.commit()

    checked = 0
    enriched = 0
    no_contact = 0
    outreach_created = 0

    for prospect in unique_prospects:
        checked += 1
        email = None

        # Strategy 1: If prospect already has a website, search that domain
        domain = _extract_domain_from_website(prospect.website)

        if domain:
            emails = _search_domain_emails(token, domain)
            email = _pick_best_email(emails)

        # Strategy 2: Try deriving domain from company name via Snov company search
        if not email:
            try:
                company_name = _clean_company_name(prospect.name or "")
                resp = requests.post(SNOV_COMPANY_SEARCH_URL, data={
                    "access_token": token,
                    "name": company_name,
                }, timeout=15)

                if resp.status_code == 200:
                    data = resp.json()
                    # Snov returns company profile with website
                    website = data.get("webSite") or data.get("website")
                    if website:
                        domain = _extract_domain_from_website(website)
                        if domain and domain not in seen_domains:
                            seen_domains.add(domain)
                            # Update prospect website
                            prospect.website = website
                            emails = _search_domain_emails(token, domain)
                            email = _pick_best_email(emails)
            except Exception as e:
                logger.error(f"Snov company search error for {prospect.name}: {e}")

        # Save results
        if email and _is_valid_email(email):
            prospect.email = email
            prospect.status = "enriched"
            enriched += 1

            # Create outreach log if not already exists
            existing = db.query(OutreachLog).filter(
                OutreachLog.email == email
            ).first()

            if not existing:
                outreach = OutreachLog(
                    email=email,
                    subject=f"Commercial plumbing opportunity - {prospect.name}",
                    status="new",
                    lead_score=25,
                    estimated_value=_estimate_value(prospect),
                    close_probability=35,
                    sent_at=None,
                )
                db.add(outreach)
                outreach_created += 1

            logger.info(f"Enriched {prospect.name} -> {email}")
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