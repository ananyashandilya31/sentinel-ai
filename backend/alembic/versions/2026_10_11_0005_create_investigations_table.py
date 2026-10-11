"""create_investigations_table

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investigations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "incident_id",
            sa.String(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence_points", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("recommended_actions", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("mitre_tactics", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.90"),
        sa.Column("model_used", sa.String(50), nullable=False, server_default="sentinel-soc-analyst-v1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_investigations_incident_id", "investigations", ["incident_id"])
    op.create_index("ix_investigations_created_at", "investigations", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_investigations_created_at", table_name="investigations")
    op.drop_index("ix_investigations_incident_id", table_name="investigations")
    op.drop_table("investigations")
