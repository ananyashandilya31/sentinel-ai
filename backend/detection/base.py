from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Any
from backend.models.log import Log


@dataclass
class DetectedAlert:
    """
    Structured alert emitted by a detection rule.
    Captures the rule triggered, severity, entity involved, and associated log IDs for evidence.
    """
    rule_name: str
    severity: str              # LOW, MEDIUM, HIGH, CRITICAL
    incident_type: str         # BRUTE_FORCE, PORT_SCAN, etc.
    title: str
    description: str
    entity_type: str           # "ip" or "user"
    entity_value: str          # e.g. "185.220.101.5" or "admin"
    trigger_log_ids: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class BaseRule(ABC):
    """
    Abstract interface for SentinelAI detection rules.
    Every rule takes a sequence of Log events and returns zero or more DetectedAlert objects.
    """
    name: str = "BaseRule"
    description: str = "Base detection rule interface"
    severity: str = "MEDIUM"
    incident_type: str = "ANOMALY"

    @abstractmethod
    def evaluate(self, events: List[Log]) -> List[DetectedAlert]:
        """
        Evaluates a slice of security events against this detection rule.
        """
        pass
