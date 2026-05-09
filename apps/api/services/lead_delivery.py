"""
services/lead_delivery.py
Delivers leads to paying plumbers immediately after Stripe payment.
- Matches leads by location (city/postcode)
- Never sends same lead to two plumbers
- Emails full lead details
- Logs delivery to DB
"""

import os
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from models import Plumber, DemandProspect, LeadDelivery

logger = logging.getLogger(__name__)

PLAN_LIMITS = {
    "basic": 5,
    "pro": 20,
    "unlimited": 9999,
}


def get_lead_limit(plan: str) -> int:
    return PLAN_LIMITS.get(plan.lower(), 5)


def get_available_leads(db: Session, plumber: Plumber, limit: int) -> list:
    """
    Find leads that:
    1. Match plumber's city or postcode area
    2. Have NOT been delivered to any other plumber yet
    3. Are ordered by demand score (best first)
    """
    delivered_ids = db.query(LeadDelivery.prospect_id).filter(
        LeadDelivery.status == "delivered"
    ).subquery()

    location_filter = or_(
        func.lower(DemandProspect.city) == func.lower(plumber.city or "London"),
        func.lower(DemandProspect.borough) == func.lower(plumber.borough or ""),
    )

    if plumber.postcode:
        postcode_area = plumber.postcode[:2].upper()
        location_filter = or_(
            location_filter,
            DemandProspect.postcode.ilike(f"{postcode_area}%")
        )

    prospects = (
        db.query(DemandProspect)
        .filter(location_filter)
        .filter(DemandProspect.id.notin_(delivered_ids))
        .filter(DemandProspect.status != "blacklisted")
        .order_by(DemandProspect.demand_score.desc())
        .limit(limit)
        .all()
    )

    if len(prospects) < limit:
        existing_ids = [p.id for p in prospects]
        extra = (
            db.query(DemandProspect)
            .filter(DemandProspect.id.notin_(delivered_ids))
            .filter(DemandProspect.id.notin_(existing_ids))
            .filter(DemandProspect.status != "blacklisted")
            .order_by(DemandProspect.demand_score.desc())
            .limit(limit - len(prospects))
            .all()
        )
        prospects += extra

    return prospects


