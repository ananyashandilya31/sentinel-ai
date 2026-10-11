import uuid
from datetime import datetime, timezone
import json
from typing import List, Optional
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from backend.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class IPReputation(Base):
    """
    SQLAlchemy ORM Model representing Threat Intelligence for an IP address.
    Stores reputation, risk score (0-100), geolocation, ASN, Tor/VPN indicators,
    and associated threat category tags.
    """
    __tablename__ = "ip_reputation"

    ip = Column(String(50), primary_key=True, index=True)
    reputation = Column(String(20), nullable=False, default="UNKNOWN", index=True)  # MALICIOUS, SUSPICIOUS, CLEAN, UNKNOWN
    risk_score = Column(Integer, nullable=False, default=0, index=True)  # 0 to 100
    country = Column(String(100), nullable=True)
    country_code = Column(String(10), nullable=True)
    city = Column(String(100), nullable=True)
    asn = Column(String(50), nullable=True)
    isp = Column(String(100), nullable=True)
    is_tor = Column(Boolean, nullable=False, default=False)
    is_vpn = Column(Boolean, nullable=False, default=False)
    threat_types = Column(Text, nullable=False, default="[]")  # JSON-serialized array of tags
    total_reports = Column(Integer, nullable=False, default=0)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    source = Column(String(50), nullable=False, default="local_seed")  # local_seed, external_api, heuristic
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    @property
    def threat_tags_list(self) -> List[str]:
        """Deserializes threat_types JSON text to a Python list."""
        if not self.threat_types:
            return []
        try:
            val = json.loads(self.threat_types)
            return val if isinstance(val, list) else [str(val)]
        except Exception:
            return [t.strip() for t in self.threat_types.split(",") if t.strip()]

    def set_threat_tags(self, tags: List[str]) -> None:
        """Serializes list of tags to JSON string."""
        self.threat_types = json.dumps(tags or [])

    def __repr__(self) -> str:
        return f"<IPReputation ip={self.ip} rep={self.reputation} score={self.risk_score} country={self.country}>"
