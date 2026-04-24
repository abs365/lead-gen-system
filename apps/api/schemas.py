"""
Pydantic v2 schemas for API request validation and response serialisation.

SECURITY: All incoming data is validated here before reaching the database.
String lengths are capped to prevent oversized payloads.
Allowlists are enforced in router-level validators (see routers/).
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re


# --------------------------------------------------------------------------- #
# Shared helpers                                                               #
# --------------------------------------------------------------------------- #

def _safe_str(v: Optional[str], max_len: int = 255) -> Optional[str]:
    """Strip whitespace and cap length."""
    if v is None:
        return None
    return v.strip()[:max_len]


# --------------------------------------------------------------------------- #
# Request schemas                                                              #
# --------------------------------------------------------------------------- #

# Allowlisted keywords to prevent arbitrary Google Places searches
ALLOWED_KEYWORDS: List[str] = [
    "plumbers in London",
    "emergency plumbers London",
    "commercial plumbers London",
    "plumbing services London",
    "heating and plumbing London",
]

ALLOWED_DEMAND_CATEGORIES: List[str] = [
    "all",
    "restaurant",
    "cafe",
    "takeaway",
    "pub",
    "hotel",
    "hospitality",
]

ALLOWED_PROSPECT_STATUSES: List[str] = [
    "new", "contacted", "interested", "client",
]


class CollectPlumbersRequest(BaseModel):
    keyword:  str = Field(default="plumbers in London", max_length=100)
    location: str = Field(default="London, UK", max_length=100)

    @field_validator("keyword")
    @classmethod
    def keyword_must_be_allowlisted(cls, v: str) -> str:
        if v not in ALLOWED_KEYWORDS:
            raise ValueError(
                f"keyword must be one of: {ALLOWED_KEYWORDS}"
            )
        return v

    @field_validator("location")
    @classmethod
    def sanitise_location(cls, v: str) -> str:
        # Only allow alphanumeric, spaces, commas, hyphens
        if not re.match(r'^[A-Za-z0-9 ,\-\.]+$', v):
            raise ValueError("location contains invalid characters")
        return v.strip()


class CollectDemandRequest(BaseModel):
    location: str = Field(default="London", max_length=100)
    category: str = Field(default="all", max_length=50)
    page:     int = Field(default=1, ge=1, le=100)

    @field_validator("category")
    @classmethod
    def category_must_be_allowlisted(cls, v: str) -> str:
        if v not in ALLOWED_DEMAND_CATEGORIES:
            raise ValueError(
                f"category must be one of: {ALLOWED_DEMAND_CATEGORIES}"
            )
        return v


class EnrichRequest(BaseModel):
    """Optional: restrict enrichment to specific IDs."""
    ids: Optional[List[int]] = Field(default=None, max_length=500)


class RunMatchRequest(BaseModel):
    max_matches_per_prospect: int = Field(default=3, ge=1, le=10)


class UpdatePlumberStatusRequest(BaseModel):
    prospect_status: str = Field(max_length=50)
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("prospect_status")
    @classmethod
    def status_must_be_valid(cls, v: str) -> str:
        if v not in ALLOWED_PROSPECT_STATUSES:
            raise ValueError(
                f"prospect_status must be one of: {ALLOWED_PROSPECT_STATUSES}"
            )
        return v


# --------------------------------------------------------------------------- #
# Response schemas                                                             # score_reason_summary: Optional[str] = None
# --------------------------------------------------------------------------- #

class PlumberOut(BaseModel):
    id:               int
    name:             str
    address:          Optional[str]
    postcode:         Optional[str]
    city:             Optional[str]
    borough:          Optional[str]
    website:          Optional[str]
    email:            Optional[str]
    phone:            Optional[str]
    lat:              Optional[float]
    lng:              Optional[float]
    source:           Optional[str]
    category:         Optional[str]
    is_commercial:    Optional[int]
    prospect_status:  Optional[str]
    created_at:       Optional[datetime]

    model_config = {"from_attributes": True}


class DemandProspectOut(BaseModel):
    id:                   int
    name:                 str
    category:             Optional[str]
    address:              Optional[str]
    postcode:             Optional[str]
    city:                 Optional[str]
    borough:              Optional[str]
    website:              Optional[str]
    email:                Optional[str]
    phone:                Optional[str]
    source:               Optional[str]
    freshness_label:      Optional[str]
    demand_score:         Optional[int]
    fsa_rating:           Optional[str]
    created_at:           Optional[datetime]

    model_config = {"from_attributes": True}


class MatchOut(BaseModel):
    id:                  int
    demand_prospect_id:  int
    plumber_id:          int
    match_score:         int
    match_reason:        Optional[str]
    created_at:          Optional[datetime]
    # Nested for convenience
    demand_prospect:     Optional[DemandProspectOut]
    plumber:             Optional[PlumberOut]

    model_config = {"from_attributes": True}


class JobLogOut(BaseModel):
    id:                int
    job_type:          Optional[str]
    status:            Optional[str]
    message:           Optional[str]
    records_processed: Optional[int]
    created_at:        Optional[datetime]

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel):
    total:   int
    page:    int
    size:    int
    items:   list


class JobResult(BaseModel):
    status:  str
    message: str
    added:   int = 0
    skipped: int = 0
    updated: int = 0
