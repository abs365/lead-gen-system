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
}

SIGNATURE = """Best,

Abi Lawrence
Team LeadGen
Merit-Bold Lead Generation
128 City Road, London, United Kingdom, EC1V 2NX"""

FOOTER = "<p style='font-size:11px;color:#999;'>This email was sent under UK PECR legitimate interest provisions. To unsubscribe, reply with the word UNSUBSCRIBE and we will remove you immediately.</p>"


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

    prompt = f"""Write a short cold outreach email from Abi Lawrence at Merit-Bold Lead Generation to a plumbing company.

Details:
- Plumber: {plumber_name}
- Prospect business: {prospect_name}
- Business type: {business_type}
- Location: {address}, {city}

Use this exact format and structure:

Hi {plumber_name},

We help connect plumbing companies with commercial property leads in [city].

We recently identified a [business type] in [area of city or postcode district only] that may need commercial plumbing support.

If you'd like the full contact details including business name and address, reply YES and I'll send them over.

If you'd prefer not to receive these emails, just reply unsubscribe.

Best,

Abi Lawrence
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
                "messages": [
                    {"role": "user", "content": prompt}
                ],
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
) -> str:
    city = prospect_city or "London"
    business_type = _get_business_type(prospect_name, prospect_category)
    address = prospect_address or city

    claude_body = generate_outreach_email(
        plumber_name=plumber_name,
        prospect_name=prospect_name,
        prospect_category=prospect_category,
        prospect_city=city,
        prospect_address=address,
    )

    if claude_body:
        body_content = claude_body
    else:
        body_content = f"""Hi {plumber_name or 'there'},

We help connect plumbing companies with commercial property leads in {city}.

We recently identified a {business_type} in {city} that may need commercial plumbing support.

If you'd like the full contact details including business name and address, reply YES and I'll send them over.

If you'd prefer not to receive these emails, just reply unsubscribe.

{SIGNATURE}"""

    body_html = f"<p>{body_content.replace(chr(10), '</p><p>')}</p><br>{FOOTER}"
    return body_html