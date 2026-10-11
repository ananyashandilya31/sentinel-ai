from __future__ import annotations

import pytest
from datetime import datetime, timezone
from backend.models.log import Log
from backend.models.incident import Incident, Alert, Evidence
from backend.models.threat_intel import IPReputation
from backend.services.threat_intel_service import (
    seed_threat_intel_database,
    get_ip_reputation,
    list_ip_reputations,
    batch_lookup_ips,
    enrich_incident_ips,
    is_private_ip,
    derive_heuristic_threat_intel,
)


def test_is_private_ip():
    """Verify RFC 1918 and loopback IP recognition."""
    assert is_private_ip("192.168.1.1") is True
    assert is_private_ip("10.0.0.1") is True
    assert is_private_ip("172.16.0.5") is True
    assert is_private_ip("127.0.0.1") is True
    assert is_private_ip("8.8.8.8") is False
    assert is_private_ip("45.154.255.88") is False
    assert is_private_ip("not-an-ip") is False


def test_seed_threat_intel_database(db_session):
    """Verify threat intelligence seeding adds default dataset."""
    count = seed_threat_intel_database(db_session, overwrite=False)
    assert count > 0

    # Ensure known malicious IP is present
    rep = db_session.query(IPReputation).filter(IPReputation.ip == "45.154.255.88").first()
    assert rep is not None
    assert rep.reputation == "MALICIOUS"
    assert rep.risk_score >= 90
    assert "port_scanner" in rep.threat_tags_list or "brute_force" in rep.threat_tags_list

    # Re-seeding with overwrite=False returns 0 modifications
    count2 = seed_threat_intel_database(db_session, overwrite=False)
    assert count2 == 0


def test_get_ip_reputation_seeded(db_session):
    """Verify get_ip_reputation retrieves correct seeded attributes."""
    seed_threat_intel_database(db_session)
    result = get_ip_reputation(db_session, "185.220.101.5")
    assert result is not None
    assert result.ip == "185.220.101.5"
    assert result.is_tor is True
    assert result.country == "Germany"
    assert result.risk_score >= 80


def test_get_ip_reputation_unseen_heuristic(db_session):
    """Verify unseeded IP is enriched dynamically using heuristics."""
    # Lookup unseen public IP
    result = get_ip_reputation(db_session, "198.51.100.23", enrich_if_missing=True)
    assert result is not None
    assert result.ip == "198.51.100.23"
    assert result.source == "dynamic_heuristic"

    # Should now be persisted in DB
    in_db = db_session.query(IPReputation).filter(IPReputation.ip == "198.51.100.23").first()
    assert in_db is not None


def test_list_ip_reputations_filtering(db_session):
    """Verify filtering and pagination of IP reputation list."""
    seed_threat_intel_database(db_session)

    # Filter by reputation MALICIOUS
    malicious_res = list_ip_reputations(db_session, page=1, page_size=10, reputation="MALICIOUS")
    assert malicious_res.total >= 3
    for item in malicious_res.items:
        assert item.reputation == "MALICIOUS"

    # Filter by minimum risk score
    high_risk_res = list_ip_reputations(db_session, page=1, page_size=10, min_risk=80)
    for item in high_risk_res.items:
        assert item.risk_score >= 80

    # Search filter
    search_res = list_ip_reputations(db_session, page=1, page_size=10, search="Russia")
    assert search_res.total >= 1
    assert any("Russia" in (item.country or "") for item in search_res.items)


def test_batch_lookup_ips(db_session):
    """Verify batch lookup resolves multiple IPs."""
    seed_threat_intel_database(db_session)
    results = batch_lookup_ips(db_session, ["45.154.255.88", "8.8.8.8", "45.154.255.88"])
    # Should deduplicate duplicate IPs
    assert len(results) == 2
    ips = {r.ip for r in results}
    assert "45.154.255.88" in ips
    assert "8.8.8.8" in ips


def test_enrich_incident_ips(db_session):
    """Verify incident IP extraction and enrichment via evidence logs."""
    seed_threat_intel_database(db_session)

    # Create dummy log, incident, and evidence
    now = datetime.now(timezone.utc)
    log = Log(
        id="log-ti-01",
        timestamp=now,
        user="analyst1",
        ip="45.154.255.88",
        event_type="LOGIN_FAILED",
        session_id="sess-ti-01",
    )
    incident = Incident(
        id="inc-ti-01",
        title="Brute Force from 45.154.255.88",
        type="BRUTE_FORCE",
        severity="HIGH",
        status="OPEN",
        created_at=now,
        updated_at=now,
    )
    evidence = Evidence(
        id="ev-ti-01",
        incident_id="inc-ti-01",
        log_id="log-ti-01",
        description="Triggering login failed attempt",
        created_at=now,
    )
    db_session.add(log)
    db_session.add(incident)
    db_session.add(evidence)
    db_session.commit()

    enriched = enrich_incident_ips(db_session, "inc-ti-01")
    assert len(enriched) >= 1
    assert enriched[0].ip == "45.154.255.88"
    assert enriched[0].reputation == "MALICIOUS"
