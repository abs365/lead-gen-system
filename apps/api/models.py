from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    Text, Float, Boolean
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


def _utcnow():
    return datetime.utcnow()


# --------------------------------------------------------------------------- #
# Outreach Log
# --------------------------------------------------------------------------- #

class OutreachLog(Base):
    __tablename__ = "outreach_logs"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    subject = Column(String)

    opened = Column(Integer, default=0)
    clicked = Column(Integer, default=0)

    sent_at = Column(DateTime)

    follow_up_step = Column(Integer, default=0)
    last_contacted_at = Column(DateTime)

    lead_score = Column(Integer, default=0)
    replied = Column(Integer, default=0)

    status = Column(String, default="new")

    deal_value = Column(Integer, default=0)
    estimated_value = Column(Integer, default=0)
    close_probability = Column(Integer, default=0)

    auto_replied = Column(Integer, default=0)


# --------------------------------------------------------------------------- #
# Plumbers
# --------------------------------------------------------------------------- #

class Plumber(Base):
    __tablename__ = "plumbers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    address = Column(Text)
    postcode = Column(String(20))
    city = Column(String(100), default="London")
    borough = Column(String(100))

    website = Column(String(500))
    email = Column(String(255))
    phone = Column(String(50))

    lat = Column(Float)
    lng = Column(Float)

    place_id = Column(String(255), unique=True, index=True)
    source = Column(String(100), default="google_places")
    category = Column(String(100), default="plumber")

    is_commercial = Column(Integer, default=0)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    matches = relationship("Match", back_populates="plumber", cascade="all, delete-orphan")


# --------------------------------------------------------------------------- #
# Demand Prospects
# --------------------------------------------------------------------------- #

class DemandProspect(Base):
    __tablename__ = "demand_prospects"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    category = Column(String(100))

    address = Column(Text)
    city = Column(String(100), default="London")
    borough = Column(String(100))
    postcode = Column(String(20))

    website = Column(String(500))
    email = Column(String(255))
    phone = Column(String(50))

    source = Column(String(100))
    source_record_id = Column(String(255), index=True)

    fsa_establishment_id = Column(String(100), unique=True, index=True)
    fsa_rating = Column(String(50))
    last_inspection_date = Column(String)

    demand_score = Column(Integer, default=0)
    score_breakdown = Column(Text)
    status = Column(String(50), default="new")

    is_high_priority = Column(Integer, default=0)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    signals = relationship("ProspectSignal", back_populates="prospect", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="demand_prospect", cascade="all, delete-orphan")


# --------------------------------------------------------------------------- #
# Prospect Signals
# --------------------------------------------------------------------------- #

class ProspectSignal(Base):
    __tablename__ = "prospect_signals"

    id = Column(Integer, primary_key=True, index=True)

    prospect_id = Column(Integer, ForeignKey("demand_prospects.id", ondelete="CASCADE"))

    signal_type = Column(String(100))
    signal_source = Column(String(100))
    signal_strength = Column(String(50))

    signal_data = Column(Text)

    freshness_score = Column(Float)
    detected_at = Column(DateTime, default=_utcnow)

    processed = Column(Boolean, default=False)

    prospect = relationship("DemandProspect", back_populates="signals")


# --------------------------------------------------------------------------- #
# Matching
# --------------------------------------------------------------------------- #

class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)

    demand_prospect_id = Column(
        Integer,
        ForeignKey("demand_prospects.id", ondelete="CASCADE"),
        nullable=False,
    )

    plumber_id = Column(
        Integer,
        ForeignKey("plumbers.id", ondelete="CASCADE"),
        nullable=False,
    )

    match_score = Column(Integer, default=0)
    match_reason = Column(Text)

    outreach_sent = Column(Integer, default=0)
    outreach_sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=_utcnow)

    demand_prospect = relationship("DemandProspect", back_populates="matches")
    plumber = relationship("Plumber", back_populates="matches")


# --------------------------------------------------------------------------- #
# Opportunities (CLEAN VERSION)
# --------------------------------------------------------------------------- #

class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True)

    business_name = Column(String, nullable=False)
    category = Column(String)
    location = Column(String)

    issue_detected = Column(String, nullable=False)
    urgency_score = Column(Integer, default=0)
    estimated_value = Column(Integer, default=0)
    is_interested = Column(Integer, default=0)

    status = Column(String, default="new")

    plumber_id = Column(Integer)

    created_at = Column(DateTime, default=_utcnow)
    sent_at = Column(DateTime)
    accepted_at = Column(DateTime)


# --------------------------------------------------------------------------- #
# Job Logs
# --------------------------------------------------------------------------- #

class JobLog(Base):
    __tablename__ = "job_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String(100))
    status = Column(String(50))
    message = Column(Text)
    records_processed = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)

    active_imap_email = Column(String(255), nullable=True)
    active_imap_password = Column(String(500), nullable=True)
    active_imap_host = Column(String(255), nullable=True)
    active_imap_port = Column(Integer, default=993)

    active_smtp_email = Column(String(255), nullable=True)
    active_smtp_password = Column(String(500), nullable=True)
    active_smtp_host = Column(String(255), nullable=True)
    active_smtp_port = Column(Integer, default=587)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

"""
Add this to models.py — the LeadDelivery table tracks which leads
have been sent to which plumber. This prevents duplicate delivery.
"""

# Add this import at the top of models.py (already there):
# from sqlalchemy import Column, Integer, String, DateTime, ForeignKey

class LeadDelivery(Base):
    __tablename__ = "lead_deliveries"

    id = Column(Integer, primary_key=True, index=True)

    plumber_id = Column(Integer, ForeignKey("plumbers.id", ondelete="CASCADE"), nullable=False)
    prospect_id = Column(Integer, ForeignKey("demand_prospects.id", ondelete="CASCADE"), nullable=False)

    plan = Column(String(50))  # basic, pro, unlimited
    delivered_at = Column(DateTime, default=_utcnow)
    status = Column(String(50), default="delivered")  # delivered, bounced, clicked

    # Track if plumber viewed/acted on this lead
    opened = Column(Integer, default=0)
    contacted = Column(Integer, default=0)  # plumber marked as contacted
    converted = Column(Integer, default=0)  # plumber got the job
