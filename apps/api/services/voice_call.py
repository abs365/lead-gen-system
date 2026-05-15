import os
import requests
from sqlalchemy.orm import Session
from models import OutreachLog, Plumber, Match, DemandProspect

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
BACKEND_URL = os.getenv("BACKEND_URL", "https://leadgen-api-khfd.onrender.com")

VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs Rachel voice


def generate_voice_audio(text: str) -> bytes | None:
    if not ELEVENLABS_API_KEY:
        return None
    try:
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                }
            },
            timeout=30,
        )
        if response.status_code == 200:
            return response.content
        return None
    except Exception:
        return None


def make_outbound_call(to_number: str, plumber_name: str, prospect_name: str, prospect_category: str, prospect_city: str, prospect_address: str, lead_id: int) -> dict:
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        return {"success": False, "message": "Missing Twilio credentials"}

    if not to_number:
        return {"success": False, "message": "No phone number for plumber"}

    # Clean phone number
    phone = to_number.replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        if phone.startswith("0"):
            phone = "+44" + phone[1:]
        else:
            phone = "+44" + phone

    # TwiML that plays a message and captures keypress
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Amy">
        Hello, this is Abi calling from Merit Bold Lead Generation.
        We have a commercial plumbing opportunity for {plumber_name} in {prospect_city}.
        We identified a {prospect_category or 'commercial property'} at {prospect_address or prospect_city} that needs plumbing work.
        To receive the full contact details, press 1.
        To be removed from our list, press 2.
    </Say>
    <Gather numDigits="1" action="{BACKEND_URL}/voice/keypress/{lead_id}" method="POST" timeout="10">
    </Gather>
    <Say voice="Polly.Amy">We did not receive your input. We will try again later. Goodbye.</Say>
</Response>"""

    try:
        response = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls.json",
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            data={
                "To": phone,
                "From": TWILIO_PHONE_NUMBER,
                "Twiml": twiml,
            },
            timeout=15,
        )

        if response.status_code == 201:
            call_sid = response.json().get("sid")
            return {"success": True, "call_sid": call_sid, "to": phone}
        else:
            return {"success": False, "message": response.text}

    except Exception as e:
        return {"success": False, "message": str(e)}


def call_interested_plumbers(db: Session) -> dict:
    logs = db.query(OutreachLog).filter(
        OutreachLog.status == "interested",
        OutreachLog.replied == 1,
    ).all()

    called = 0
    skipped = 0

    for log in logs:
        try:
            # Look up plumber by email since OutreachLog has no plumber_id
            plumber = db.query(Plumber).filter(
                Plumber.email == log.email
            ).first()

            if not plumber or not plumber.phone:
                skipped += 1
                continue

            # Find the matched prospect
            match = db.query(Match).filter(
                Match.plumber_id == plumber.id,
                Match.outreach_sent == 1,
            ).order_by(Match.match_score.desc()).first()

            if not match:
                skipped += 1
                continue

            prospect = db.query(DemandProspect).filter(
                DemandProspect.id == match.demand_prospect_id
            ).first()

            if not prospect:
                skipped += 1
                continue

            result = make_outbound_call(
                to_number=plumber.phone,
                plumber_name=plumber.name,
                prospect_name=prospect.name,
                prospect_category=prospect.category,
                prospect_city=prospect.city,
                prospect_address=prospect.address,
                lead_id=log.id,
            )

            if result.get("success"):
                log.status = "called"
                called += 1
            else:
                skipped += 1

        except Exception as e:
            skipped += 1
            continue

    db.commit()

    return {
        "success": True,
        "called": called,
        "skipped": skipped,
    }