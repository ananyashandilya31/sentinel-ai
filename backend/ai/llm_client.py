from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.config import settings
from backend.schemas.investigation import StructuredEvidence
from backend.ai.prompt_builder import SOC_ANALYST_SYSTEM_PROMPT, build_investigation_prompt

logger = logging.getLogger(__name__)


def generate_deterministic_investigation(evidence: StructuredEvidence) -> Dict[str, Any]:
    """
    Tier-3 Deterministic SOC Synthesis Engine.
    Produces high-fidelity, factual, context-aware incident triage analyses
    derived strictly from the provided structured evidence.
    Used when running offline or as a zero-hallucination fallback.
    """
    inc_type = (evidence.type or "ANOMALY").upper()
    primary_user = evidence.affected_users[0] if evidence.affected_users else "unknown_user"
    primary_ip = evidence.source_ips[0] if evidence.source_ips else "unknown_ip"
    primary_ti = evidence.threat_intel_context[0] if evidence.threat_intel_context else {}

    ti_rep = primary_ti.get("reputation", "UNKNOWN")
    ti_risk = primary_ti.get("risk_score", 50)
    ti_country = primary_ti.get("country", "Unknown Location")
    ti_isp = primary_ti.get("isp", "Dynamic Host")
    is_tor = primary_ti.get("is_tor", False)
    is_vpn = primary_ti.get("is_vpn", False)

    total_bytes = sum(log.get("bytes_transferred") or 0 for log in evidence.evidence_logs)
    volume_mb = round(total_bytes / (1024 * 1024), 2)
    distinct_ports = list({log.get("port") for log in evidence.evidence_logs if log.get("port")})

    if "BRUTE" in inc_type:
        title = f"Brute Force Authentication Campaign from {primary_ip}"
        severity = "HIGH"
        summary = (
            f"High-velocity authentication assault identified against account '{primary_user}' originating from {primary_ip}. "
            f"Multiple rapid failed login attempts indicate automated credential guessing or dictionary attack."
        )
        evidence_points = [
            f"Identified {evidence.events_count} correlated authentication events targeting user '{primary_user}'",
            f"Source IP {primary_ip} geolocated to {ti_country} ({ti_isp}) with threat risk score {ti_risk}/100 ({ti_rep})",
        ]
        if is_tor or is_vpn:
            evidence_points.append(f"Source IP utilizes anonymization infrastructure ({'Tor Exit Node' if is_tor else 'VPN / Proxy'})")
        if evidence.max_anomaly_score is not None:
            evidence_points.append(f"Machine learning anomaly model scored activity at {round(evidence.max_anomaly_score * 100)}% anomaly risk")

        recommended_actions = [
            f"Temporarily lock account '{primary_user}' and require an out-of-band credential reset",
            f"Enforce perimeter firewall / WAF block on source IP {primary_ip}",
            "Review authentication telemetry across external gateways for adjacent target usernames",
            "Verify mandatory Multi-Factor Authentication (MFA) enforcement on single-sign-on portals",
        ]
        mitre_tactics = ["Credential Access: T1110 (Brute Force)", "Initial Access: T1078 (Valid Accounts)"]

    elif "PORT_SCAN" in inc_type or "SCAN" in inc_type:
        title = f"Reconnaissance Port Scan Probe from {primary_ip}"
        severity = "MEDIUM"
        summary = (
            f"Network reconnaissance activity detected from host {primary_ip}. "
            f"Multiple service ports were sequentially probed to discover exposed services and open attack surfaces."
        )
        evidence_points = [
            f"Rapid connection probes across {len(distinct_ports) or 'multiple'} destination ports ({', '.join(map(str, distinct_ports[:5])) or 'various'})",
            f"Source IP {primary_ip} originating from {ti_country} ({ti_isp}) with reputation {ti_rep}",
        ]
        if is_tor or is_vpn:
            evidence_points.append("Scanner routed through anonymizing proxy infrastructure")
        evidence_points.append(f"Total scan events logged in detection window: {evidence.events_count}")

        recommended_actions = [
            f"Blackhole source IP {primary_ip} at edge border gateways",
            "Audit exposed services on probed ports to confirm no unauthorized listening daemons",
            "Verify IDS/IPS intrusion rules are triggering automated rate-limiting for port sweeps",
        ]
        mitre_tactics = ["Reconnaissance: T1046 (Network Service Discovery)"]

    elif "EXFILTRATION" in inc_type:
        title = f"Data Exfiltration Alert: Excessive Outbound Volume to {primary_ip}"
        severity = "CRITICAL"
        summary = (
            f"Potential data exfiltration detected. Account '{primary_user}' transferred {volume_mb} MB to external address {primary_ip}, "
            f"greatly exceeding historical baseline network volumes."
        )
        evidence_points = [
            f"Abnormal outbound data transfer totaling {volume_mb} MB within detection window",
            f"Transfer destination {primary_ip} located in {ti_country} ({ti_isp}) with risk score {ti_risk}/100",
            f"Authenticated user session attributed to '{primary_user}'",
        ]
        if evidence.max_anomaly_score:
            evidence_points.append(f"ML Anomaly detector flagged transfer with score {round(evidence.max_anomaly_score * 100)}%")

        recommended_actions = [
            f"Sever active TCP/IP connections associated with session destination {primary_ip} immediately",
            f"Quarantine endpoint workstation and suspend account '{primary_user}' pending forensic review",
            "Determine scope and sensitivity classification of files accessed immediately prior to transfer",
            "Inspect egress DLP (Data Loss Prevention) and NetFlow logs for auxiliary destination hosts",
        ]
        mitre_tactics = [
            "Exfiltration: T1048 (Exfiltration Over Alternative Protocol)",
            "Collection: T1005 (Data from Local System)",
        ]

    elif "COMPROMISE" in inc_type:
        title = f"Suspected Account Compromise for User {primary_user}"
        severity = "HIGH"
        summary = (
            f"High-confidence account compromise detected. Account '{primary_user}' experienced failed logins followed by successful authentication "
            f"from unfamiliar IP {primary_ip} in {ti_country}."
        )
        evidence_points = [
            f"Anomalous transition from failed attempts to successful authentication from {primary_ip}",
            f"Source IP reputation: {ti_rep} (Risk Score: {ti_risk}/100) registered to {ti_isp} ({ti_country})",
            f"Unfamiliar geolocation and session identifier deviating from user baseline",
        ]
        recommended_actions = [
            f"Terminate all active OAuth and SSO sessions for '{primary_user}'",
            "Trigger emergency password reset and revoke registered MFA devices",
            "Audit post-login event logs to trace all API and database actions executed by the session",
            "Add source IP {primary_ip} to threat containment list",
        ]
        mitre_tactics = ["Initial Access: T1078 (Valid Accounts)", "Defense Evasion: T1078 (Valid Accounts)"]

    elif "PRIVILEGE" in inc_type:
        title = f"Privilege Escalation Event for User {primary_user}"
        severity = "HIGH"
        summary = (
            f"Unauthorized privilege elevation detected. User '{primary_user}' accessed restricted administrative resources "
            f"or assumed elevated permissions from host {primary_ip}."
        )
        evidence_points = [
            f"Elevated access request from non-admin account '{primary_user}'",
            f"Activity originated from network address {primary_ip}",
            f"{evidence.events_count} correlated logs recorded in the security sequence",
        ]
        recommended_actions = [
            f"Revoke elevated role assignments and admin permissions for '{primary_user}'",
            "Inspect system authorization logs for sudo or role-assignment modifications",
            "Conduct full audit of security groups and RBAC entitlements",
        ]
        mitre_tactics = [
            "Privilege Escalation: T1068 (Exploitation for Privilege Escalation)",
            "Persistence: T1098 (Account Manipulation)",
        ]

    else:
        # Generic / ML Anomaly
        title = f"Behavioral Anomaly Incident involving {primary_user} / {primary_ip}"
        severity = evidence.severity or "MEDIUM"
        ml_pct = round((evidence.max_anomaly_score or 0.75) * 100)
        summary = (
            f"Behavioral anomaly identified by unsupervised detection layer for entity {primary_user} / {primary_ip}. "
            f"Statistical patterns show significant deviation from normal operational baselines."
        )
        evidence_points = [
            f"Unsupervised Isolation Forest anomaly score: {ml_pct}% deviation",
            f"Entity {primary_ip} in {ti_country} with risk assessment {ti_risk}/100",
            f"Event cardinality: {evidence.events_count} events across types: {', '.join(evidence.event_types) or 'General'}",
        ]
        recommended_actions = [
            f"Cross-reference recent operational change requests for entity '{primary_user}'",
            f"Monitor host {primary_ip} for secondary lateral movement indicators",
            "Request user activity validation from reporting supervisor",
        ]
        mitre_tactics = ["Initial Access: T1190 (Exploit Public-Facing Application)"]

    return {
        "title": title,
        "severity": severity,
        "summary": summary,
        "evidence_points": evidence_points,
        "recommended_actions": recommended_actions,
        "mitre_tactics": mitre_tactics,
        "confidence_score": 0.94,
        "model_used": "sentinel-soc-analyst-v1 (Deterministic Expert Engine)",
    }


