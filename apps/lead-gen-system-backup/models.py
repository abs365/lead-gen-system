"""
SQLAlchemy ORM models.

Plumber     — buyer side: businesses that may pay for demand-side leads.
DemandProspect — demand side: restaurants/hospitality likely to need plumbing.
Match       — links demand prospects to matching plumbers by area/type.
JobLog      — audit trail for every collection / enrichment run.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey, Index,
)
from sqlalchemy.orm import relationship
from database import Base


def _utcnow():
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Buyer side                                                                   #
# --------------------------------------------------------------------------- #

class Plumber(Base):
    """
    A plumbing business that is a potential buyer / paying client.
    Sourced primarily from Google Places API.
    """
    __tablename__ = "plumbers"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(255), nullable=False)
    address       = Column(Text)
    postcode      = Column(String(20))
    city          = Column(String(100), default="London")
    borough       = Column(String(100))
    website       = Column(String(500))
    email         = Column(String(255))
    phone         = Column(String(50))
    lat           = Column(Float)
    lng           = Column(Float)
    # Unique Google identifier — used to deduplicate on re-collection
    place_id      = Column(String(255), unique=True, index=True, nullable=True)
    source        = Column(String(100), default="google_places")
    category      = Column(String(100), default="plumber")
    # 1 if the business appears to be a commercial/contract plumber
    is_commercial = Column(Integer, default=0)

    # Phase 2 CRM fields — included now so Phase 2 migration is minimal
    prospect_status   = Column(String(50), default="new")   # new|contacted|interested|client
    notes             = Column(Text)
    last_contacted_at = Column(DateTime)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    matches = relationship("Match", back_populates="plumber", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_plumber_borough", "borough"),
        Index("ix_plumber_postcode", "postcode"),
    )


# --------------------------------------------------------------------------- #
# Demand side                                                                  #
# --------------------------------------------------------------------------- #

from sqlalchemy import Column, Integer, String

class DemandProspect(Base):
    __tablename__ = "demand_prospects"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    name = Column(String(255), nullable=False)
    category = Column(String(100))
    address = Column(Text)
    city = Column(String(100), default="London")
    borough = Column(String(100))
    postcode = Column(String(20))

    # Contact (future enrichment)
    website = Column(String(500))
    email = Column(String(255))
    phone = Column(String(50))

    # Source
    source = Column(String(100))

    # FSA identifiers
    fsa_establishment_id = Column(String(100), unique=True, index=True)
    fsa_rating = Column(String(50))
    last_inspection_date = Column(String)

    # Scoring
    demand_score = Column(Integer, default=0)
    score_reason_summary = Column(String)

    # Freshness
    freshness_label = Column(String(100))

    # Timestamps
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    matches = relationship("Match", back_populates="demand_prospect", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_demand_borough", "borough"),
        Index("ix_demand_score", "demand_score"),
        Index("ix_demand_postcode", "postcode"),
    )


# --------------------------------------------------------------------------- #
# Matching                                                                     #
# --------------------------------------------------------------------------- #

class Match(Base):
    """
    One demand prospect ↔ one plumber match.
    A prospect can have multiple matches (one per plumber recommendation).
    """
    __tablename__ = "matches"

    id                  = Column(Integer, primary_key=True, index=True)
    demand_prospect_id  = Column(
        Integer,
        ForeignKey("demand_prospects.id", ondelete="CASCADE"),
        nullable=False,
    )
    plumber_id = Column(
        Integer,
        ForeignKey("plumbers.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_score  = Column(Integer, default=0)   # 0–100
    match_reason = Column(Text)                  # Human-readable explanation
    created_at   = Column(DateTime, default=_utcnow)

    demand_prospect = relationship("DemandProspect", back_populates="matches")
    plumber         = relationship("Plumber", back_populates="matches")

    __table_args__ = (
        Index("ix_match_demand", "demand_prospect_id"),
        Index("ix_match_plumber", "plumber_id"),
    )


# --------------------------------------------------------------------------- #
# Audit log                                                                    #
# --------------------------------------------------------------------------- #

class JobLog(Base):
    """Records every collection, enrichment, and matching run for auditability."""
    __tablename__ = "job_logs"

    id                = Column(Integer, primary_key=True, index=True)
    job_type          = Column(String(100))          # collect_plumbers|collect_demand|enrich|match
    status            = Column(String(50))            # running|success|error
    message           = Column(Text)
    records_processed = Column(Integer, default=0)
    created_at        = Column(DateTime, default=_utcnow)