import re
import time
import httpx
from sqlalchemy.orm import Session
from models import Plumber

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

SKIP_DOMAINS = [
    "sentry.io", "wix.com", "wordpress.com", "squarespace.com",
    "googletagmanager", "schema.org", "example.com", "gmail.com",
    "yahoo.com", "hotmail.com", "w3.org", "jquery.com",
    "amazonaws.com", "cloudflare.com", "google.com", "facebook.com",
    "twitter.com", "instagram.com", "linkedin.com", "apple.com",
]

SKIP_PREFIXES = [
    "noreply", "no-reply", "donotreply", "support", "admin",
    "webmaster", "postmaster", "mailer", "bounce", "newsletter",
    "notifications", "notification", "alerts", "alert", "news",
    "marketing", "sales@", "enquiries@", "enquiry@",
]

def is_valid_email(email: str) -> bool:
    email = email.lower()
    if any(skip in email for skip in SKIP_DOMAINS):
        return False
    prefix = email.split("@")[0]
    if any(prefix.startswith(s.rstrip("@")) for s in SKIP_PREFIXES):
        return False
    parts = email.split("@")
    if len(parts) != 2:
        return False
    domain = parts[1]
    if "." not in domain:
        return False
    # Must have a real TLD
    tld = domain.split(".")[-1]
    if len(tld) < 2 or len(tld) > 6:
        return False
    return True
def scrape_email_from_website(url: str) -> str | None:
    if not url:
        return None
    try:
        if not url.startswith("http"):
            url = "https://" + url
        headers = {"User-Agent": "Mozilla/5.0 (compatible; LeadBot/1.0)"}
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                return None
            text = resp.text
            emails = EMAIL_REGEX.findall(text)
            for email in emails:
                email = email.lower().strip(".,;")
                if is_valid_email(email):
                    return email
            # Try /contact page
            base = url.rstrip("/")
            for path in ["/contact", "/contact-us", "/about"]:
                try:
                    resp2 = client.get(base + path, headers=headers, timeout=8.0)
                    if resp2.status_code == 200:
                        emails2 = EMAIL_REGEX.findall(resp2.text)
                        for email in emails2:
                            email = email.lower().strip(".,;")
                            if is_valid_email(email):
                                return email
                except Exception:
                    continue
    except Exception:
        return None
    return None

def enrich_plumbers(db: Session, limit: int = 50) -> dict:
    plumbers = db.query(Plumber).filter(
        Plumber.email.is_(None),
        Plumber.website.isnot(None),
    ).limit(limit).all()

    enriched = 0
    failed = 0

    for plumber in plumbers:
        email = scrape_email_from_website(plumber.website)
        if email:
            plumber.email = email
            enriched += 1
        else:
            failed += 1
        time.sleep(0.5)

    db.commit()

    return {
        "success": True,
        "enriched": enriched,
        "failed": failed,
        "total_processed": enriched + failed,
    }