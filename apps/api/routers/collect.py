# --------------------------------------------------------------------------- #
# IMPORTS
# --------------------------------------------------------------------------- #

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db, SessionLocal
from services.security import require_api_key
from utils.email import send_email
from services.auto_send import run_auto_send
from services.reply_handler import process_replies
from services.reply_detector import hard_unsubscribe

from models import Plumber, Opportunity, OutreachLog
from services.plumber_email_collector import collect_plumber_emails

# --------------------------------------------------------------------------- #
# ROUTER
# --------------------------------------------------------------------------- #

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/collect",
    tags=["collect"],
)

# --------------------------------------------------------------------------- #
# REQUEST MODELS
# --------------------------------------------------------------------------- #

class SendOpportunityRequest(BaseModel):
    opportunity_id: int
    plumber_id: int


class ManualUnsubscribeRequest(BaseModel):
    emails: list[str]


class OpportunityCreate(BaseModel):
    business_name: str
    category: str | None = None
    location: str | None = None
    issue_detected: str
    urgency_score: int = 0
    estimated_value: int = 0


# --------------------------------------------------------------------------- #
# AUTO SEND
# --------------------------------------------------------------------------- #

@router.post("/opportunities/auto-send")
def auto_send():
    run_auto_send()
    return {"message": "Auto send executed"}


# --------------------------------------------------------------------------- #
# MARK INTERESTED
# --------------------------------------------------------------------------- #

@router.post("/opportunities/mark-interested")
def mark_interested(opportunity_id: int):
    db = SessionLocal()

    try:
        opp = db.query(Opportunity).filter(
            Opportunity.id == opportunity_id
        ).first()

        if not opp:
            return {"error": "Opportunity not found"}

        opp.is_interested = 1
        opp.status = "interested"

        db.commit()

        return {"message": "Marked as interested"}

    finally:
        db.close()


# --------------------------------------------------------------------------- #
# GET OPPORTUNITIES
# --------------------------------------------------------------------------- #

@router.get("/opportunities")
def get_opportunities():
    db = SessionLocal()
    try:
        return db.query(Opportunity).all()
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# GET PLUMBERS
# --------------------------------------------------------------------------- #

@router.get("/plumbers")
def get_plumbers(with_email: bool = False, limit: int = 100, offset: int = 0):
    db = SessionLocal()
    try:
        query = db.query(Plumber)
        if with_email:
            query = query.filter(Plumber.email.isnot(None)).filter(Plumber.email != "")
        return query.offset(offset).limit(limit).all()
    finally:
        db.close()

# --------------------------------------------------------------------------- #
# CREATE TEST PLUMBER
# --------------------------------------------------------------------------- #

@router.post("/plumbers/create-test")
def create_test_plumber():
    db = SessionLocal()
    try:
        plumber = Plumber(
            name="Test Plumber",
            email="blue2gtv@gmail.com"
        )

        db.add(plumber)
        db.commit()
        db.refresh(plumber)

        return plumber
    finally:
        db.close()


@router.post("/replies/process")
def process_reply_endpoint():
    process_replies()
    return {"message": "Replies processed"}


# --------------------------------------------------------------------------- #
# MANUAL UNSUBSCRIBE
# --------------------------------------------------------------------------- #

@router.post("/manual-unsubscribe", dependencies=[Depends(require_api_key)])
def manual_unsubscribe(data: ManualUnsubscribeRequest):
    db = SessionLocal()
    processed = []
    try:
        for email in data.emails:
            email = email.strip().lower()
            if not email:
                continue
            hard_unsubscribe(db, email)
            processed.append(email)
        return {"unsubscribed": processed, "count": len(processed)}
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# CREATE OPPORTUNITY
# --------------------------------------------------------------------------- #

