from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import OutreachLog

router = APIRouter(prefix="/analytics", tags=["analytics"])


# --------------------------------------------------------------------------- #
# PIPELINE
# --------------------------------------------------------------------------- #

@router.get("/pipeline")
def pipeline(db: Session = Depends(get_db)):
    return {
        "new": db.query(OutreachLog).filter(OutreachLog.status == "new").count(),
        "contacted": db.query(OutreachLog).filter(OutreachLog.status == "contacted").count(),
        "interested": db.query(OutreachLog).filter(OutreachLog.status == "interested").count(),
        "closed": db.query(OutreachLog).filter(OutreachLog.status == "closed").count(),
    }


# --------------------------------------------------------------------------- #
# REVENUE
# --------------------------------------------------------------------------- #

@router.get("/revenue")
def revenue(db: Session = Depends(get_db)):
    total = db.query(OutreachLog).filter(
        OutreachLog.status == "closed"
    ).with_entities(OutreachLog.deal_value).all()

    total_revenue = sum([v[0] for v in total if v[0]])

    return {
        "total_revenue": total_revenue
    }


# --------------------------------------------------------------------------- #
# PRIORITY LEADS
# --------------------------------------------------------------------------- #

@router.get("/priority-leads")
def priority_leads(db: Session = Depends(get_db)):
    leads = db.query(OutreachLog)\
        .order_by(OutreachLog.lead_score.desc())\
        .limit(10)\
        .all()

    return leads


# --------------------------------------------------------------------------- #
# RECALCULATE SCORES
# --------------------------------------------------------------------------- #

@router.post("/recalculate-scores")
def recalculate_scores(db: Session = Depends(get_db)):
    from services.scoring import calculate_lead_score

    leads = db.query(OutreachLog).all()

    updated = 0

    for lead in leads:
        lead.lead_score = calculate_lead_score(lead)
        updated += 1

    db.commit()

    return {
        "success": True,
        "updated": updated
    }

@router.get("/matches")
def get_matches(db: Session = Depends(get_db)):
    from models import Match, DemandProspect, Plumber

    matches = db.query(Match, DemandProspect, Plumber)\
        .join(DemandProspect, Match.demand_prospect_id == DemandProspect.id)\
        .join(Plumber, Match.plumber_id == Plumber.id)\
        .order_by(Match.match_score.desc())\
        .limit(20)\
        .all()

    result = []

    for m, prospect, plumber in matches:
        result.append({
            "prospect_name": prospect.name,
            "plumber_name": plumber.name,
            "match_score": m.match_score
        })

    return result

@router.post("/close-deal/{lead_id}/{value}")
def close_deal(lead_id: int, value: int, db: Session = Depends(get_db)):
    lead = db.query(OutreachLog).filter(OutreachLog.id == lead_id).first()

    if not lead:
        return {"success": False, "message": "Lead not found"}

    lead.status = "closed"
    lead.deal_value = value

    db.commit()

    return {
        "success": True,
        "lead_id": lead_id,
        "value": value
    }

@router.post("/clean-bad-leads")
def clean_bad_leads(db: Session = Depends(get_db)):
    leads = db.query(OutreachLog).all()

    deleted = 0

    for lead in leads:
        email = (lead.email or "").lower()

        if not email or "@" not in email:
            db.delete(lead)
            deleted += 1
            continue

        domain = email.split("@")[-1]

        if (
            "." not in domain
            or any(x in email for x in ["user@", "example", "test@", "noreply"])
            or domain.startswith(tuple("0123456789"))
            or any(char.isdigit() for char in domain.split(".")[-1])
        ):
            db.delete(lead)
            deleted += 1

    db.commit()

    return {"deleted": deleted}

@router.get("/demand-prospects")
def get_demand_prospects(db: Session = Depends(get_db)):
    from models import DemandProspect
    prospects = db.query(DemandProspect).order_by(
        DemandProspect.demand_score.desc()
    ).limit(100).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "address": p.address,
            "city": p.city,
            "email": p.email,
            "phone": p.phone,
            "website": p.website,
            "demand_score": p.demand_score,
            "status": p.status,
            "source": p.source,
            "is_high_priority": p.is_high_priority,
        }
        for p in prospects
    ]

@router.get("/plumbers")
def get_plumbers_public(db: Session = Depends(get_db)):
    from models import Plumber
    plumbers = db.query(Plumber).order_by(Plumber.name).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "email": p.email,
            "phone": p.phone,
            "address": p.address,
            "city": p.city,
            "website": p.website,
            "is_commercial": p.is_commercial,
            "category": p.category,
        }
        for p in plumbers
    ]