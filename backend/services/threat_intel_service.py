from __future__ import annotations

import json
import ipaddress
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from backend.models.threat_intel import IPReputation
from backend.models.incident import Incident, Evidence
from backend.models.log import Log
from backend.schemas.threat_intel import (
    IPReputationBase,
    IPReputationCreate,
    IPReputationUpdate,
    IPReputationResponse,
    PaginatedIPReputationResponse,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Curated seed threat intelligence records for known infrastructure and synthetic attack scenarios
SEEDED_THREAT_INTEL: List[Dict[str, Any]] = [
    {
        "ip": "45.154.255.88",
        "reputation": "MALICIOUS",
        "risk_score": 95,
        "country": "Russia",
        "country_code": "RU",
        "city": "Moscow",
        "asn": "AS200019",
        "isp": "Webhosting Ltd",
        "is_tor": False,
        "is_vpn": True,
        "threat_types": ["brute_force", "port_scanner", "credential_stuffing"],
        "total_reports": 342,
        "last_seen": utc_now() - timedelta(hours=2),
        "source": "local_seed",
    },
    {
        "ip": "185.220.101.5",
        "reputation": "SUSPICIOUS",
        "risk_score": 82,
        "country": "Germany",
        "country_code": "DE",
        "city": "Frankfurt",
        "asn": "AS208294",
        "isp": "Zwiebelfreunde e.V.",
        "is_tor": True,
        "is_vpn": False,
        "threat_types": ["tor_exit_node", "anonymizer"],
        "total_reports": 189,
        "last_seen": utc_now() - timedelta(hours=5),
        "source": "local_seed",
    },
    {
        "ip": "185.23.41.12",
        "reputation": "MALICIOUS",
        "risk_score": 92,
        "country": "Seychelles",
        "country_code": "SC",
        "city": "Victoria",
        "asn": "AS44050",
        "isp": "Chang Way Tech Co.",
        "is_tor": False,
        "is_vpn": True,
        "threat_types": ["brute_force", "botnet", "ssh_scan"],
        "total_reports": 280,
        "last_seen": utc_now() - timedelta(hours=1),
        "source": "local_seed",
    },
    {
        "ip": "194.26.29.11",
        "reputation": "MALICIOUS",
        "risk_score": 88,
        "country": "Netherlands",
        "country_code": "NL",
        "city": "Amsterdam",
        "asn": "AS49981",
        "isp": "WorldStream B.V.",
        "is_tor": False,
        "is_vpn": False,
        "threat_types": ["data_exfiltration", "c2_server"],
        "total_reports": 115,
        "last_seen": utc_now() - timedelta(hours=3),
        "source": "local_seed",
    },
    {
        "ip": "192.168.1.99",
        "reputation": "SUSPICIOUS",
        "risk_score": 65,
        "country": "Internal Network",
        "country_code": "INT",
        "city": "Corporate LAN",
        "asn": "AS-INTERNAL",
        "isp": "Corporate Internal LAN (Host 99)",
        "is_tor": False,
        "is_vpn": False,
        "threat_types": ["compromised_endpoint", "privilege_escalation"],
        "total_reports": 12,
        "last_seen": utc_now() - timedelta(hours=6),
        "source": "local_seed",
    },
    {
        "ip": "192.168.1.10",
        "reputation": "CLEAN",
        "risk_score": 5,
        "country": "Internal Network",
        "country_code": "INT",
        "city": "Corporate LAN",
        "asn": "AS-INTERNAL",
        "isp": "Workstation DHCP Pool",
        "is_tor": False,
        "is_vpn": False,
        "threat_types": [],
        "total_reports": 0,
        "last_seen": None,
        "source": "local_seed",
    },
    {
        "ip": "10.0.0.15",
        "reputation": "CLEAN",
        "risk_score": 2,
        "country": "Internal Network",
        "country_code": "INT",
        "city": "Corporate LAN",
        "asn": "AS-INTERNAL",
        "isp": "Production Server Cluster",
        "is_tor": False,
        "is_vpn": False,
        "threat_types": [],
        "total_reports": 0,
        "last_seen": None,
        "source": "local_seed",
    },
    {
        "ip": "192.168.1.42",
        "reputation": "CLEAN",
        "risk_score": 5,
        "country": "Internal Network",
        "country_code": "INT",
        "city": "Corporate LAN",
        "asn": "AS-INTERNAL",
        "isp": "Workstation DHCP Pool",
        "is_tor": False,
        "is_vpn": False,
        "threat_types": [],
        "total_reports": 0,
        "last_seen": None,
        "source": "local_seed",
    },
    {
        "ip": "192.168.1.25",
        "reputation": "CLEAN",
        "risk_score": 5,
        "country": "Internal Network",
        "country_code": "INT",
        "city": "Corporate LAN",
        "asn": "AS-INTERNAL",
        "isp": "Workstation DHCP Pool",
        "is_tor": False,
        "is_vpn": False,
        "threat_types": [],
        "total_reports": 0,
        "last_seen": None,
        "source": "local_seed",
    },
    {
        "ip": "10.0.0.22",
        "reputation": "CLEAN",
        "risk_score": 2,
        "country": "Internal Network",
        "country_code": "INT",
        "city": "Corporate LAN",
        "asn": "AS-INTERNAL",
        "isp": "Database Server Pool",
        "is_tor": False,
        "is_vpn": False,
        "threat_types": [],
        "total_reports": 0,
        "last_seen": None,
        "source": "local_seed",
    },
    {
        "ip": "8.8.8.8",
        "reputation": "CLEAN",
        "risk_score": 0,
        "country": "United States",
        "country_code": "US",
        "city": "Mountain View",
        "asn": "AS15169",
        "isp": "Google LLC",
        "is_tor": False,
        "is_vpn": False,
        "threat_types": ["public_dns"],
        "total_reports": 0,
        "last_seen": None,
        "source": "local_seed",
    },
    {
        "ip": "1.1.1.1",
        "reputation": "CLEAN",
        "risk_score": 0,
        "country": "Australia",
        "country_code": "AU",
        "city": "Sydney",
        "asn": "AS13335",
        "isp": "Cloudflare, Inc.",
        "is_tor": False,
        "is_vpn": False,
        "threat_types": ["public_dns"],
        "total_reports": 0,
        "last_seen": None,
        "source": "local_seed",
    },
]


def is_private_ip(ip: str) -> bool:
    """Returns True if the IP string belongs to private RFC 1918 or loopback space."""
    try:
        obj = ipaddress.ip_address(ip)
        return obj.is_private or obj.is_loopback
    except ValueError:
        return False


def count_past_incidents_for_ip(db: Session, ip: str) -> int:
    """Counts incidents where this IP is referenced in triggering evidence logs."""
    try:
        # Join Evidence with Log to count distinct incidents matching this IP
        count = (
            db.query(func.count(func.distinct(Evidence.incident_id)))
            .join(Log, Evidence.log_id == Log.id)
            .filter(Log.ip == ip)
            .scalar()
        )
        return int(count or 0)
    except Exception as exc:
        logger.warning("Error counting past incidents for IP %s: %s", ip, exc)
        return 0


def seed_threat_intel_database(db: Session, overwrite: bool = False) -> int:
    """
    Populates default threat intelligence database with known IPs.
    If overwrite is False, existing IPs are left unmodified.
    Returns the count of inserted or updated entries.
    """
    count = 0
    for record in SEEDED_THREAT_INTEL:
        ip = record["ip"]
        existing = db.query(IPReputation).filter(IPReputation.ip == ip).first()

        if existing and not overwrite:
            continue

        if not existing:
            existing = IPReputation(ip=ip)
            db.add(existing)

        existing.reputation = record["reputation"]
        existing.risk_score = record["risk_score"]
        existing.country = record["country"]
        existing.country_code = record["country_code"]
        existing.city = record["city"]
        existing.asn = record["asn"]
        existing.isp = record["isp"]
        existing.is_tor = record["is_tor"]
        existing.is_vpn = record["is_vpn"]
        existing.set_threat_tags(record["threat_types"])
        existing.total_reports = record["total_reports"]
        existing.last_seen = record["last_seen"]
        existing.source = record["source"]
        existing.updated_at = utc_now()
        count += 1

    db.commit()
    return count


def derive_heuristic_threat_intel(db: Session, ip: str) -> IPReputation:
    """
    Dynamically infers threat intelligence for an unseen IP using:
    1. RFC 1918 address space rules.
    2. Event history & failed login frequency in the local log database.
    3. Associated security incident history.
    Saves and returns the resulting IPReputation record.
    """
    is_priv = is_private_ip(ip)

    # Inspect logs associated with this IP
    log_count = db.query(Log).filter(Log.ip == ip).count()
    failed_logins = (
        db.query(Log)
        .filter(Log.ip == ip, Log.event_type == "LOGIN_FAILED")
        .count()
    )
    distinct_ports = (
        db.query(func.count(func.distinct(Log.port)))
        .filter(Log.ip == ip, Log.port.isnot(None))
        .scalar()
    ) or 0

    past_incidents = count_past_incidents_for_ip(db, ip)

    # Compute risk score (0-100)
    risk_score = 10 if not is_priv else 5
    threat_types: List[str] = []

    if failed_logins >= 8:
        risk_score += 45
        threat_types.append("brute_force")
    elif failed_logins >= 3:
        risk_score += 20
        threat_types.append("failed_authentications")

    if distinct_ports >= 10:
        risk_score += 35
        threat_types.append("port_scanner")

    if past_incidents > 0:
        risk_score += min(past_incidents * 20, 40)
        threat_types.append("incident_source")

    risk_score = min(max(risk_score, 0), 100)

    if risk_score >= 70:
        reputation = "MALICIOUS"
    elif risk_score >= 35:
        reputation = "SUSPICIOUS"
    else:
        reputation = "CLEAN" if (log_count > 0 or is_priv) else "UNKNOWN"

    new_record = IPReputation(
        ip=ip,
        reputation=reputation,
        risk_score=risk_score,
        country="Internal Network" if is_priv else "Unknown / Public",
        country_code="INT" if is_priv else "ZZ",
        city="LAN" if is_priv else "Unknown",
        asn="AS-INTERNAL" if is_priv else "AS-DYNAMIC",
        isp="Internal Device" if is_priv else "Dynamic Host Lookup",
        is_tor=False,
        is_vpn=False,
        total_reports=past_incidents + (1 if risk_score > 50 else 0),
        last_seen=utc_now() if log_count > 0 else None,
        source="dynamic_heuristic",
    )
    new_record.set_threat_tags(threat_types)

    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record


def get_ip_reputation(
    db: Session,
    ip: str,
    enrich_if_missing: bool = True,
) -> Optional[IPReputationResponse]:
    """
    Retrieves threat intelligence for an IP address.
    If not in DB and enrich_if_missing is True, calculates and persists heuristic threat intel.
    """
    record = db.query(IPReputation).filter(IPReputation.ip == ip).first()

    if not record:
        if not enrich_if_missing:
            return None
        record = derive_heuristic_threat_intel(db, ip)

    past_incidents = count_past_incidents_for_ip(db, ip)
    return IPReputationResponse.from_orm_model(record, past_incidents_count=past_incidents)


def list_ip_reputations(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    reputation: Optional[str] = None,
    min_risk: Optional[int] = None,
    search: Optional[str] = None,
) -> PaginatedIPReputationResponse:
    """Retrieves paginated IP reputation records with optional filters."""
    # Ensure seed records exist if table is empty
    if db.query(IPReputation).count() == 0:
        seed_threat_intel_database(db)

    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    query = db.query(IPReputation)

    if reputation:
        query = query.filter(IPReputation.reputation == reputation.upper())

    if min_risk is not None:
        query = query.filter(IPReputation.risk_score >= min_risk)

    if search:
        search_filter = f"%{search.strip()}%"
        query = query.filter(
            (IPReputation.ip.like(search_filter))
            | (IPReputation.country.like(search_filter))
            | (IPReputation.isp.like(search_filter))
            | (IPReputation.threat_types.like(search_filter))
        )

    total = query.count()
    offset = (page - 1) * page_size
    records = query.order_by(desc(IPReputation.risk_score), desc(IPReputation.updated_at)).offset(offset).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    items: List[IPReputationResponse] = []
    for r in records:
        incidents = count_past_incidents_for_ip(db, r.ip)
        items.append(IPReputationResponse.from_orm_model(r, past_incidents_count=incidents))

    return PaginatedIPReputationResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


def batch_lookup_ips(
    db: Session,
    ips: List[str],
    enrich_if_missing: bool = True,
) -> List[IPReputationResponse]:
    """Resolves threat intelligence for multiple IP addresses in batch."""
    results: List[IPReputationResponse] = []
    # Deduplicate while preserving order
    seen = set()
    clean_ips = []
    for ip in ips:
        ip_clean = ip.strip()
        if ip_clean and ip_clean not in seen:
            seen.add(ip_clean)
            clean_ips.append(ip_clean)

    for ip in clean_ips:
        rep = get_ip_reputation(db, ip, enrich_if_missing=enrich_if_missing)
        if rep:
            results.append(rep)

    return results


def enrich_incident_ips(db: Session, incident_id: str) -> List[IPReputationResponse]:
    """
    Extracts all distinct IP addresses involved in an incident's evidence logs,
    resolves their threat intelligence, and returns the list of reputations.
    """
    ip_records = (
        db.query(func.distinct(Log.ip))
        .join(Evidence, Evidence.log_id == Log.id)
        .filter(Evidence.incident_id == incident_id)
        .all()
    )

    ips = [r[0] for r in ip_records if r[0]]
    if not ips:
        # Fallback: check if an IP was mentioned in the incident title
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if incident and incident.title:
            import re
            ip_pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
            found = ip_pattern.findall(incident.title)
            ips.extend(found)

    return batch_lookup_ips(db, ips, enrich_if_missing=True)
