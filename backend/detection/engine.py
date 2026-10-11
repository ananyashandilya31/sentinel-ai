from typing import List
from backend.models.log import Log
from backend.detection.base import BaseRule, DetectedAlert
from backend.detection.rules import (
    BruteForceRule,
    PortScanRule,
    DataExfiltrationRule,
    AccountCompromiseRule,
    PrivilegeEscalationRule,
)


class DetectionEngine:
    """
    Central Detection Engine orchestrator for SentinelAI.
    Manages active rule sets and evaluates security logs against all configured rules.
    """

    def __init__(self, rules: List[BaseRule] = None):
        if rules is not None:
            self.rules = rules
        else:
            # Default to all 5 built-in detection rules
            self.rules = [
                BruteForceRule(),
                PortScanRule(),
                DataExfiltrationRule(),
                AccountCompromiseRule(),
                PrivilegeEscalationRule(),
            ]

    def register_rule(self, rule: BaseRule) -> None:
        """Adds a new detection rule to the active evaluation pipeline."""
        self.rules.append(rule)

    def evaluate(self, events: List[Log]) -> List[DetectedAlert]:
        """
        Runs all registered detection rules against the provided batch/stream of events.
        Returns a consolidated list of DetectedAlert instances.
        """
        all_alerts: List[DetectedAlert] = []
        if not events:
            return all_alerts

        for rule in self.rules:
            try:
                rule_alerts = rule.evaluate(events)
                all_alerts.extend(rule_alerts)
            except Exception as exc:
                print(f"[DetectionEngine] Error executing rule '{rule.name}': {exc}")

        return all_alerts


# Singleton engine instance
default_engine = DetectionEngine()
