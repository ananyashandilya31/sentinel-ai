"""create incidents, alerts, and evidence tables

Revision ID: 0002_create_incidents_alerts_evidence
Revises: 0001_create_logs
Create Date: 2026-10-11 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_create_incidents_alerts_evidence"
down_revision: Union[str, None] = "0001_create_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create incidents table
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="OPEN"),
        sa.Column("assigned_to", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incidents_type", "incidents", ["type"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_created_at", "incidents", ["created_at"])

    # 2. Create alerts table
    op.create_table(
        "alerts",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("incident_id", sa.String(length=36), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("rule_name", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("log_id", sa.String(length=36), sa.ForeignKey("logs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alerts_incident_id", "alerts", ["incident_id"])
    op.create_index("ix_alerts_log_id", "alerts", ["log_id"])

    # 3. Create evidence table
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("incident_id", sa.String(length=36), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("log_id", sa.String(length=36), sa.ForeignKey("logs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_incident_id", "evidence", ["incident_id"])
    op.create_index("ix_evidence_log_id", "evidence", ["log_id"])


def downgrade() -> None:
    op.drop_table("evidence")
    op.drop_table("alerts")
    op.drop_table("incidents")
