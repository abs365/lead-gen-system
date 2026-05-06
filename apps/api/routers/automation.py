from fastapi import APIRouter, Depends
from services.security import require_api_key
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database import SessionLocal
from models import OutreachLog, Match, Plumber, DemandProspect
from services.email import send_email
from services.deal_intelligence import enhanced_estimated_value, predict_close_probability

router = APIRouter(
    prefix="/automation",
    tags=["automation"],
    dependencies=[Depends(require_api_key)]
)


# --------------------------------------------------------------------------- #
# DB SESSION
# --------------------------------------------------------------------------- #

def get_db():
    return SessionLocal()


# --------------------------------------------------------------------------- #
# LEAD SCORING
# --------------------------------------------------------------------------- #

def calculate_lead_score(lead):
    score = 0

    if lead.email:
        if any(x in lead.email for x in ["gmail", "yahoo", "outlook"]):
            score += 10
        else:
            score += 50

    if lead.subject and len(lead.subject) > 10:
        score += 20

    if lead.opened:
        score += 40

    if lead.follow_up_step >= 1:
        score += 10

    return score


# --------------------------------------------------------------------------- #
# MATCH-BASED OUTREACH
# --------------------------------------------------------------------------- #

@router.post("/send-match-outreach")
def send_match_outreach():
    db: Session = get_db()
    sent = 0
    skipped = 0
    errors = []

    try:
        # Get all unsent matches with score >= 60, ordered by score
        all_matches = (
            db.query(Match, DemandProspect, Plumber)
            .join(DemandProspect, Match.demand_prospect_id == DemandProspect.id)
            .join(Plumber, Match.plumber_id == Plumber.id)
            .filter(Match.outreach_sent == 0)
            .filter(Match.match_score >= 60)
            .filter(Plumber.email.isnot(None))
            .order_by(Match.match_score.desc())
            .all()
        )

        # Cap at 3 matches per plumber
        plumber_counts = {}
        selected = []
        for match, demand, plumber in all_matches:
            count = plumber_counts.get(plumber.id, 0)
            if count < 3:
                selected.append((match, demand, plumber))
                plumber_counts[plumber.id] = count + 1

        for match, demand, plumber in selected:
            if not plumber.email:
                skipped += 1
                continue

            try:
                subject = f"New plumbing job opportunity — {demand.city or 'London'}"

                body = f"""
                <p>Hi {plumber.name or 'there'},</p>
                <p>We found a business in {demand.city or 'your area'} that likely needs commercial plumbing support:</p>
                <p><strong>{demand.name}</strong> ({demand.category or 'Business'})<br>
                Location: {demand.address or demand.city or 'London'}</p>
                <p>Reply <strong>YES</strong> and we will send the full contact details over.</p>
                <p>— MeritBold Lead Generation<br>
                generalenquiry@meritbold.com</p>
                <hr>
                <p style="font-size:11px;color:#999;">
                You are receiving this because your business offers plumbing services in {demand.city or 'your area'}.
                This is a legitimate business opportunity email sent under UK PECR legitimate interest provisions.
                To unsubscribe and stop receiving emails, reply with the word STOP and we will remove you immediately.
                MeritBold, United Kingdom.
                </p>
                """

                send_email(
                    to_email=plumber.email,
                    subject=subject,
                    body=body
                )

                match.outreach_sent = 1
                match.outreach_sent_at = datetime.utcnow()
                sent += 1

            except Exception as e:
                skipped += 1
                errors.append(str(e))

        db.commit()

        return {
            "status": "match outreach complete",
            "sent": sent,
            "skipped": skipped,
            "errors": errors[:5],
        }

    finally:
        db.close()

# --------------------------------------------------------------------------- #
# STANDARD OUTREACH + FOLLOW-UP
# (also called by scheduler — must be callable without HTTP context)
# --------------------------------------------------------------------------- #

