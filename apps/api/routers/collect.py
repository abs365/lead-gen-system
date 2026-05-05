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

from models import Plumber, Opportunity

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
def get_plumbers():
    db = SessionLocal()
    try:
        return db.query(Plumber).all()
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
        "plumbing services Islington",
        "plumbing services Tower Hamlets",
        "plumbing services Wandsworth",
        "plumbing services Lewisham",
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

                if "canada" in address.lower() or "australia" in address.lower():
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

                plumber = Plumber(
                    name=name,
                    address=address,
                    city="London",
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