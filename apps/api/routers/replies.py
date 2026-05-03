from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
import os

from database import get_db
from services.reply_detector import detect_gmail_replies
from services.reply_followup import send_reply_followups
from services.deal_detector import detect_and_close_deals
from services.azure_email import send_email  # 👈 NEW

router = APIRouter(prefix="/automation", tags=["automation"])

API_KEY = os.getenv("API_KEY")


# =========================
# EXISTING ENDPOINTS (UNCHANGED)
# =========================

@router.post("/detect-replies")
def detect_replies(db: Session = Depends(get_db)):
    return detect_gmail_replies(db)


@router.post("/followup-replies")
def followup_replies(db: Session = Depends(get_db)):
    return send_reply_followups(db)


@router.post("/detect-deals")
def detect_deals(db: Session = Depends(get_db)):
    return detect_and_close_deals(db)


# =========================
# NEW: PROCESS + SEND EMAIL
# =========================

@router.post("/collect/replies/process")
def process_replies(
    x_api_key: str = Header(...),
    db: Session = Depends(get_db)
):
    print("ENV API_KEY:", API_KEY)
    print("HEADER API_KEY:", x_api_key)

    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # AUTH
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    try:
        # STEP 1: detect replies
        replies = detect_gmail_replies(db)

        # STEP 2: optional follow-ups
        send_reply_followups(db)

        # STEP 3: detect deals
        detect_and_close_deals(db)

        # STEP 4: send email notification (example)
        # 👉 Replace with real recipient logic later
        send_email(
            to_email="test@example.com",
            subject="Replies Processed",
            body="<h3>Replies processed successfully.</h3>"
        )

        return {
            "message": "Replies processed",
            "replies_detected": len(replies) if replies else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))