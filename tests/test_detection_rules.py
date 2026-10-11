import uuid
from datetime import datetime, timezone, timedelta
from backend.models.log import Log
from backend.detection.rules import (
    BruteForceRule,
    PortScanRule,
    DataExfiltrationRule,
    AccountCompromiseRule,
    PrivilegeEscalationRule,
)


def make_log(
    user="alice",
    ip="192.168.1.10",
    event_type="LOGIN_SUCCESS",
    timestamp=None,
    port=None,
    bytes_transferred=None,
    session_id="s-test",
) -> Log:
    """Helper factory for creating mock Log instances for rule testing."""
    return Log(
        id=str(uuid.uuid4()),
        user=user,
        ip=ip,
        event_type=event_type,
        timestamp=timestamp or datetime.now(timezone.utc),
        port=port,
        bytes_transferred=bytes_transferred,
        country="US",
        session_id=session_id,
    )


# 1. Brute Force Rule Tests
def test_brute_force_rule_positive():
    rule = BruteForceRule()
    now = datetime.now(timezone.utc)
    # 8 consecutive failed logins within 60 seconds (well within 120s window)
    events = [
        make_log(
            user="admin",
            ip="185.220.101.5",
            event_type="LOGIN_FAILED",
            timestamp=now + timedelta(seconds=i * 5),
        )
        for i in range(8)
    ]
    alerts = rule.evaluate(events)
    assert len(alerts) == 1
    assert alerts[0].rule_name == "Brute Force Authentication"
    assert alerts[0].severity == "HIGH"
    assert alerts[0].incident_type == "BRUTE_FORCE"
    assert len(alerts[0].trigger_log_ids) == 8


def test_brute_force_rule_negative_slow_attempts():
    rule = BruteForceRule()
    now = datetime.now(timezone.utc)
    # 8 failed logins spread out across 30 minutes (exceeds 120s window)
    events = [
        make_log(
            user="admin",
            ip="185.220.101.5",
            event_type="LOGIN_FAILED",
            timestamp=now + timedelta(minutes=i * 4),
        )
        for i in range(8)
    ]
    alerts = rule.evaluate(events)
    assert len(alerts) == 0


def test_brute_force_rule_negative_different_users():
    rule = BruteForceRule()
    now = datetime.now(timezone.utc)
    # 4 failures for alice, 4 for bob: should not trigger threshold of 8 per user
    events = [
        make_log(user="alice", ip="10.0.0.1", event_type="LOGIN_FAILED", timestamp=now + timedelta(seconds=i))
        for i in range(4)
    ] + [
        make_log(user="bob", ip="10.0.0.1", event_type="LOGIN_FAILED", timestamp=now + timedelta(seconds=i))
        for i in range(4)
    ]
    alerts = rule.evaluate(events)
    assert len(alerts) == 0


# 2. Port Scan Rule Tests
def test_port_scan_rule_positive():
    rule = PortScanRule()
    now = datetime.now(timezone.utc)
    # Single IP touching 20 distinct ports within 20 seconds
    events = [
        make_log(
            ip="45.154.255.88",
            port=1000 + i,
            event_type="PORT_CONNECT",
            timestamp=now + timedelta(seconds=i),
        )
        for i in range(20)
    ]
    alerts = rule.evaluate(events)
    assert len(alerts) == 1
    assert alerts[0].incident_type == "PORT_SCAN"
    assert alerts[0].severity == "MEDIUM"
    assert len(alerts[0].trigger_log_ids) == 20


def test_port_scan_rule_negative_repeated_same_port():
    rule = PortScanRule()
    now = datetime.now(timezone.utc)
    # 25 events touching the same port 443 (not distinct ports)
    events = [
        make_log(
            ip="45.154.255.88",
            port=443,
            event_type="PORT_CONNECT",
            timestamp=now + timedelta(seconds=i),
        )
        for i in range(25)
    ]
    alerts = rule.evaluate(events)
    assert len(alerts) == 0


