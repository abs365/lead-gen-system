def predict_close_probability(lead):
    score = 0

    if lead.replied:
        score += 50

    if lead.opened:
        score += 20

    if lead.follow_up_step >= 2:
        score += 20

    if lead.status == "interested":
        score += 40

    return min(score, 100)


def enhanced_estimated_value(lead):
    value = 0

    # base value from previous system
    if lead.email and not any(x in lead.email for x in ["gmail", "yahoo", "outlook"]):
        value += 150

    if lead.opened:
        value += 50

    if lead.replied:
        value += 200

    # NEW: intent multiplier
    if lead.status == "interested":
        value += 200

    # NEW: follow-up depth
    if lead.follow_up_step >= 2:
        value += 100

    return value