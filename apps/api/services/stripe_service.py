import os
import stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRICE_IDS = {
    "basic": os.getenv("STRIPE_PRICE_BASIC"),
    "pro": os.getenv("STRIPE_PRICE_PRO"),
    "unlimited": os.getenv("STRIPE_PRICE_UNLIMITED"),
    "promax": os.getenv("STRIPE_PRICE_PROMAX"),
    "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE"),
}

PLAN_LIMITS = {
    "basic": 5,
    "pro": 20,
    "unlimited": 50,
    "promax": 50,
    "enterprise": 100,
}

def create_checkout_session(plan: str, plumber_email: str, plumber_id: int) -> dict:
    price_id = PRICE_IDS.get(plan)
    if not price_id:
        return {"success": False, "message": f"Invalid plan: {plan}"}
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=plumber_email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url="https://lead-gen-system-azure.vercel.app/subscribe/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://lead-gen-system-azure.vercel.app/subscribe/cancel",
            metadata={
                "plumber_id": str(plumber_id),
                "plan": plan,
            },
        )
        return {"success": True, "checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        return {"success": False, "message": str(e)}

def get_subscription_status(stripe_customer_id: str) -> dict:
    try:
        subscriptions = stripe.Subscription.list(customer=stripe_customer_id, limit=1)
        if not subscriptions.data:
            return {"active": False, "plan": None}
        sub = subscriptions.data[0]
        price_id = sub["items"]["data"][0]["price"]["id"]
        plan = None
        for plan_name, pid in PRICE_IDS.items():
            if pid == price_id:
                plan = plan_name
                break
        return {
            "active": sub.status == "active",
            "plan": plan,
            "leads_limit": PLAN_LIMITS.get(plan, 0),
            "status": sub.status,
        }
    except Exception as e:
        return {"active": False, "plan": None, "message": str(e)}

def handle_webhook(payload: bytes, sig_header: str) -> dict:
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        return {"success": False, "message": str(e)}
    return {"success": True, "type": event["type"], "data": event["data"]}