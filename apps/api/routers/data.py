from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, HTMLResponse
from sqlalchemy.orm import Session, joinedload
import uuid

from database import get_db
from models import Match, OutreachLog
from services.export import generate_csv
from services.email_sender import send_email
from services.ai_outreach import generate_ai_outreach

router = APIRouter()


# ---------------------------------------------------------------------------
# TRACK OPEN
# ---------------------------------------------------------------------------

@router.get("/track/open/{tracking_id}")
def track_open(tracking_id: str, db: Session = Depends(get_db)):
    log = db.query(OutreachLog).filter(OutreachLog.tracking_id == tracking_id).first()

    if log:
        log.opened = 1
        db.commit()

    return HTMLResponse(content="<img src='' />")


# ---------------------------------------------------------------------------
# TRACK CLICK
# ---------------------------------------------------------------------------

@router.get("/track/click/{tracking_id}")
def track_click(tracking_id: str, db: Session = Depends(get_db)):
    log = db.query(OutreachLog).filter(OutreachLog.tracking_id == tracking_id).first()

    if log:
        log.clicked = 1
        db.commit()

    return {"status": "clicked"}


# ---------------------------------------------------------------------------
# TOP LEADS
# ---------------------------------------------------------------------------

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
            "is_high_priority": m.demand_prospect.is_high_priority if m.demand_prospect else 0,
        }
        for m in matches
    ]


# ---------------------------------------------------------------------------
# GENERATE OUTREACH
# ---------------------------------------------------------------------------

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

    result = generate_ai_outreach(
        match.demand_prospect,
        match.plumber,
        match.match_score
    )

    return {
        "match_id": match.id,
        "subject": result["subject"],
        "message": result["message"],
        "tracking_id": result.get("tracking_id"),
    }


# ---------------------------------------------------------------------------
# EXPORT CSV
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# SEND OUTREACH EMAILS (WITH TRACKING)
# ---------------------------------------------------------------------------

@router.post("/send-outreach")
def send_outreach(db: Session = Depends(get_db)):
    matches = (
        db.query(Match)
        .options(joinedload(Match.demand_prospect), joinedload(Match.plumber))
        .order_by(Match.match_score.desc())
        .all()
    )

    sent = 0
    skipped = 0

    for m in matches:
        if not m.demand_prospect or m.demand_prospect.is_high_priority != 1:
            skipped += 1
            continue

        if not m.plumber or not m.plumber.email:
            skipped += 1
            continue

        result = generate_ai_outreach(
            m.demand_prospect,
            m.plumber,
            m.match_score
        )

        tracking_id = result.get("tracking_id", str(uuid.uuid4()))

        try:
            send_email(
                to_email=m.plumber.email,
                subject=result["subject"],
                body=result["message"]
            )

            db.add(
                OutreachLog(
                    match_id=m.id,
                    plumber_id=m.plumber.id,
                    email=m.plumber.email,
                    subject=result["subject"],
                    body=result["message"],
                    status="sent",
                    tracking_id=tracking_id,
                )
            )
            db.commit()
            sent += 1

        except Exception as e:
            db.rollback()

            db.add(
                OutreachLog(
                    match_id=m.id,
                    plumber_id=m.plumber.id,
                    email=m.plumber.email,
                    subject=result["subject"],
                    body=result["message"],
                    status="failed",
                    error_message=str(e),
                    tracking_id=tracking_id,
                )
            )
            db.commit()
            skipped += 1

    return {
        "sent": sent,
        "skipped": skipped
    }


# ---------------------------------------------------------------------------
# RESET MATCHES
# ---------------------------------------------------------------------------

@router.post("/reset-matches")
def reset_matches(db: Session = Depends(get_db)):
    db.query(Match).delete()
    db.commit()
    return {"status": "cleared"}