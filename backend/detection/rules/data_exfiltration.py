from typing import List
from backend.models.log import Log
from backend.detection.base import BaseRule, DetectedAlert
from backend.detection.config import detection_config


class DataExfiltrationRule(BaseRule):
    """
    Detection Rule: Data Exfiltration
    Triggers when a single data transfer exceeds the normal baseline threshold (500 MB).
    """
    name: str = "Data Exfiltration Detection"
    description: str = "Anomalously large outbound data volume transfer."
    severity: str = "CRITICAL"
    incident_type: str = "DATA_EXFILTRATION"

    def evaluate(self, events: List[Log]) -> List[DetectedAlert]:
        alerts: List[DetectedAlert] = []
        if not events:
            return alerts

        threshold = detection_config.DATA_EXFILTRATION_BYTES_THRESHOLD

        for event in events:
            if event.event_type == "DATA_TRANSFER" and event.bytes_transferred:
                if event.bytes_transferred >= threshold:
                    mb_size = round(event.bytes_transferred / (1024 * 1024), 2)
                    alerts.append(
                        DetectedAlert(
                            rule_name=self.name,
                            severity=self.severity,
                            incident_type=self.incident_type,
                            title=f"Potential Data Exfiltration: {event.user} ({mb_size} MB)",
                            description=(
                                f"User '{event.user}' transferred {mb_size} MB to IP '{event.ip}' "
                                f"({event.country}), exceeding the 500 MB security threshold."
                            ),
                            entity_type="user",
                            entity_value=event.user,
                            trigger_log_ids=[event.id],
                            timestamp=event.timestamp,
                        )
                    )

        return alerts
