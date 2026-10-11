"""create_ip_reputation_table

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ip_reputation",
        sa.Column("ip", sa.String(50), primary_key=True),
        sa.Column("reputation", sa.String(20), nullable=False, server_default="UNKNOWN"),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("country_code", sa.String(10), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("asn", sa.String(50), nullable=True),
        sa.Column("isp", sa.String(100), nullable=True),
        sa.Column("is_tor", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_vpn", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("threat_types", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("total_reports", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="local_seed"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_ip_reputation_ip", "ip_reputation", ["ip"])
    op.create_index("ix_ip_reputation_reputation", "ip_reputation", ["reputation"])
    op.create_index("ix_ip_reputation_risk_score", "ip_reputation", ["risk_score"])


def downgrade() -> None:
    op.drop_index("ix_ip_reputation_risk_score", table_name="ip_reputation")
    op.drop_index("ix_ip_reputation_reputation", table_name="ip_reputation")
    op.drop_index("ix_ip_reputation_ip", table_name="ip_reputation")
    op.drop_table("ip_reputation")
