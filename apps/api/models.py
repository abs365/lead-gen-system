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
    match_id = Column(Integer, ForeignKey("matches.id"))
    plumber_id = Column(Integer, ForeignKey("plumbers.id"))

    tracking_id = Column(String(255), index=True)
    opened = Column(Integer, default=0)
    clicked = Column(Integer, default=0)

    email = Column(String)
    subject = Column(String)
    body = Column(Text)  # FIXED

    status = Column(String)
    error_message = Column(String, nullable=True)

    sent_at = Column(DateTime, default=_utcnow)


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

    place_id = Column(String(255), unique=True, index=True, nullable=True)
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
    created_at = Column(DateTime, default=_utcnow)

    demand_prospect = relationship("DemandProspect", back_populates="matches")
    plumber = relationship("Plumber", back_populates="matches")


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