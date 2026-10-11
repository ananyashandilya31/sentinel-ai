import csv
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# Normal user pool and baseline IPs
USERS = ["admin", "alice", "bob", "charlie", "devops_sarah", "intern_john"]
INTERNAL_IPS = ["192.168.1.10", "192.168.1.25", "192.168.1.42", "10.0.0.15", "10.0.0.22"]
SAFE_COUNTRIES = ["US", "US", "US", "CA", "GB", "DE"]

# Malicious IP pool
ATTACK_IPS = {
    "brute_force": "185.220.101.5",
    "port_scan": "45.154.255.88",
    "exfiltration": "194.26.29.11",
    "compromise": "185.23.41.12",
    "privilege": "192.168.1.99",
}


def generate_normal_log(base_time: datetime) -> Dict[str, Any]:
    """Generates a routine, benign user activity log."""
    user = random.choice(USERS)
    ip = random.choice(INTERNAL_IPS)
    country = random.choice(SAFE_COUNTRIES)
    session_id = f"s-{user[:3]}-{random.randint(1000, 9999)}"

    # Typical office-hour jitter
    hour = random.choice([9, 10, 11, 12, 13, 14, 15, 16, 17])
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    ts = base_time.replace(hour=hour, minute=minute, second=second)

    # Event distribution: mostly success, small transfers, occasional typo failure
    rand_type = random.random()
    if rand_type < 0.50:
        event_type = "LOGIN_SUCCESS"
        port = random.choice([443, 22, 80])
        bytes_transferred = None
    elif rand_type < 0.85:
        event_type = "DATA_TRANSFER"
        port = random.choice([443, 80])
        # Benign transfers are small: 50 KB to 25 MB
        bytes_transferred = random.randint(50_000, 25_000_000)
    elif rand_type < 0.95:
        event_type = "PORT_CONNECT"
        port = random.choice([80, 443, 8080, 5432, 22])
        bytes_transferred = None
    else:
        # Harmless single typo login failure
        event_type = "LOGIN_FAILED"
        port = 443
        bytes_transferred = None

    return {
        "id": str(uuid.uuid4()),
        "timestamp": ts.isoformat(),
        "user": user,
        "ip": ip,
        "event_type": event_type,
        "port": port,
        "bytes_transferred": bytes_transferred,
        "country": country,
        "session_id": session_id,
        "is_attack": 0,
        "attack_type": "none",
    }


def inject_brute_force(start_time: datetime) -> List[Dict[str, Any]]:
    """Injects ≥ 8 LOGIN_FAILED events for same user/IP within 2 minutes."""
    events = []
    ip = ATTACK_IPS["brute_force"]
    target_user = "admin"
    country = "RU"
    session_id = f"s-bf-{random.randint(100, 999)}"

    for i in range(10):
        ts = start_time + timedelta(seconds=i * 8)  # 10 attempts in 80 seconds
        events.append({
            "id": str(uuid.uuid4()),
            "timestamp": ts.isoformat(),
            "user": target_user,
            "ip": ip,
            "event_type": "LOGIN_FAILED",
            "port": 443,
            "bytes_transferred": None,
            "country": country,
            "session_id": session_id,
            "is_attack": 1,
            "attack_type": "brute_force",
        })
    return events


def inject_port_scan(start_time: datetime) -> List[Dict[str, Any]]:
    """Injects 1 IP touching ≥ 20 distinct ports within 30 seconds."""
    events = []
    ip = ATTACK_IPS["port_scan"]
    country = "CN"
    ports_to_probe = [
        21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445,
        993, 995, 1433, 1521, 3306, 3389, 5432, 5900, 8080, 8443, 9200
    ]

    for idx, port in enumerate(ports_to_probe):
        ts = start_time + timedelta(seconds=idx * 1)  # 23 ports in 23 seconds
        events.append({
            "id": str(uuid.uuid4()),
            "timestamp": ts.isoformat(),
            "user": "anonymous",
            "ip": ip,
            "event_type": "PORT_CONNECT",
            "port": port,
            "bytes_transferred": None,
            "country": country,
            "session_id": f"s-scan-{port}",
            "is_attack": 1,
            "attack_type": "port_scan",
        })
    return events


def inject_data_exfiltration(start_time: datetime) -> List[Dict[str, Any]]:
    """Injects massive outbound transfer (850 MB) far exceeding 20 MB baseline."""
    user = "alice"
    ip = ATTACK_IPS["exfiltration"]
    country = "NL"
    return [{
        "id": str(uuid.uuid4()),
        "timestamp": start_time.isoformat(),
        "user": user,
        "ip": ip,
        "event_type": "DATA_TRANSFER",
        "port": 443,
        "bytes_transferred": 891_289_600,  # ~850 MB
        "country": country,
        "session_id": f"s-exfil-{random.randint(100, 999)}",
        "is_attack": 1,
        "attack_type": "data_exfiltration",
    }]


