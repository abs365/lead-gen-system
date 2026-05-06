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

    if event_type == "checkout.session.completed":
        session = data.get("object", {})
        plumber_id = session.get("metadata", {}).get("plumber_id")
        plan = session.get("metadata", {}).get("plan")
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