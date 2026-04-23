from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Match
from services.outreach import generate_outreach_message
from services.export import generate_csv
from services.email_sender import send_email

router = APIRouter()


@router.get("/top-leads")
def get_top_leads(db: Session = Depends(get_db)):
    matches = (
        db.query(Match)
        .options(joinedload(Match.demand_prospect), joinedload(Match.plumber))
        .order_by(Match.match_score.desc())
        .limit(20)
        .all()
    )

    return [
        {
            "match_id": m.id,
            "score": m.match_score,
            "business": m.demand_prospect.name if m.demand_prospect else None,
            "plumber": m.plumber.name if m.plumber else None,
        }
        for m in matches
    ]


@router.get("/outreach/{match_id}")
def generate_outreach(match_id: int, db: Session = Depends(get_db)):
    match = (
        db.query(Match)
        .options(joinedload(Match.demand_prospect), joinedload(Match.plumber))
        .filter(Match.id == match_id)
        .first()
    )

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    result = generate_outreach_message(
        match.demand_prospect,
        match.plumber,
        match.match_score
    )

    return {
        "match_id": match.id,
        "subject": result["subject"],
        "message": result["message"]
    }


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    matches = (
        db.query(Match)
        .options(joinedload(Match.demand_prospect), joinedload(Match.plumber))
        .order_by(Match.match_score.desc())
        .limit(100)
        .all()
    )

    csv_data = generate_csv(matches)

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )


@router.post("/send-outreach")
def send_outreach(db: Session = Depends(get_db)):
    matches = (
        db.query(Match)
        .options(joinedload(Match.demand_prospect), joinedload(Match.plumber))
        .order_by(Match.match_score.desc())
        .limit(10)
        .all()
    )

    sent = 0
    skipped = 0

    for m in matches:
        if not m.plumber or not m.plumber.email:
            skipped += 1
            continue

        result = generate_outreach_message(
            m.demand_prospect,
            m.plumber,
            m.match_score
        )

        try:
            send_email(
                to_email=m.plumber.email,
                subject=result["subject"],
                body=result["message"]
            )
            sent += 1
        except Exception as e:
            print("❌ EMAIL ERROR:", str(e))
            skipped += 1

    return {
        "sent": sent,
        "skipped": skipped
    }