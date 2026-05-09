from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from services.security import require_api_key

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/call-interested-plumbers")
def call_interested_plumbers_endpoint(db: Session = Depends(get_db), api_key: str = Depends(require_api_key)):
    from services.voice_call import call_interested_plumbers
    result = call_interested_plumbers(db)
    return result


@router.post("/keypress/{lead_id}")
async def handle_keypress(lead_id: int, request: Request, Digits: str = Form(default="")):
    db = SessionLocal()
    try:
        from models import OutreachLog, Plumber, Match, DemandProspect
        from utils.email import send_email

        log = db.query(OutreachLog).filter(OutreachLog.id == lead_id).first()

        if Digits == "1" and log:
            # Send prospect details to plumber
            plumber = db.query(Plumber).filter(Plumber.id == log.plumber_id).first()
            match = db.query(Match).filter(
                Match.plumber_id == log.plumber_id,
                Match.outreach_sent == 1,
            ).order_by(Match.match_score.desc()).first()

            if match and plumber:
                prospect = db.query(DemandProspect).filter(
                    DemandProspect.id == match.demand_prospect_id
                ).first()

                if prospect and plumber.email:
                    body = f"<p>Hi {plumber.name},</p><p>As requested, here are the full contact details for the lead:</p><p><strong>{prospect.name}</strong><br>{prospect.address}<br>{prospect.city}<br>Phone: {prospect.phone or 'N/A'}<br>Email: {prospect.email or 'N/A'}<br>Website: {prospect.website or 'N/A'}</p><p>Good luck!</p><p>— Zephyr William<br>Merit-Bold Lead Generation</p>"
                    send_email(plumber.email, "Your lead contact details — Merit-Bold", body)

            if log:
                log.status = "deal_sent"
                db.commit()

            twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Amy">Great! We have sent the full contact details to your email. Good luck with the job. Goodbye!</Say>
</Response>"""

        elif Digits == "2":
            if log:
                log.status = "unsubscribed"
                db.commit()

            twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Amy">No problem. We have removed you from our list. Goodbye!</Say>
</Response>"""

        else:
            twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Amy">We did not receive a valid response. Goodbye.</Say>
</Response>"""

        return PlainTextResponse(content=twiml, media_type="application/xml")

    finally:
        db.close()