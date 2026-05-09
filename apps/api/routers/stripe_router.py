import logging
import os
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db, SessionLocal
from services.security import require_api_key

router = APIRouter(prefix="/stripe", tags=["stripe"])


class CheckoutRequest(BaseModel):
    plan: str
    plumber_email: str
    plumber_id: int


@router.post("/create-checkout")
def create_checkout(data: CheckoutRequest):
    from services.stripe_service import create_checkout_session
    result = create_checkout_session(
        plan=data.plan,
        plumber_email=data.plumber_email,
        plumber_id=data.plumber_id,
    )
    return result


@router.get("/plans")
def get_plans():
    return {
        "plans": [
            {
                "id": "basic",
                "name": "LeadGen Basic",
                "price": 49,
                "currency": "GBP",
                "leads_per_month": 5,
                "description": "Perfect for small plumbing businesses",
                "features": ["5 verified leads per month", "Email support", "Lead details on reply"],
            },
            {
                "id": "pro",
                "name": "LeadGen Pro",
                "price": 99,
                "currency": "GBP",
                "leads_per_month": 20,
                "description": "For growing plumbing companies",
                "features": ["20 verified leads per month", "Priority support", "Lead details on reply", "Follow-up sequences"],
            },
            {
                "id": "unlimited",
                "name": "LeadGen Unlimited",
                "price": 199,
                "currency": "GBP",
                "leads_per_month": 999,
                "description": "For large commercial plumbing operations",
                "features": ["Unlimited leads per month", "Dedicated support", "Lead details on reply", "Follow-up sequences", "Voice call alerts"],
            },
        ]
    }


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    from services.stripe_service import handle_webhook
    result = handle_webhook(payload, sig_header)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))

    event_type = result.get("type")
    data = result.get("data", {})

    """
UPDATE to apps/api/routers/stripe_router.py
Replace the checkout.session.completed block with this updated version.
It now triggers lead delivery immediately after payment.
"""

# In the stripe_webhook function, replace this block:
#
#    if event_type == "checkout.session.completed":
#        ... (existing code) ...
#
# With this:

    if event_type == "checkout.session.completed":
        session = data.get("object", {})
        plumber_id = session.get("metadata", {}).get("plumber_id")
        plan = session.get("metadata", {}).get("plan", "basic")
        customer_id = session.get("customer")

        if plumber_id:
            from models import Plumber
            plumber = db.query(Plumber).filter(
                Plumber.id == int(plumber_id)
            ).first()

            if plumber:
                # Update subscription status
                plumber.stripe_customer_id = customer_id
                plumber.subscription_plan = plan
                plumber.subscription_active = 1
                db.commit()

                # Deliver leads immediately
                from services.lead_delivery import deliver_leads_to_plumber
                result = deliver_leads_to_plumber(db, int(plumber_id), plan)
                logger.info(f"Lead delivery result: {result}")


        if plumber_id:
            from models import Plumber
            plumber = db.query(Plumber).filter(
                Plumber.id == int(plumber_id)
            ).first()
            if plumber:
                plumber.stripe_customer_id = customer_id
                plumber.subscription_plan = plan
                plumber.subscription_active = 1
                db.commit()

    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("object", {}).get("customer")
        if customer_id:
            from models import Plumber
            plumber = db.query(Plumber).filter(
                Plumber.stripe_customer_id == customer_id
            ).first()
            if plumber:
                plumber.subscription_active = 0
                plumber.subscription_plan = None
                db.commit()

    return {"success": True}

"""
ADD these endpoints to apps/api/routers/stripe_router.py or a new leads_router.py
These allow manual lead delivery and checking delivery status.
"""

import logging
logger = logging.getLogger(__name__)

# Manual trigger — deliver leads to a specific plumber (for testing or manual override)
@router.post("/deliver-leads/{plumber_id}", dependencies=[Depends(require_api_key)])
def manual_deliver_leads(plumber_id: int, plan: str = "basic", db: Session = Depends(get_db)):
    """
    Manually trigger lead delivery to a plumber.
    Useful for: testing, manual overrides, re-delivery after issues.
    """
    from services.lead_delivery import deliver_leads_to_plumber
    result = deliver_leads_to_plumber(db, plumber_id, plan)
    return result


# Check delivery history for a plumber
@router.get("/delivery-history/{plumber_id}", dependencies=[Depends(require_api_key)])
def get_delivery_history(plumber_id: int, db: Session = Depends(get_db)):
    """
    Get all leads delivered to a specific plumber.
    """
    from models import LeadDelivery, DemandProspect
    deliveries = (
        db.query(LeadDelivery, DemandProspect)
        .join(DemandProspect, LeadDelivery.prospect_id == DemandProspect.id)
        .filter(LeadDelivery.plumber_id == plumber_id)
        .order_by(LeadDelivery.delivered_at.desc())
        .all()
    )

    return {
        "plumber_id": plumber_id,
        "total_delivered": len(deliveries),
        "leads": [
            {
                "id": d.LeadDelivery.id,
                "business_name": d.DemandProspect.name,
                "category": d.DemandProspect.category,
                "city": d.DemandProspect.city,
                "address": d.DemandProspect.address,
                "phone": d.DemandProspect.phone,
                "email": d.DemandProspect.email,
                "website": d.DemandProspect.website,
                "delivered_at": d.LeadDelivery.delivered_at,
                "status": d.LeadDelivery.status,
            }
            for d in deliveries
        ]
    }


# Get all active subscribers
@router.get("/active-subscribers", dependencies=[Depends(require_api_key)])
def get_active_subscribers(db: Session = Depends(get_db)):
    """
    Get all plumbers with active subscriptions.
    """
    from models import Plumber
    subscribers = db.query(Plumber).filter(
        Plumber.subscription_active == 1
    ).all()

    return {
        "total": len(subscribers),
        "subscribers": [
            {
                "id": p.id,
                "name": p.name,
                "email": p.email,
                "city": p.city,
                "plan": p.subscription_plan,
                "stripe_customer_id": p.stripe_customer_id,
            }
            for p in subscribers
        ]
    }
