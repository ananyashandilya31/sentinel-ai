from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class IPReputationBase(BaseModel):
    ip: str = Field(..., description="IPv4 or IPv6 address")
    reputation: str = Field("UNKNOWN", description="Reputation rating: MALICIOUS, SUSPICIOUS, CLEAN, UNKNOWN")
    risk_score: int = Field(0, ge=0, le=100, description="Composite threat risk score (0 to 100)")
    country: Optional[str] = Field(None, description="Country name")
    country_code: Optional[str] = Field(None, description="2-letter ISO country code")
    city: Optional[str] = Field(None, description="City name")
    asn: Optional[str] = Field(None, description="Autonomous System Number (e.g., AS15169)")
    isp: Optional[str] = Field(None, description="Internet Service Provider or hosting organization")
    is_tor: bool = Field(False, description="Flag indicating if IP is a known Tor Exit Node")
    is_vpn: bool = Field(False, description="Flag indicating if IP is a known VPN / Proxy")
    threat_types: List[str] = Field(default_factory=list, description="Associated threat categories")
    total_reports: int = Field(0, ge=0, description="Aggregated community / feed report count")
    last_seen: Optional[datetime] = Field(None, description="Last detected malicious or suspicious activity timestamp")
    source: str = Field("local_seed", description="Source provider or mechanism of threat intelligence")


class IPReputationCreate(IPReputationBase):
    pass


class IPReputationUpdate(BaseModel):
    reputation: Optional[str] = None
    risk_score: Optional[int] = Field(None, ge=0, le=100)
    country: Optional[str] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    asn: Optional[str] = None
    isp: Optional[str] = None
    is_tor: Optional[bool] = None
    is_vpn: Optional[bool] = None
    threat_types: Optional[List[str]] = None
    total_reports: Optional[int] = None
    last_seen: Optional[datetime] = None
    source: Optional[str] = None


class IPReputationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ip: str
    reputation: str
    risk_score: int
    country: Optional[str] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    asn: Optional[str] = None
    isp: Optional[str] = None
    is_tor: bool = False
    is_vpn: bool = False
    threat_types: List[str] = Field(default_factory=list)
    total_reports: int = 0
    last_seen: Optional[datetime] = None
    source: str = "local_seed"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    past_incidents_count: int = 0

    @classmethod
    def from_orm_model(cls, model_obj, past_incidents_count: int = 0) -> IPReputationResponse:
        """Helper to safely construct response from ORM model with JSON deserialized threat_types."""
        tags = model_obj.threat_tags_list if hasattr(model_obj, "threat_tags_list") else []
        return cls(
            ip=model_obj.ip,
            reputation=model_obj.reputation,
            risk_score=model_obj.risk_score,
            country=model_obj.country,
            country_code=model_obj.country_code,
            city=model_obj.city,
            asn=model_obj.asn,
            isp=model_obj.isp,
            is_tor=model_obj.is_tor,
            is_vpn=model_obj.is_vpn,
            threat_types=tags,
            total_reports=model_obj.total_reports,
            last_seen=model_obj.last_seen,
            source=model_obj.source,
            created_at=model_obj.created_at,
            updated_at=model_obj.updated_at,
            past_incidents_count=past_incidents_count,
        )


class PaginatedIPReputationResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[IPReputationResponse]


class IPBatchLookupRequest(BaseModel):
    ips: List[str] = Field(..., max_length=100, description="List of IP addresses to look up or enrich")


class IPBatchLookupResponse(BaseModel):
    total: int
    results: List[IPReputationResponse]