@router.post("/opportunities/create")
def create_opportunity(data: OpportunityCreate):
    db = SessionLocal()
    try:
        opportunity = Opportunity(
            business_name=data.business_name,
            category=data.category,
            location=data.location,
            issue_detected=data.issue_detected,
            urgency_score=data.urgency_score,
            estimated_value=data.estimated_value,
            status="new"
        )

        db.add(opportunity)
        db.commit()
        db.refresh(opportunity)

        return {"id": opportunity.id}
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# SEND OPPORTUNITY
# --------------------------------------------------------------------------- #

@router.post("/opportunities/send")
def send_opportunity(data: SendOpportunityRequest):
    db = SessionLocal()
    try:
        opportunity = db.query(Opportunity).filter(
            Opportunity.id == data.opportunity_id
        ).first()

        plumber = db.query(Plumber).filter(
            Plumber.id == data.plumber_id
        ).first()

        if not opportunity or not plumber:
            return {"error": "Opportunity or plumber not found"}

        plumber_email = getattr(plumber, "email", None)

        if not plumber_email:
            return {"error": "Plumber email not found"}

        subject = f"New plumbing job in your area (£{opportunity.estimated_value})"

        body = f"""
Hi,

We've identified a business in your area that may need plumbing work.

Business: {opportunity.business_name}
Location: {opportunity.location}
Issue: {opportunity.issue_detected}
Estimated value: £{opportunity.estimated_value}
Urgency: {opportunity.urgency_score}/10

Reply YES if interested.

– MeritBold
"""

        send_email(plumber_email, subject, body)

        opportunity.status = "sent"
        opportunity.plumber_id = plumber.id
        opportunity.sent_at = datetime.utcnow()

        db.commit()

        return {"message": "Opportunity sent"}

    finally:
        db.close()


# --------------------------------------------------------------------------- #
# SCORING + MATCHING
# --------------------------------------------------------------------------- #

@router.get("/score-demand")
def score_demand_endpoint(db: Session = Depends(get_db)):
    from services.scoring import calculate_demand_score, assign_high_priority_flags
    from models import DemandProspect
    prospects = db.query(DemandProspect).all()
    updated = 0
    for p in prospects:
        raw = p.score_breakdown or ""
        signals = [s.strip() for s in raw.split(",") if s.strip()]
        score, breakdown = calculate_demand_score(
            signals=signals,
            source=p.source or "fsa",
            inspection_date=p.last_inspection_date
        )
        p.demand_score = score
        p.score_breakdown = breakdown
        p.is_high_priority = 1 if score >= 70 else 0
        updated += 1
    assign_high_priority_flags(db)
    db.commit()
    return {"success": True, "scored": updated}


@router.get("/run-matching-engine")
def run_matching_engine_endpoint(db: Session = Depends(get_db)):
    from services.matching_engine import run_matching_engine
    result = run_matching_engine(db)
    return result

@router.get("/enrich-demand")
def enrich_demand_endpoint(db: Session = Depends(get_db)):
    from services.demand_enrichment import enrich_demand_prospects
    result = enrich_demand_prospects(db, limit=25)
    return result

@router.get("/planning-data")
def collect_planning_data_endpoint(db: Session = Depends(get_db)):
    from services.planning_data import collect_planning_applications
    result = collect_planning_applications(db, days_back=30, limit=100)
    return result

