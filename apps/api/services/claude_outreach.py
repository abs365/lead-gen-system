"""
Claude-powered outreach email builder.
Detects tender vs commercial prospects and builds appropriate emails.
"""
import os
import requests

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

BUSINESS_TYPE_HINTS = {
    "cafe": "cafe or coffee shop",
    "restaurant": "restaurant",
    "hotel": "hotel",
    "takeaway": "takeaway",
    "landlord": "landlord or property owner",
    "facilities": "facilities management company",
    "property maintenance": "property maintenance company",
    "maintenance": "property maintenance company",
    "care home": "care home",
    "nursing home": "nursing home",
    "pub": "pub or bar",
    "gym": "gym or leisure centre",
    "school": "school or academy",
    "office": "commercial office building",
}

SIGNATURE = """Best regards,

Zephyr William
Team LeadGen
Merit-Bold Lead Generation
128 City Road, London, United Kingdom, EC1V 2NX"""

FOOTER = "<p style='font-size:11px;color:#999;'>This email was sent under UK PECR legitimate interest provisions. To unsubscribe, reply UNSUBSCRIBE and we will remove you immediately.</p>"


def _get_business_type(name: str, category: str) -> str:
    name_lower = (name or "").lower()
    for keyword, label in BUSINESS_TYPE_HINTS.items():
        if keyword in name_lower:
            return label
    cat = (category or "").lower()
    for keyword, label in BUSINESS_TYPE_HINTS.items():
        if keyword in cat:
            return label
    return "commercial property"


def _is_tender(category: str, source: str, score_breakdown: str) -> bool:
    """Detect if this is a Contracts Finder tender prospect."""
    cat = (category or "").lower()
    src = (source or "").lower()
    breakdown = (score_breakdown or "").lower()
    return (
        cat == "tender" or
        src == "contracts_finder" or
        "contracts_finder" in breakdown
    )


def _parse_tender_details(score_breakdown: str) -> dict:
    """Extract value and deadline from score_breakdown field."""
    details = {"value": "", "deadline": ""}
    if not score_breakdown:
        return details
    parts = score_breakdown.split("|")
    for part in parts:
        part = part.strip()
        if part.startswith("£"):
            details["value"] = part
        elif part.startswith("Deadline:"):
            details["deadline"] = part.replace("Deadline:", "").strip()
    return details


def generate_tender_email(
    plumber_name: str,
    tender_name: str,
    tender_city: str,
    tender_address: str,
    tender_value: str,
    tender_deadline: str,
) -> str | None:
    if not ANTHROPIC_API_KEY:
        return None

    city = tender_city or "UK"
    value_str = f"worth {tender_value}" if tender_value else ""
    deadline_str = f"closing {tender_deadline}" if tender_deadline else "with an upcoming deadline"

    prompt = f"""Write a short cold outreach email from Zephyr William at Merit-Bold Lead Generation to a plumbing company about a real public sector tender.

Details:
- Plumber: {plumber_name}
- Tender: {tender_name}
- Location: {tender_address}, {city}
- Contract value: {tender_value or 'not specified'}
- Deadline: {tender_deadline or 'upcoming'}

Use this exact format:

Hi {plumber_name},

We've identified a public sector tender in your area that may be a good fit for your business.

The contract is for [brief description of work] in [area], {value_str} and {deadline_str}.

We offer new plumbers 3 free verified commercial leads — no card, no commitment.

Reply FREE and I'll send your first lead today. If you like what you see, we have plans from just £49/month for ongoing leads.

If you'd prefer not to receive these emails, just reply UNSUBSCRIBE.

Best regards,

Zephyr William
Team LeadGen
Merit-Bold Lead Generation
128 City Road, London, United Kingdom, EC1V 2NX

Rules:
- Use the plumber's actual name
- Keep it under 100 words in the body
- Sound natural and direct, not salesy
- The value and deadline create urgency — use them
- No extra commentary, just the email body"""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15,
        )
        if response.status_code != 200:
            return None
        return response.json()["content"][0]["text"].strip()
    except Exception:
        return None


