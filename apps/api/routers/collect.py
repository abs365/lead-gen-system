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