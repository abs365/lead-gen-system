def estimate_lead_value(lead):
    value = 0

    # Business email = higher value
    if lead.email and not any(x in lead.email for x in ["gmail", "yahoo", "outlook"]):
        value += 100

    # Strong subject (intent)
    if lead.subject and len(lead.subject) > 10:
        value += 50

    # Engagement signals
    if lead.opened:
        value += 50

    if lead.replied:
        value += 150

    # Follow-up engagement
    if lead.follow_up_step >= 2:
        value += 50

    return value