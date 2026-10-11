from typing import List
from backend.models.log import Log
from backend.detection.base import BaseRule, DetectedAlert
from backend.detection.config import detection_config


class PrivilegeEscalationRule(BaseRule):
    """
    Detection Rule: Unauthorized Privilege Escalation
    Triggers when a non-administrative account generates a PRIVILEGE_CHANGE event.
    """
    name: str = "Unauthorized Privilege Escalation"
    description: str = "Standard user account invoked or received elevated administrative rights."
    severity: str = "HIGH"
    incident_type: str = "PRIVILEGE_ESCALATION"

    def evaluate(self, events: List[Log]) -> List[DetectedAlert]:
        alerts: List[DetectedAlert] = []
        if not events:
            return alerts

        authorized_admins = set(detection_config.AUTHORIZED_ADMINS)

        for event in events:
            if event.event_type == detection_config.PRIVILEGE_CHANGE_EVENT_TYPE:
                # If standard non-admin account executes or undergoes privilege escalation
                if event.user not in authorized_admins:
                    alerts.append(
                        DetectedAlert(
                            rule_name=self.name,
                            severity=self.severity,
                            incident_type=self.incident_type,
                            title=f"Privilege Escalation: {event.user}",
                            description=(
                                f"Non-administrative user '{event.user}' triggered a PRIVILEGE_CHANGE "
                                f"event from IP '{event.ip}' ({event.country})."
                            ),
                            entity_type="user",
                            entity_value=event.user,
                            trigger_log_ids=[event.id],
                            timestamp=event.timestamp,
                        )
                    )

        return alerts
