from collections import defaultdict
from datetime import timedelta
from typing import List
from backend.models.log import Log
from backend.detection.base import BaseRule, DetectedAlert
from backend.detection.config import detection_config


class BruteForceRule(BaseRule):
    """
    Detection Rule: Brute Force Authentication
    Triggers when ≥ 8 LOGIN_FAILED events occur for the same user and source IP
    within a 2-minute (120-second) sliding window.
    """
    name: str = "Brute Force Authentication"
    description: str = "Repeated failed login attempts from single IP against a user account."
    severity: str = "HIGH"
    incident_type: str = "BRUTE_FORCE"

    def evaluate(self, events: List[Log]) -> List[DetectedAlert]:
        alerts: List[DetectedAlert] = []
        if not events:
            return alerts

        # Group failed logins by (user, ip)
        groups = defaultdict(list)
        for event in events:
            if event.event_type == "LOGIN_FAILED":
                groups[(event.user, event.ip)].append(event)

        threshold = detection_config.BRUTE_FORCE_FAILED_THRESHOLD
        window_seconds = detection_config.BRUTE_FORCE_WINDOW_SECONDS

        for (user, ip), user_events in groups.items():
            if len(user_events) < threshold:
                continue

            # Sort chronologically
            sorted_events = sorted(user_events, key=lambda e: e.timestamp)

            # Two-pointer sliding window
            left = 0
            for right in range(len(sorted_events)):
                # Shrink window from left until time difference is <= window_seconds
                while (sorted_events[right].timestamp - sorted_events[left].timestamp).total_seconds() > window_seconds:
                    left += 1

                window_count = right - left + 1
                if window_count >= threshold:
                    trigger_logs = sorted_events[left:right + 1]
                    alerts.append(
                        DetectedAlert(
                            rule_name=self.name,
                            severity=self.severity,
                            incident_type=self.incident_type,
                            title=f"Brute Force Detected: {user} from {ip}",
                            description=(
                                f"Detected {window_count} failed logins for user '{user}' "
                                f"from IP '{ip}' within {window_seconds} seconds."
                            ),
                            entity_type="ip",
                            entity_value=ip,
                            trigger_log_ids=[e.id for e in trigger_logs],
                            timestamp=sorted_events[right].timestamp,
                        )
                    )
                    # Advance left pointer to avoid emitting redundant overlapping alert for same burst
                    left = right + 1

        return alerts