@router.get("/collect-plumbers")
def collect_plumbers_endpoint(db: Session = Depends(get_db)):
    import os
    import httpx
    import re
    import time

    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

    SEARCH_TERMS = [
        # London
        "commercial plumber London",
        "plumbing contractor London",
        "gas engineer London",
        "heating engineer London",
        "emergency plumber East London",
        "emergency plumber South London",
        "emergency plumber North London",
        "emergency plumber West London",
        "plumbing services Hackney",
        "plumbing services Southwark",
        "plumbing services Lambeth",
        "plumbing services Tower Hamlets",
        # Birmingham
        "commercial plumber Birmingham",
        "plumbing contractor Birmingham",
        "gas engineer Birmingham",
        "emergency plumber Birmingham",
        "plumbing services Birmingham city centre",
        "plumber Solihull",
        "plumber Wolverhampton",
        "plumber Coventry",
        # Manchester
        "commercial plumber Manchester",
        "plumbing contractor Manchester",
        "gas engineer Manchester",
        "emergency plumber Manchester",
        "plumbing services Salford",
        "plumber Stockport",
        "plumber Bolton",
        "plumber Oldham",
        # Other major cities
        "commercial plumber Leeds",
        "commercial plumber Sheffield",
        "commercial plumber Bristol",
        "commercial plumber Liverpool",
        "commercial plumber Newcastle",
        "commercial plumber Nottingham",
        "commercial plumber Leicester",
    ]

    added = 0
    skipped = 0

    for term in SEARCH_TERMS:
        try:
            params = {"query": term, "region": "gb", "key": GOOGLE_API_KEY}
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(TEXT_SEARCH_URL, params=params)
                data = resp.json()

            if data.get("status") not in ("OK", "ZERO_RESULTS"):
                continue

            for place in data.get("results", []):
                place_id = place.get("place_id")
                name = place.get("name", "").strip()
                address = place.get("formatted_address", "")

                if not place_id or not name:
                    skipped += 1
                    continue

                if "canada" in address.lower() or "australia" in address.lower() or "united states" in address.lower():
                    skipped += 1
                    continue

                existing = db.query(Plumber).filter(Plumber.place_id == place_id).first()
                if existing:
                    skipped += 1
                    continue

                # Get details
                phone = None
                website = None
                try:
                    det_params = {
                        "place_id": place_id,
                        "fields": "formatted_phone_number,website",
                        "key": GOOGLE_API_KEY,
                    }
                    with httpx.Client(timeout=10.0) as client:
                        det_resp = client.get(DETAILS_URL, params=det_params)
                        det_data = det_resp.json().get("result", {})
                        phone = det_data.get("formatted_phone_number")
                        website = det_data.get("website")
                    time.sleep(0.5)
                except Exception:
                    pass

                location = place.get("geometry", {}).get("location", {})
                postcode_match = re.search(
                    r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b',
                    address, re.IGNORECASE
                )

                # Extract city from address
                city = "London"
                for c in ["Birmingham", "Manchester", "Leeds", "Sheffield",
                          "Bristol", "Liverpool", "Newcastle", "Nottingham",
                          "Leicester", "Coventry", "Wolverhampton", "Solihull",
                          "Salford", "Stockport", "Bolton", "Oldham"]:
                    if c.lower() in address.lower():
                        city = c
                        break

                plumber = Plumber(
                    name=name,
                    address=address,
                    city=city,
                    postcode=postcode_match.group(1).upper() if postcode_match else None,
                    lat=location.get("lat"),
                    lng=location.get("lng"),
                    place_id=place_id,
                    source="google_places",
                    category="plumber",
                    website=website,
                    phone=phone,
                    is_commercial=1,
                )
                db.add(plumber)
                added += 1

            db.commit()
            time.sleep(1)

        except Exception as e:
            continue

    return {
        "success": True,
        "added": added,
        "skipped": skipped,
    }

@router.get("/collect-demand-all-cities")
def collect_demand_all_cities(db: Session = Depends(get_db)):
    from services.food_standards import fetch_all_cities
    from models import DemandProspect
    results = fetch_all_cities()
    added = 0
    skipped = 0
    for r in results:
        try:
            existing = db.query(DemandProspect).filter(
                DemandProspect.fsa_establishment_id == str(r.get("fsa_establishment_id", ""))
            ).first()
            if existing:
                skipped += 1
                continue
            if not r.get("name"):
                skipped += 1
                continue
            prospect = DemandProspect(
                name=r.get("name"),
                category=r.get("category"),
                address=r.get("address"),
                city=r.get("city", "London"),
                borough=r.get("borough"),
                postcode=r.get("postcode"),
                fsa_establishment_id=str(r.get("fsa_establishment_id", "")),
                fsa_rating=r.get("fsa_rating"),
                last_inspection_date=None,
                source="fsa",
                status="new",
            )
            db.add(prospect)
            db.commit()
            added += 1
        except Exception:
            db.rollback()
            skipped += 1
            continue
    return {"success": True, "added": added, "skipped": skipped}

