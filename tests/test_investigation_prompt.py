from __future__ import annotations

import pytest
from datetime import datetime, timezone
from backend.models.log import Log
from backend.models.incident import Incident, Evidence
from backend.models.threat_intel import IPReputation
from backend.ai.prompt_builder import build_structured_evidence, build_investigation_prompt
from backend.ai.llm_client import generate_deterministic_investigation, generate_investigation_report


def test_build_structured_evidence(db_session):
    """Verify structured evidence properly aggregates incident entities, logs, and threat context."""
    now = datetime.now(timezone.utc)
    log = Log(
        id="log-ai-01",
        timestamp=now,
        user="analyst1",
        ip="185.23.41.12",
        event_type="LOGIN_FAILED",
        session_id="sess-ai-01",
        bytes_transferred=5000,
    )
    incident = Incident(
        id="inc-ai-01",
        title="Brute force attack from 185.23.41.12",
        type="BRUTE_FORCE",
        severity="HIGH",
        status="OPEN",
        created_at=now,
        updated_at=now,
    )
    evidence = Evidence(
        id="ev-ai-01",
        incident_id="inc-ai-01",
        log_id="log-ai-01",
        description="Repeated failed logins",
        created_at=now,
    )
    ti = IPReputation(
        ip="185.23.41.12",
        reputation="MALICIOUS",
        risk_score=92,
        country="Seychelles",
        city="Victoria",
        asn="AS44050",
        isp="Chang Way Tech",
    )
    ti.set_threat_tags(["brute_force", "botnet"])

    db_session.add(log)
    db_session.add(incident)
    db_session.add(evidence)
    db_session.add(ti)
    db_session.commit()

    structured = build_structured_evidence(db_session, incident)
    assert structured.incident_id == "inc-ai-01"
    assert "analyst1" in structured.affected_users
    assert "185.23.41.12" in structured.source_ips
    assert structured.events_count == 1
    assert len(structured.threat_intel_context) == 1
    assert structured.threat_intel_context[0]["risk_score"] == 92


def test_build_investigation_prompt(db_session):
    """Verify investigation prompt serializes compact JSON evidence."""
    now = datetime.now(timezone.utc)
    incident = Incident(
        id="inc-ai-02",
        title="Port Scan from 45.154.255.88",
        type="PORT_SCAN",
        severity="MEDIUM",
        status="OPEN",
        created_at=now,
        updated_at=now,
    )
    db_session.add(incident)
    db_session.commit()

    structured = build_structured_evidence(db_session, incident)
    prompt = build_investigation_prompt(structured)
    assert "PORT_SCAN" in prompt
    assert "inc-ai-02" in prompt
    assert "```json" in prompt


def test_generate_deterministic_investigation_attack_types(db_session):
    """Verify synthesis engine generates tailored reports for different attack types."""
    now = datetime.now(timezone.utc)

    # Brute Force
    inc_bf = Incident(
        id="inc-bf",
        title="Brute force against admin",
        type="BRUTE_FORCE",
        severity="HIGH",
        created_at=now,
        updated_at=now,
    )
    ev_bf = build_structured_evidence(db_session, inc_bf)
    rep_bf = generate_deterministic_investigation(ev_bf)
    assert "Brute Force" in rep_bf["title"] or "Authentication" in rep_bf["title"]
    assert len(rep_bf["evidence_points"]) >= 2
    assert len(rep_bf["recommended_actions"]) >= 3
    assert any("T1110" in t for t in rep_bf["mitre_tactics"])

    # Exfiltration
    inc_exfil = Incident(
        id="inc-exfil",
        title="Data Exfiltration by user bob",
        type="DATA_EXFILTRATION",
        severity="CRITICAL",
        created_at=now,
        updated_at=now,
    )
    ev_exfil = build_structured_evidence(db_session, inc_exfil)
    rep_exfil = generate_deterministic_investigation(ev_exfil)
    assert rep_exfil["severity"] == "CRITICAL"
    assert any("T1048" in t for t in rep_exfil["mitre_tactics"])