def inject_account_compromise(start_time: datetime) -> List[Dict[str, Any]]:
    """
    Failed login sequence -> Successful login from new IP -> Massive data transfer.
    """
    events = []
    user = "charlie"
    attacker_ip = ATTACK_IPS["compromise"]
    country = "RU"
    session_id = f"s-comp-{random.randint(100, 999)}"

    # Step 1: 5 rapid failed attempts
    for i in range(5):
        ts = start_time + timedelta(seconds=i * 12)
        events.append({
            "id": str(uuid.uuid4()),
            "timestamp": ts.isoformat(),
            "user": user,
            "ip": attacker_ip,
            "event_type": "LOGIN_FAILED",
            "port": 443,
            "bytes_transferred": None,
            "country": country,
            "session_id": session_id,
            "is_attack": 1,
            "attack_type": "account_compromise",
        })

    # Step 2: Successful login from new foreign IP
    ts_success = start_time + timedelta(seconds=70)
    events.append({
        "id": str(uuid.uuid4()),
        "timestamp": ts_success.isoformat(),
        "user": user,
        "ip": attacker_ip,
        "event_type": "LOGIN_SUCCESS",
        "port": 443,
        "bytes_transferred": None,
        "country": country,
        "session_id": session_id,
        "is_attack": 1,
        "attack_type": "account_compromise",
    })

    # Step 3: Massive outbound transfer right after login
    ts_transfer = start_time + timedelta(seconds=110)
    events.append({
        "id": str(uuid.uuid4()),
        "timestamp": ts_transfer.isoformat(),
        "user": user,
        "ip": attacker_ip,
        "event_type": "DATA_TRANSFER",
        "port": 443,
        "bytes_transferred": 750_000_000,  # 750 MB
        "country": country,
        "session_id": session_id,
        "is_attack": 1,
        "attack_type": "account_compromise",
    })

    return events


def inject_privilege_escalation(start_time: datetime) -> List[Dict[str, Any]]:
    """Standard user suddenly acquires or exercises unauthorized administrative rights."""
    user = "intern_john"
    ip = ATTACK_IPS["privilege"]
    session_id = f"s-priv-{random.randint(100, 999)}"

    return [{
        "id": str(uuid.uuid4()),
        "timestamp": start_time.isoformat(),
        "user": user,
        "ip": ip,
        "event_type": "PRIVILEGE_CHANGE",
        "port": 443,
        "bytes_transferred": None,
        "country": "US",
        "session_id": session_id,
        "is_attack": 1,
        "attack_type": "privilege_escalation",
    }]


def generate_synthetic_logs(
    output_file: str = "data/security_logs.csv",
    total_normal: int = 1000,
) -> str:
    """
    Generates a full synthetic cybersecurity log dataset containing:
    - Normal background user activity
    - Injected attack scenarios with ground-truth labels for ML evaluation
    """
    now = datetime.now(timezone.utc)
    base_time = now - timedelta(days=2)

    all_logs: List[Dict[str, Any]] = []

    # 1. Normal logs across 2 days
    for i in range(total_normal):
        day_offset = random.choice([0, 1])
        current_base = base_time + timedelta(days=day_offset)
        all_logs.append(generate_normal_log(current_base))

    # 2. Inject Attacks at specific time anchors
    all_logs.extend(inject_brute_force(base_time + timedelta(hours=14, minutes=10)))
    all_logs.extend(inject_port_scan(base_time + timedelta(hours=18, minutes=30)))
    all_logs.extend(inject_data_exfiltration(base_time + timedelta(days=1, hours=11, minutes=45)))
    all_logs.extend(inject_account_compromise(base_time + timedelta(days=1, hours=3, minutes=15)))
    all_logs.extend(inject_privilege_escalation(base_time + timedelta(days=1, hours=15, minutes=20)))

    # Sort all logs chronologically
    all_logs.sort(key=lambda x: x["timestamp"])

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

    fieldnames = [
        "id",
        "timestamp",
        "user",
        "ip",
        "event_type",
        "port",
        "bytes_transferred",
        "country",
        "session_id",
        "is_attack",
        "attack_type",
    ]

    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_logs)

    print(f"Generated {len(all_logs)} logs (including injected attacks) at {output_file}")
    return output_file


if __name__ == "__main__":
    generate_synthetic_logs()
