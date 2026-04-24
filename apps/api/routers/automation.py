from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import OutreachLog, Match
from services.ai_outreach import generate_ai_outreach
from services.email_sender import send_email
from services.matching import run_matching
from services.scoring import assign_high_priority_flags

router = APIRouter()


# ------------------------------------------------------------------
# RUN FULL PIPELINE
# ------------------------------------------------------------------

@router.post("/run-full-pipeline")
def run_full_pipeline(db: Session = Depends(get_db)):
    created = run_matching(db)
    assign_high_priority_flags(db)

    return {
        "matches_created": created,
        "status": "pipeline complete"
    }


# ------------------------------------------------------------------
# FOLLOW-UP
# ------------------------------------------------------------------

from datetime import datetime, timedelta


@router.post("/follow-up")
def follow_up(db: Session = Depends(get_db)):
    cutoff_time = datetime.utcnow() - timedelta(hours=24)

    logs = (
        db.query(OutreachLog)
        .filter(
            OutreachLog.opened == 0,
            OutreachLog.sent_at < cutoff_time
        )
        .all()
    )

    sent = 0

    for log in logs:
        match = (
            db.query(Match)
            .options(joinedload(Match.demand_prospect), joinedload(Match.plumber))
            .filter(Match.id == log.match_id)
            .first()
        )

        if not match:
            continue

        if not match.plumber or not match.plumber.email:
            continue

        result = generate_ai_outreach(
            match.demand_prospect,
            match.plumber,
            match.match_score
        )

        try:
            send_email(
                to_email=match.plumber.email,
                subject="Following up — quick check",
                body=result["message"]
            )
            sent += 1
        except Exception:
            continue

    return {"follow_up_sent": sent}