# 3. Data Exfiltration Rule Tests
def test_data_exfiltration_rule_positive():
    rule = DataExfiltrationRule()
    # Outbound transfer of 800 MB (threshold is 500 MB)
    event = make_log(
        user="alice",
        ip="194.26.29.11",
        event_type="DATA_TRANSFER",
        bytes_transferred=838_860_800,
    )
    alerts = rule.evaluate([event])
    assert len(alerts) == 1
    assert alerts[0].incident_type == "DATA_EXFILTRATION"
    assert alerts[0].severity == "CRITICAL"


def test_data_exfiltration_rule_negative_normal_volume():
    rule = DataExfiltrationRule()
    # Typical 15 MB transfer
    event = make_log(
        user="alice",
        ip="194.26.29.11",
        event_type="DATA_TRANSFER",
        bytes_transferred=15_000_000,
    )
    alerts = rule.evaluate([event])
    assert len(alerts) == 0


# 4. Account Compromise Rule Tests
def test_account_compromise_rule_positive():
    rule = AccountCompromiseRule()
    now = datetime.now(timezone.utc)
    # 3 failures -> 1 success -> 250 MB transfer within 2 minutes
    events = [
        make_log(user="charlie", ip="185.23.41.12", event_type="LOGIN_FAILED", timestamp=now + timedelta(seconds=10)),
        make_log(user="charlie", ip="185.23.41.12", event_type="LOGIN_FAILED", timestamp=now + timedelta(seconds=20)),
        make_log(user="charlie", ip="185.23.41.12", event_type="LOGIN_FAILED", timestamp=now + timedelta(seconds=30)),
        make_log(user="charlie", ip="185.23.41.12", event_type="LOGIN_SUCCESS", timestamp=now + timedelta(seconds=50)),
        make_log(
            user="charlie",
            ip="185.23.41.12",
            event_type="DATA_TRANSFER",
            bytes_transferred=300_000_000,
            timestamp=now + timedelta(seconds=80),
        ),
    ]
    alerts = rule.evaluate(events)
    assert len(alerts) == 1
    assert alerts[0].incident_type == "ACCOUNT_COMPROMISE"
    assert alerts[0].severity == "CRITICAL"
    assert len(alerts[0].trigger_log_ids) == 5


def test_account_compromise_rule_negative_no_large_transfer():
    rule = AccountCompromiseRule()
    now = datetime.now(timezone.utc)
    # 3 failures -> success -> tiny 10 KB file (no anomalous exfiltration)
    events = [
        make_log(user="charlie", ip="10.0.0.1", event_type="LOGIN_FAILED", timestamp=now + timedelta(seconds=10)),
        make_log(user="charlie", ip="10.0.0.1", event_type="LOGIN_FAILED", timestamp=now + timedelta(seconds=20)),
        make_log(user="charlie", ip="10.0.0.1", event_type="LOGIN_FAILED", timestamp=now + timedelta(seconds=30)),
        make_log(user="charlie", ip="10.0.0.1", event_type="LOGIN_SUCCESS", timestamp=now + timedelta(seconds=50)),
        make_log(
            user="charlie",
            ip="10.0.0.1",
            event_type="DATA_TRANSFER",
            bytes_transferred=10_000,
            timestamp=now + timedelta(seconds=60),
        ),
    ]
    alerts = rule.evaluate(events)
    assert len(alerts) == 0


# 5. Privilege Escalation Rule Tests
def test_privilege_escalation_rule_positive():
    rule = PrivilegeEscalationRule()
    # Standard user triggers PRIVILEGE_CHANGE
    event = make_log(
        user="intern_john",
        event_type="PRIVILEGE_CHANGE",
    )
    alerts = rule.evaluate([event])
    assert len(alerts) == 1
    assert alerts[0].incident_type == "PRIVILEGE_ESCALATION"
    assert alerts[0].severity == "HIGH"


def test_privilege_escalation_rule_negative_admin():
    rule = PrivilegeEscalationRule()
    # Authorized administrator performs routine PRIVILEGE_CHANGE
    event = make_log(
        user="admin",
        event_type="PRIVILEGE_CHANGE",
    )
    alerts = rule.evaluate([event])
    assert len(alerts) == 0
