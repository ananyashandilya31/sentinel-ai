from collections import defaultdict
from typing import List
from backend.models.log import Log
from backend.detection.base import BaseRule, DetectedAlert
from backend.detection.config import detection_config


class PortScanRule(BaseRule):
    """
    Detection Rule: Port Scanning
    Triggers when a single source IP touches ≥ 20 distinct network ports
    within a 30-second sliding window.
    """
    name: str = "Port Scan Detection"
    description: str = "Host reconnaissance scanning multiple ports across short timeframe."
    severity: str = "MEDIUM"
    incident_type: str = "PORT_SCAN"

    def evaluate(self, events: List[Log]) -> List[DetectedAlert]:
        alerts: List[DetectedAlert] = []
        if not events:
            return alerts

        # Group port-bearing events by IP
        ip_groups = defaultdict(list)
        for event in events:
            if event.port is not None:
                ip_groups[event.ip].append(event)

        threshold = detection_config.PORT_SCAN_PORTS_THRESHOLD
        window_seconds = detection_config.PORT_SCAN_WINDOW_SECONDS

        for ip, ip_events in ip_groups.items():
            if len(ip_events) < threshold:
                continue

            sorted_events = sorted(ip_events, key=lambda e: e.timestamp)

            left = 0
            for right in range(len(sorted_events)):
                # Slide left until within time window
                while (sorted_events[right].timestamp - sorted_events[left].timestamp).total_seconds() > window_seconds:
                    left += 1

                window_events = sorted_events[left:right + 1]
                distinct_ports = {e.port for e in window_events}

                if len(distinct_ports) >= threshold:
                    alerts.append(
                        DetectedAlert(
                            rule_name=self.name,
                            severity=self.severity,
                            incident_type=self.incident_type,
                            title=f"Port Scan Detected from {ip}",
                            description=(
                                f"IP '{ip}' touched {len(distinct_ports)} distinct ports "
                                f"within {window_seconds} seconds."
                            ),
                            entity_type="ip",
                            entity_value=ip,
                            trigger_log_ids=[e.id for e in window_events],
                            timestamp=sorted_events[right].timestamp,
                        )
                    )
                    # Advance to skip overlapping window for this scan wave
                    left = right + 1

        return alerts
