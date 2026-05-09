import os
import logging
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db, SessionLocal
from services.security import require_api_key

logger = logging.getLogger(__name__)

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
                "name": "LeadGen Pro Max",
                "price": 199,
                "currency": "GBP",
                "leads_per_month": 50,
                "description": "For established commercial plumbing operations",
                "features": ["50 verified leads per month", "Dedicated support", "Lead details on                         reply", "Follow-up sequences", "Voice call alerts"],
            },
            {
                "id": "enterprise",
                "name": "LeadGen Enterprise",
                "price": 349,
                "currency": "GBP",
                "leads_per_month": 100,
                "description": "For large commercial plumbing companies",
                "features": ["100 verified leads per month", "Dedicated account manager", "Priority             lead matching", "Follow-up sequences", "Voice call alerts", "Custom reporting"],
},        ]
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
                plumber.stripe_customer_id = customer_id
                plumber.subscription_plan = plan
                plumber.subscription_active = 1
                db.commit()
                from services.lead_delivery import deliver_leads_to_plumber
                result = deliver_leads_to_plumber(db, int(plumber_id), plan)
                logger.info(f"Lead delivery result: {result}")

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


@router.post("/deliver-leads/{plumber_id}", dependencies=[Depends(require_api_key)])
def manual_deliver_leads(plumber_id: int, plan: str = "basic", db: Session = Depends(get_db)):
    from services.lead_delivery import deliver_leads_to_plumber
    return deliver_leads_to_plumber(db, plumber_id, plan)


@router.get("/delivery-history/{plumber_id}", dependencies=[Depends(require_api_key)])
def get_delivery_history(plumber_id: int, db: Session = Depends(get_db)):
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


@router.get("/active-subscribers", dependencies=[Depends(require_api_key)])
def get_active_subscribers(db: Session = Depends(get_db)):
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