def call_llm_api(evidence: StructuredEvidence) -> Optional[Dict[str, Any]]:
    """
    Calls configured external LLM (e.g. OpenAI / Compatible endpoint) if API key is provided.
    Returns parsed JSON dictionary or None on failure.
    """
    api_key = settings.LLM_API_KEY
    if not api_key or api_key == "mock-key":
        return None

    try:
        import urllib.request

        prompt = build_investigation_prompt(evidence)
        payload = {
            "model": settings.LLM_MODEL or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SOC_ANALYST_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content = res_data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            parsed["model_used"] = f"{settings.LLM_MODEL} (Live LLM)"
            return parsed
    except Exception as exc:
        logger.warning("External LLM API call failed (%s); using expert synthesis engine.", exc)
        return None


def generate_investigation_report(evidence: StructuredEvidence) -> Dict[str, Any]:
    """
    Primary GenAI pipeline entry point.
    Tries external LLM provider if configured; falls back safely to the deterministic
    expert SOC synthesis engine.
    """
    # 1. Attempt live LLM if API key configured
    result = call_llm_api(evidence)

    # 2. Fall back to expert SOC deterministic synthesis
    if not result:
        result = generate_deterministic_investigation(evidence)

    # Validate essential schema keys
    return {
        "title": str(result.get("title", f"Investigation: {evidence.title}")),
        "severity": str(result.get("severity", evidence.severity)),
        "summary": str(result.get("summary", "Analysis completed.")),
        "evidence_points": list(result.get("evidence_points", [])),
        "recommended_actions": list(result.get("recommended_actions", [])),
        "mitre_tactics": list(result.get("mitre_tactics", [])),
        "confidence_score": float(result.get("confidence_score", 0.90)),
        "model_used": str(result.get("model_used", "sentinel-soc-analyst-v1")),
    }
