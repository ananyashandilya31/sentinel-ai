"""
Threat Intelligence API Router — /api/v1/threat-intel/*

Endpoints:
    GET  /threat-intel/{ip}             Retrieve reputation, risk score & enrichment for an IP
    GET  /threat-intel                  List stored IP reputations (paginated, with search & filter)
    POST /threat-intel/seed             Seed known malicious / benign IPs into local database
    POST /threat-intel/batch            Batch lookup threat intel for multiple IPs
    GET  /threat-intel/incident/{id}    Get threat intelligence for all IPs involved in an incident
"""
from __future__ import annotations

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import require_auth_if_enabled
from backend.schemas.threat_intel import (
    IPReputationResponse,
    PaginatedIPReputationResponse,
    IPBatchLookupRequest,
    IPBatchLookupResponse,
)
from backend.services.threat_intel_service import (
    get_ip_reputation,
    list_ip_reputations,
    seed_threat_intel_database,
    batch_lookup_ips,
    enrich_incident_ips,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/threat-intel")


@router.get(
    "/seed",
    summary="Seed known IP threat intelligence (GET convenience)",
    tags=["Threat Intelligence"],
)
@router.post(
    "/seed",
    summary="Seed known IP threat intelligence into database",
    tags=["Threat Intelligence"],
)
def seed_threat_intel(
    overwrite: bool = Query(False, description="Whether to overwrite existing IP reputation entries"),
    db: Session = Depends(get_db),
    _: None = Depends(require_auth_if_enabled),
):
    """
    Seeds local Threat Intelligence database with curated IP reputations,
    geolocations, ASN data, and risk scores.
    """
    try:
        count = seed_threat_intel_database(db, overwrite=overwrite)
        return {
            "status": "success",
            "message": f"Successfully seeded {count} threat intelligence records.",
            "seeded_count": count,
        }
    except Exception as exc:
        logger.exception("Failed to seed threat intelligence: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed threat intelligence: {exc}",
        ) from exc


@router.get(
    "",
    response_model=PaginatedIPReputationResponse,
    summary="List and filter IP reputations",
    tags=["Threat Intelligence"],
)
def list_reputations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    reputation: Optional[str] = Query(None, description="Filter by reputation: MALICIOUS, SUSPICIOUS, CLEAN, UNKNOWN"),
    min_risk: Optional[int] = Query(None, ge=0, le=100, description="Minimum risk score (0-100)"),
    search: Optional[str] = Query(None, description="Search term across IP, Country, ISP, or Threat tags"),
    db: Session = Depends(get_db),
):
    """
    Returns a paginated list of IP reputation records with optional filtering
    by reputation rating, minimum risk score, and free-text search.
    """
    return list_ip_reputations(
        db,
        page=page,
        page_size=page_size,
        reputation=reputation,
        min_risk=min_risk,
        search=search,
    )


@router.post(
    "/batch",
    response_model=IPBatchLookupResponse,
    summary="Batch lookup threat intelligence for multiple IPs",
    tags=["Threat Intelligence"],
)
def batch_lookup(
    request: IPBatchLookupRequest,
    db: Session = Depends(get_db),
):
    """
    Resolves threat intelligence for an array of IP addresses in a single request.
    """
    results = batch_lookup_ips(db, request.ips, enrich_if_missing=True)
    return IPBatchLookupResponse(total=len(results), results=results)


@router.get(
    "/incident/{incident_id}",
    response_model=List[IPReputationResponse],
    summary="Get threat intelligence for IPs involved in an incident",
    tags=["Threat Intelligence"],
)
def get_incident_threat_intel(
    incident_id: str,
    db: Session = Depends(get_db),
):
    """
    Extracts all IP addresses associated with triggering evidence logs for the incident
    and returns their enriched threat intelligence.
    """
    return enrich_incident_ips(db, incident_id)


@router.get(
    "/{ip}",
    response_model=IPReputationResponse,
    summary="Lookup or dynamically enrich threat intelligence for an IP",
    tags=["Threat Intelligence"],
)
def get_reputation(
    ip: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves threat intelligence for a specific IP address.
    If the IP is not in the database, runs dynamic heuristic enrichment
    and persists the record for fast subsequent access.
    """
    # Clean input
    clean_ip = ip.strip()
    if not clean_ip:
        raise HTTPException(status_code=400, detail="Invalid IP address provided")

    result = get_ip_reputation(db, clean_ip, enrich_if_missing=True)
    if not result:
        raise HTTPException(status_code=404, detail=f"No threat intelligence available for {clean_ip}")
    return result
