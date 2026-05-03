from datetime import datetime
from models import DemandProspect
from models import OutreachLog


def calculate_lead_score(lead):
    score = 0

    if lead.email:
        score += 20

    if lead.opened:
        score += 20

    if lead.replied:
        score += 40

    if lead.status == "interested":
        score += 20

    if lead.estimated_value >= 200:
        score += 20

    return min(score, 100)

# ---------------------------------------------------------------------------
# DATE PARSING
# ---------------------------------------------------------------------------

def parse_date_safe(value):
    if not value:
        return None

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%d %B %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue

    return None


# ---------------------------------------------------------------------------
# FRESHNESS
# ---------------------------------------------------------------------------

def calculate_freshness_multiplier(date_value):
    dt = parse_date_safe(date_value)

    if not dt:
        return 1.0, "freshness_unknown:+0%"

    days_old = (datetime.utcnow() - dt).days

    if days_old <= 7:
        return 1.25, "freshness_0_7_days:+25%"
    elif days_old <= 30:
        return 1.10, "freshness_8_30_days:+10%"
    elif days_old <= 90:
        return 1.00, "freshness_31_90_days:+0%"
    else:
        return 0.85, "freshness_90_plus_days:-15%"


# ---------------------------------------------------------------------------
# DEMAND SCORE
# ---------------------------------------------------------------------------

def calculate_demand_score(signals, source, inspection_date=None):
    base_score = 0
    breakdown = []

    for signal in signals:
        if signal == "new_food_business":
            base_score += 30
            breakdown.append("new_food_business:+30")

        elif signal == "high_water_usage":
            base_score += 20
            breakdown.append("high_water_usage:+20")

        elif signal == "no_website":
            base_score += 10
            breakdown.append("no_website:+10")

        elif signal == "new_company":
            base_score += 25
            breakdown.append("new_company:+25")

    if source == "fsa":
        base_score += 10
        breakdown.append("source_fsa:+10")

    elif source == "companies_house":
        base_score += 15
        breakdown.append("source_companies_house:+15")

    freshness_multiplier, freshness_reason = calculate_freshness_multiplier(inspection_date)
    breakdown.append(freshness_reason)

    final_score = int(round(base_score * freshness_multiplier))

    # HARD CAP
    final_score = min(final_score, 100)

    return final_score, ",".join(breakdown)


# ---------------------------------------------------------------------------
# HIGH PRIORITY FLAG (TOP 10%)
# ---------------------------------------------------------------------------

def assign_high_priority_flags(db):
    prospects = db.query(DemandProspect)\
        .order_by(DemandProspect.demand_score.desc())\
        .all()

    if not prospects:
        return

    total = len(prospects)
    cutoff = max(1, int(total * 0.1))

    for i, p in enumerate(prospects):
        if hasattr(p, "is_high_priority"):
            p.is_high_priority = 1 if i < cutoff else 0

    db.commit()