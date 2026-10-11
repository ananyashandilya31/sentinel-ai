from collections import defaultdict
from typing import List
from backend.models.log import Log
from backend.detection.base import BaseRule, DetectedAlert
from backend.detection.config import detection_config


class AccountCompromiseRule(BaseRule):
    """
    Detection Rule: Account Compromise Kill Chain
    Detects the multi-stage attack pattern:
    1. Multiple failed logins (≥3)
    2. Followed by a successful login
    3. Followed by an abnormal data transfer (≥200 MB) within a 5-minute window.
    """
    name: str = "Account Compromise Kill Chain"
    description: str = "Correlated failed logins followed by successful entry and exfiltration."
    severity: str = "CRITICAL"
    incident_type: str = "ACCOUNT_COMPROMISE"

    def evaluate(self, events: List[Log]) -> List[DetectedAlert]:
        alerts: List[DetectedAlert] = []
        if not events:
            return alerts

        # Group by user
        user_groups = defaultdict(list)
        for event in events:
            user_groups[event.user].append(event)

        window_seconds = detection_config.ACCOUNT_COMPROMISE_WINDOW_SECONDS
        failed_threshold = detection_config.ACCOUNT_COMPROMISE_FAILED_THRESHOLD
        bytes_threshold = detection_config.ACCOUNT_COMPROMISE_BYTES_THRESHOLD

        for user, user_events in user_groups.items():
            sorted_events = sorted(user_events, key=lambda e: e.timestamp)

            # Slide through event stream looking for sequence: Failures -> Success -> Large Transfer
            for i in range(len(sorted_events)):
                # Check for start of sequence: failed logins
                failed_logs = []
                idx = i
                while idx < len(sorted_events) and sorted_events[idx].event_type == "LOGIN_FAILED":
                    failed_logs.append(sorted_events[idx])
                    idx += 1

                if len(failed_logs) < failed_threshold:
                    continue

                # Next event after failures must be LOGIN_SUCCESS within window
                if idx >= len(sorted_events) or sorted_events[idx].event_type != "LOGIN_SUCCESS":
                    continue

                success_log = sorted_events[idx]
                if (success_log.timestamp - failed_logs[0].timestamp).total_seconds() > window_seconds:
                    continue

                # Subsequent event within window must be large DATA_TRANSFER
                idx += 1
                transfer_log = None
                while idx < len(sorted_events):
                    candidate = sorted_events[idx]
                    if (candidate.timestamp - failed_logs[0].timestamp).total_seconds() > window_seconds:
                        break
                    if candidate.event_type == "DATA_TRANSFER" and (candidate.bytes_transferred or 0) >= bytes_threshold:
                        transfer_log = candidate
                        break
                    idx += 1

                if transfer_log:
                    trigger_logs = failed_logs + [success_log, transfer_log]
                    mb_size = round((transfer_log.bytes_transferred or 0) / (1024 * 1024), 2)
                    alerts.append(
                        DetectedAlert(
                            rule_name=self.name,
                            severity=self.severity,
                            incident_type=self.incident_type,
                            title=f"Account Compromise: {user} ({success_log.ip})",
                            description=(
                                f"Account '{user}' suffered {len(failed_logs)} failed logins, "
                                f"followed by successful login from IP '{success_log.ip}', "
                                f"and outbound transfer of {mb_size} MB."
                            ),
                            entity_type="user",
                            entity_value=user,
                            trigger_log_ids=[e.id for e in trigger_logs],
                            timestamp=transfer_log.timestamp,
                        )
                    )

        return alerts
