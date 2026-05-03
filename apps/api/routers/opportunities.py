from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import DemandProspect, Opportunity

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def calculate_urgency_score(prospect):
    score = 0

    if prospect.category:
        category = prospect.category.lower()

        if "restaurant" in category:
            score += 40

        if "hotel" in category:
            score += 50

        if "cafe" in category:
            score += 35

    if prospect.demand_score:
        score += min(prospect.demand_score, 50)

    if not prospect.website:
        score += 10

    return min(score, 100)


def estimate_opportunity_value(prospect, urgency_score):
    value = 100

    if prospect.category:
        category = prospect.category.lower()

        if "hotel" in category:
            value += 500

        elif "restaurant" in category:
            value += 300

        elif "cafe" in category:
            value += 200

    if urgency_score >= 80:
        value += 300

    elif urgency_score >= 60:
        value += 150

    return value


def detect_issue(prospect):
    if prospect.category:
        category = prospect.category.lower()

        if "restaurant" in category or "cafe" in category:
            return "High water usage business likely to need plumbing maintenance, drainage support, or emergency callouts."

        if "hotel" in category:
            return "Accommodation business likely to need urgent plumbing, bathroom, heating, or maintenance support."

    return "Commercial business with possible plumbing support requirement."


@router.get("/generate")
def generate_opportunities(db: Session = Depends(get_db)):
    prospects = db.query(DemandProspect).all()

    created = 0
    skipped = 0

    for prospect in prospects:
        existing = db.query(Opportunity).filter(
            Opportunity.demand_prospect_id == prospect.id
        ).first()

        if existing:
            skipped += 1
            continue

        urgency_score = calculate_urgency_score(prospect)
        estimated_value = estimate_opportunity_value(prospect, urgency_score)

        if urgency_score < 50:
            skipped += 1
            continue

        opportunity = Opportunity(
            demand_prospect_id=prospect.id,
            business_name=prospect.name,
            category=prospect.category,
            city=prospect.city,
            postcode=prospect.postcode,
            issue_detected=detect_issue(prospect),
            signal_source=prospect.source or "internal_scoring",
            urgency_score=urgency_score,
            estimated_value=estimated_value,
            status="new"
        )

        db.add(opportunity)
        created += 1

    db.commit()

    return {
        "status": "opportunities generated",
        "created": created,
        "skipped": skipped
    }


@router.get("/list")
def list_opportunities(db: Session = Depends(get_db)):
    opportunities = db.query(Opportunity)\
        .order_by(Opportunity.urgency_score.desc())\
        .limit(50)\
        .all()

    return [
        {
            "id": o.id,
            "business_name": o.business_name,
            "category": o.category,
            "city": o.city,
            "postcode": o.postcode,
            "issue_detected": o.issue_detected,
            "urgency_score": o.urgency_score,
            "estimated_value": o.estimated_value,
            "status": o.status
        }
        for o in opportunities
    ]


@router.get("/update-status/{opportunity_id}/{status}")
def update_opportunity_status(
    opportunity_id: int,
    status: str,
    db: Session = Depends(get_db)
):
    allowed = ["new", "offered", "accepted", "assigned", "closed", "lost"]

    if status not in allowed:
        return {"error": "invalid status"}

    opportunity = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id
    ).first()

    if not opportunity:
        return {"error": "opportunity not found"}

    opportunity.status = status
    db.commit()

    return {
        "status": "updated",
        "opportunity_id": opportunity_id,
        "new_status": status
    }