@router.get("/collect-companies-house")
def collect_companies_house_endpoint(db: Session = Depends(get_db)):
    from services.companies_house import collect_companies_house
    result = collect_companies_house(db, max_per_term=10)
    return result

@router.get("/fix-companies-house-priority")
def fix_companies_house_priority(db: Session = Depends(get_db)):
    from models import DemandProspect
    prospects = db.query(DemandProspect).filter(
        DemandProspect.source == "companies_house"
    ).all()
    updated = 0
    for p in prospects:
        if (p.demand_score or 0) >= 25:
            p.is_high_priority = 1
            updated += 1
    db.commit()
    return {"success": True, "updated": updated}

@router.get("/enrich-plumbers")
def enrich_plumbers_endpoint(db: Session = Depends(get_db)):
    from services.plumber_enrichment import enrich_plumbers
    result = enrich_plumbers(db, limit=50)
    return result

@router.get("/clean-fake-emails")
def clean_fake_emails_endpoint(db: Session = Depends(get_db)):
    from services.plumber_enrichment import null_fake_plumber_emails
    nulled = null_fake_plumber_emails(db)
    return {"success": True, "fake_emails_nulled": nulled}

@router.get("/process-manual-unsubscribes")
def process_manual_unsubscribes_endpoint(db: Session = Depends(get_db)):
    from services.reply_detector import process_manual_unsubscribes
    return process_manual_unsubscribes(db)

@router.get("/clean-bounces")
def clean_bounces_endpoint(db: Session = Depends(get_db)):
    from services.bounce_handler import clean_bounced_emails
    result = clean_bounced_emails(db)
    return result


# --------------------------------------------------------------------------- #
# CLEAN JUNK OUTREACH LOGS + PLUMBER EMAILS
# --------------------------------------------------------------------------- #

import re as _re

_JUNK_EMAIL_SUBSTRINGS = [
    "@11.", "@1.", "@5.", "@1.8",
    "segmenter", "carousel", "bootstrap", "jquery", "webpack", "node_modules",
]


def _email_is_junk(email: str) -> bool:
    if not email:
        return False
    e = email.lower()
    if any(s in e for s in _JUNK_EMAIL_SUBSTRINGS):
        return True
    if "@" in e:
        domain = e.split("@", 1)[1]
        if _re.search(r'\d', domain):
            return True
    return False


@router.get("/clean-all-fake-outreach-logs")
def clean_all_fake_outreach_logs(db: Session = Depends(get_db)):
    logs = db.query(OutreachLog).filter(OutreachLog.email.isnot(None)).all()
    deleted = 0
    for log in logs:
        if _email_is_junk(log.email):
            db.delete(log)
            deleted += 1
    db.commit()
    return {"success": True, "deleted": deleted}


@router.get("/wipe-bad-plumber-emails")
def wipe_bad_plumber_emails(db: Session = Depends(get_db)):
    plumbers = db.query(Plumber).filter(Plumber.email.isnot(None)).all()
    wiped = 0
    for plumber in plumbers:
        if _email_is_junk(plumber.email):
            plumber.email = None
            wiped += 1
    db.commit()
    return {"success": True, "wiped": wiped}


@router.get("/wipe-all-plumber-emails")
def wipe_all_plumber_emails(db: Session = Depends(get_db)):
    wiped = db.query(Plumber).filter(Plumber.email.isnot(None)).update(
        {"email": None}, synchronize_session=False
    )
    db.commit()
    return {"success": True, "wiped": wiped}

@router.get("/collect-plumber-emails", dependencies=[Depends(require_api_key)])
def collect_plumber_emails_endpoint(limit: int = 100, db: Session = Depends(get_db)):
    """
    Fetch clean emails for plumbers that have a place_id but no email.
    Uses Google Places Details API only — no website scraping.
    """
    return collect_plumber_emails(db, limit=limit)