def run_outreach_job():
    """
    Scheduler-safe version — creates its own DB session.
    Called directly by APScheduler.
    """
    db: Session = SessionLocal()
    now = datetime.utcnow()
    sent_count = 0
    MAX_SEND = 10

    try:
        leads = db.query(OutreachLog).all()

        for lead in leads:

            if sent_count >= MAX_SEND:
                break

            try:
                # AUTO PIPELINE
                if lead.opened and lead.status == "new":
                    lead.status = "contacted"

                if lead.replied and lead.status in ["new", "contacted"]:
                    lead.status = "interested"

                # SCORING + INTELLIGENCE
                lead.lead_score = calculate_lead_score(lead)
                lead.estimated_value = enhanced_estimated_value(lead)
                lead.close_probability = predict_close_probability(lead)

                # SMART FILTERING
                if lead.lead_score < 50:
                    continue

                if lead.estimated_value < 100:
                    continue

                if lead.close_probability < 0.3:
                    continue

                if not lead.email:
                    continue

                if any(x in lead.email for x in ["gmail", "yahoo", "outlook"]):
                    continue

                # FIRST EMAIL
                if lead.sent_at is None:
                    send_email(
                        lead.email,
                        lead.subject,
                        f"""
                        <p>Hi {lead.email.split('@')[0]},</p>
                        <p>We connect plumbing companies with high-intent local jobs.</p>
                        <p>Interested in receiving a few jobs weekly?</p>
                        <p>Reply YES.</p>
                        """
                    )

                    lead.sent_at = now
                    lead.last_contacted_at = now
                    lead.follow_up_step = 1
                    lead.status = "contacted"
                    sent_count += 1

                # FOLLOW-UP 1
                elif (
                    lead.follow_up_step == 1
                    and lead.last_contacted_at
                    and now - lead.last_contacted_at > timedelta(days=2)
                ):
                    send_email(
                        lead.email,
                        f"Re: {lead.subject}",
                        "<p>Just checking if you saw my previous message.</p>"
                    )

                    lead.last_contacted_at = now
                    lead.follow_up_step = 2
                    sent_count += 1

                # FOLLOW-UP 2
                elif (
                    lead.follow_up_step == 2
                    and lead.last_contacted_at
                    and now - lead.last_contacted_at > timedelta(days=5)
                ):
                    send_email(
                        lead.email,
                        f"Re: {lead.subject}",
                        "<p>Quick follow-up — happy to send details.</p>"
                    )

                    lead.last_contacted_at = now
                    lead.follow_up_step = 3
                    sent_count += 1

                # FINAL FOLLOW-UP
                elif (
                    lead.follow_up_step == 3
                    and lead.last_contacted_at
                    and now - lead.last_contacted_at > timedelta(days=10)
                ):
                    send_email(
                        lead.email,
                        f"Final follow-up: {lead.subject}",
                        "<p>Last message — let me know if interested.</p>"
                    )

                    lead.last_contacted_at = now
                    lead.follow_up_step = 4
                    sent_count += 1

            except Exception as e:
                print("Email error:", e)

        db.commit()
        print(f"[Outreach job] sent: {sent_count}")

    finally:
        db.close()


@router.get("/send-outreach")
def send_outreach():
    """HTTP endpoint — delegates to the scheduler-safe job function."""
    run_outreach_job()
    return {
        "status": "automation run",
        "timestamp": datetime.utcnow().isoformat()
    }


# --------------------------------------------------------------------------- #
# FOLLOW-UP HOT LEADS
# --------------------------------------------------------------------------- #

@router.get("/follow-up-hot-leads")
def follow_up_hot_leads():
    db: Session = get_db()
    sent = 0

    try:
        leads = db.query(OutreachLog).filter(OutreachLog.replied == 1).all()

        for lead in leads:
            try:
                if lead.status != "interested":
                    continue

                subject = f"Next steps — {lead.subject}"

                body = f"""
                <p>Hi {lead.email.split('@')[0]},</p>
                <p>Great — thanks for your reply.</p>
                <p>We currently have <strong>live plumbing job opportunities</strong> in your area.</p>
                <p>Reply with your availability or preferred contact number and we will connect you directly.</p>
                <p>— MeritBold Lead Generation<br>
                generalenquiry@meritbold.com</p>
                <hr>
                <p style="font-size:11px;color:#999;">
                To unsubscribe, reply with STOP and we will remove you immediately.
                MeritBold, United Kingdom.
                </p>
                """

                send_email(
                    to_email=lead.email,
                    subject=subject,
                    body=body
                )

                sent += 1

            except Exception as e:
                print("Follow-up error:", e)

        return {
            "status": "follow-up sent",
            "emails_sent": sent
        }

    finally:
        db.close()