def generate_outreach_email(
    plumber_name: str,
    prospect_name: str,
    prospect_category: str,
    prospect_city: str,
    prospect_address: str,
) -> str | None:
    if not ANTHROPIC_API_KEY:
        return None

    business_type = _get_business_type(prospect_name, prospect_category)
    city = prospect_city or "London"
    address = prospect_address or city

    prompt = f"""Write a short cold outreach email from Zephyr William at Merit-Bold Lead Generation to a plumbing company.

Details:
- Plumber: {plumber_name}
- Prospect business: {prospect_name}
- Business type: {business_type}
- Location: {address}, {city}

Use this exact format:

Hi {plumber_name},

We help connect plumbing companies with commercial property leads in [city].

We recently identified a [business type] in [area of city or postcode district only] that may need commercial plumbing support.

We offer new plumbers 3 free verified commercial leads — no card, no commitment.

Reply FREE and I'll send your first lead today. Plans from just £49/month after your trial.

If you'd prefer not to receive these emails, just reply UNSUBSCRIBE.

Best regards,

Zephyr William
Team LeadGen
Merit-Bold Lead Generation
128 City Road, London, United Kingdom, EC1V 2NX

Rules:
- Use the plumber's actual name
- Use the actual business type and location
- Keep it short and natural
- No extra commentary, just the email body"""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15,
        )
        if response.status_code != 200:
            return None
        return response.json()["content"][0]["text"].strip()
    except Exception:
        return None


def build_email_body(
    plumber_name: str,
    prospect_name: str,
    prospect_category: str,
    prospect_city: str,
    prospect_address: str,
    prospect_source: str = "",
    score_breakdown: str = "",
) -> str:
    city = prospect_city or "London"
    address = prospect_address or city

    # Route to tender email if this is a Contracts Finder tender
    if _is_tender(prospect_category, prospect_source, score_breakdown):
        tender_details = _parse_tender_details(score_breakdown)
        body_text = generate_tender_email(
            plumber_name=plumber_name,
            tender_name=prospect_name,
            tender_city=city,
            tender_address=address,
            tender_value=tender_details["value"],
            tender_deadline=tender_details["deadline"],
        )
        if not body_text:
            # Fallback tender email
            details = _parse_tender_details(score_breakdown)
            value_str = f"worth {details['value']}" if details['value'] else ""
            deadline_str = f"closing {details['deadline']}" if details['deadline'] else "with an upcoming deadline"
            body_text = f"""Hi {plumber_name or 'there'},

We've identified a public sector tender in your area that may be a good fit for your business.

The contract is for work in {city}, {value_str} and {deadline_str}.

We offer new plumbers 3 free verified commercial leads — no card, no commitment.

Reply FREE and I'll send your first tender details today. Plans from just £49/month after your trial.

If you'd prefer not to receive these emails, just reply UNSUBSCRIBE.

{SIGNATURE}"""
    else:
        # Standard commercial prospect email
        body_text = generate_outreach_email(
            plumber_name=plumber_name,
            prospect_name=prospect_name,
            prospect_category=prospect_category,
            prospect_city=city,
            prospect_address=address,
        )
        if not body_text:
            business_type = _get_business_type(prospect_name, prospect_category)
            body_text = f"""Hi {plumber_name or 'there'},

We help connect plumbing companies with commercial property leads in {city}.

We recently identified a {business_type} in {city} that may need commercial plumbing support.

We offer new plumbers 3 free verified commercial leads — no card, no commitment.

Reply FREE and I'll send your first lead today. Plans from just £49/month after your trial.

If you'd prefer not to receive these emails, just reply UNSUBSCRIBE.

{SIGNATURE}"""

    body_html = f"<p>{body_text.replace(chr(10), '</p><p>')}</p><br>{FOOTER}"
    return body_html