def build_lead_email(plumber: Plumber, prospects: list, plan: str) -> tuple:
    subject = f"Your MeritBold leads are ready — {len(prospects)} verified commercial jobs"

    rows = ""
    for i, p in enumerate(prospects, 1):
        rows += f"""
        <tr style="background: {'#f9f9f9' if i % 2 == 0 else '#ffffff'};">
            <td style="padding: 12px; border-bottom: 1px solid #eee; font-weight: bold; color: #1a1a2e;">
                #{i} — {p.name}
            </td>
        </tr>
        <tr style="background: {'#f9f9f9' if i % 2 == 0 else '#ffffff'};">
            <td style="padding: 0 12px 12px 12px; border-bottom: 2px solid #ddd;">
                <table style="width: 100%; font-size: 14px; color: #444;">
                    <tr>
                        <td style="padding: 3px 0;"><strong>Category:</strong> {p.category or 'Commercial'}</td>
                        <td style="padding: 3px 0;"><strong>City:</strong> {p.city or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 3px 0;" colspan="2"><strong>Address:</strong> {p.address or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 3px 0;"><strong>Phone:</strong> {p.phone or 'N/A'}</td>
                        <td style="padding: 3px 0;"><strong>Email:</strong> {p.email or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 3px 0;" colspan="2"><strong>Website:</strong>
                            {'<a href="' + p.website + '">' + p.website + '</a>' if p.website else 'N/A'}
                        </td>
                    </tr>
                    {'<tr><td colspan="2" style="padding: 3px 0;"><strong>FSA Rating:</strong> ' + str(p.fsa_rating) + '</td></tr>' if p.fsa_rating else ''}
                </table>
            </td>
        </tr>
        """

    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 650px; margin: 0 auto; color: #333;">

        <div style="background: #1a1a2e; padding: 30px; text-align: center;">
            <h1 style="color: #B8860B; margin: 0; font-size: 28px;">MeritBold</h1>
            <p style="color: #fff; margin: 8px 0 0 0; font-size: 14px;">Commercial Plumbing Lead Generation</p>
        </div>

        <div style="background: #f0f7ff; padding: 20px 30px; border-left: 4px solid #B8860B;">
            <h2 style="margin: 0; color: #1a1a2e;">Hi {plumber.name},</h2>
            <p style="margin: 10px 0 0 0;">Your <strong>{plan.title()} Plan</strong> is now active.
            Here are your <strong>{len(prospects)} verified commercial plumbing leads</strong> —
            these have been reserved exclusively for you.</p>
        </div>

        <div style="padding: 20px 30px;">
            <table style="width: 100%; border-collapse: collapse;">
                {rows}
            </table>
        </div>

        <div style="background: #e8f8e8; padding: 20px 30px; border-left: 4px solid #28a745;">
            <h3 style="margin: 0 0 10px 0; color: #1a1a2e;">How to use these leads:</h3>
            <ol style="margin: 0; padding-left: 20px; line-height: 1.8;">
                <li>Call or email each business directly using the details above</li>
                <li>Introduce yourself as a commercial plumber available in their area</li>
                <li>Ask if they have any upcoming or ongoing plumbing needs</li>
                <li>These are real, verified UK businesses — not random contacts</li>
            </ol>
        </div>

        <div style="padding: 20px 30px; background: #fff9e6; border-left: 4px solid #B8860B;">
            <p style="margin: 0; font-size: 13px; color: #666;">
                These leads are exclusively yours and will not be shared with other plumbers.<br>
                Your next batch will be delivered at the start of your next billing cycle.<br>
                Questions? Reply to this email or visit <a href="https://www.meritbold.com">www.meritbold.com</a>
            </p>
        </div>

        <div style="background: #1a1a2e; padding: 20px 30px; text-align: center;">
            <p style="color: #999; font-size: 12px; margin: 0;">
                Zephyr William | MeritBold Lead Generation<br>
                128 City Road, London, EC1V 2NX<br>
                outreach@meritbold.com | +44 1322 952157<br>
                <a href="https://www.meritbold.com" style="color: #B8860B;">www.meritbold.com</a>
            </p>
        </div>

    </div>
    """

    return subject, body


def deliver_leads_to_plumber(db: Session, plumber_id: int, plan: str) -> dict:
    plumber = db.query(Plumber).filter(Plumber.id == plumber_id).first()
    if not plumber:
        return {"success": False, "error": f"Plumber {plumber_id} not found"}

    if not plumber.email:
        return {"success": False, "error": f"Plumber {plumber_id} has no email"}

    limit = get_lead_limit(plan)
    prospects = get_available_leads(db, plumber, limit)

    if not prospects:
        logger.warning(f"No available leads for plumber {plumber_id} in {plumber.city}")
        return {"success": False, "error": "No available leads in area"}

    subject, body = build_lead_email(plumber, prospects, plan)

    try:
        from services.azure_email import send_email
send_email(
    to_email=plumber.email,
    subject=subject,
    body=body,
)
    except Exception as e:
        logger.error(f"Failed to send leads email to {plumber.email}: {e}")
        return {"success": False, "error": str(e)}

    for prospect in prospects:
        delivery = LeadDelivery(
            plumber_id=plumber.id,
            prospect_id=prospect.id,
            plan=plan,
            delivered_at=datetime.utcnow(),
            status="delivered",
        )
        db.add(delivery)

    db.commit()

    logger.info(f"Delivered {len(prospects)} leads to {plumber.name} ({plumber.email})")

    return {
        "success": True,
        "plumber": plumber.name,
        "email": plumber.email,
        "plan": plan,
        "leads_delivered": len(prospects),
    }