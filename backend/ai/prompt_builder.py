from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models.incident import Incident, Evidence
from backend.models.log import Log
from backend.models.threat_intel import IPReputation
from backend.models.ml_prediction import MLPrediction
from backend.schemas.investigation import StructuredEvidence


SOC_ANALYST_SYSTEM_PROMPT = """You are SentinelAI — an expert Tier 3 Senior SOC Analyst Assistant.
Your task is to analyze the structured security incident evidence provided below and generate a rigorous, factual, analyst-ready incident investigation report.

CRITICAL OPERATIONAL RULES:
1. ONLY reference entities, IPs, users, timestamps, and numbers explicitly present in the provided JSON evidence.
2. DO NOT hallucinate or assume unstated details (e.g., specific CVEs or compromised passwords not mentioned).
3. The LLM is an EXPLANATION assistant, NOT the detector. Provide clear explanations for human security analysts to take action.
4. Output MUST be a single valid JSON object matching the exact schema specified below with no markdown formatting around it.

JSON OUTPUT SCHEMA:
{
  "title": "Clear concise incident title",
  "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "summary": "2-3 sentences explaining what attack occurred, how it progressed, and the immediate risk to the organization.",
  "evidence_points": [
    "Factual bullet point 1 citing specific metrics (e.g., 8 failed logins from 185.23.41.12)",
    "Factual bullet point 2 citing threat intelligence or geolocation context",
    "Factual bullet point 3 citing timeline or data transfer volume"
  ],
  "recommended_actions": [
    "Immediate containment action (e.g., Revoke active session tokens for user admin)",
    "Network / firewall mitigation (e.g., Block IP 185.23.41.12 at perimeter firewall)",
    "Forensic follow-up action (e.g., Audit authentication logs for adjacent service access)"
  ],
  "mitre_tactics": [
    "Initial Access",
    "Credential Access"
  ],
  "confidence_score": 0.95
}
"""


def build_structured_evidence(db: Session, incident: Incident) -> StructuredEvidence:
    """
    Extracts relevant logs, IP threat intel, and ML anomaly scores into a compact,
    structured evidence object suitable for the LLM.
    """
    evidence_logs_records = (
        db.query(Log)
        .join(Evidence, Evidence.log_id == Log.id)
        .filter(Evidence.incident_id == incident.id)
        .order_by(Log.timestamp.asc())
        .limit(20)
        .all()
    )

    affected_users = sorted(list({log.user for log in evidence_logs_records if log.user}))
    source_ips = sorted(list({log.ip for log in evidence_logs_records if log.ip}))
    event_types = sorted(list({log.event_type for log in evidence_logs_records if log.event_type}))

    # Fallback if no linked logs
    if not source_ips and incident.title:
        import re
        ip_pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
        found = ip_pattern.findall(incident.title)
        source_ips.extend(found)

    # Gather Threat Intelligence for involved IPs
    threat_intel_context: List[Dict[str, Any]] = []
    for ip in source_ips:
        rep = db.query(IPReputation).filter(IPReputation.ip == ip).first()
        if rep:
            threat_intel_context.append({
                "ip": rep.ip,
                "reputation": rep.reputation,
                "risk_score": rep.risk_score,
                "country": rep.country,
                "city": rep.city,
                "asn": rep.asn,
                "isp": rep.isp,
                "is_tor": rep.is_tor,
                "is_vpn": rep.is_vpn,
                "threat_tags": rep.threat_tags_list,
            })

    # Gather ML Anomaly Scores
    max_anomaly_score: Optional[float] = None
    if source_ips:
        preds = (
            db.query(MLPrediction)
            .filter(MLPrediction.ip.in_(source_ips))
            .order_by(desc(MLPrediction.anomaly_score))
            .limit(5)
            .all()
        )
        if preds:
            max_anomaly_score = max(p.anomaly_score for p in preds)

    # Build compact log representations
    evidence_logs = []
    for log in evidence_logs_records:
        evidence_logs.append({
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "user": log.user,
            "ip": log.ip,
            "event_type": log.event_type,
            "port": log.port,
            "bytes_transferred": log.bytes_transferred,
            "country": log.country,
        })

    time_start = evidence_logs[0]["timestamp"] if evidence_logs else None
    time_end = evidence_logs[-1]["timestamp"] if evidence_logs else None

    return StructuredEvidence(
        incident_id=incident.id,
        title=incident.title,
        type=incident.type,
        severity=incident.severity,
        affected_users=affected_users,
        source_ips=source_ips,
        event_types=event_types,
        events_count=len(evidence_logs_records),
        time_range_start=time_start,
        time_range_end=time_end,
        max_anomaly_score=max_anomaly_score,
        threat_intel_context=threat_intel_context,
        evidence_logs=evidence_logs,
    )


def build_investigation_prompt(evidence: StructuredEvidence) -> str:
    """Formats the structured evidence JSON payload into the LLM prompt."""
    evidence_json = evidence.model_dump_json(indent=2)
    return (
        f"Analyze this incident evidence and return the structured JSON investigation report:\n\n"
        f"```json\n{evidence_json}\n```"
    )
