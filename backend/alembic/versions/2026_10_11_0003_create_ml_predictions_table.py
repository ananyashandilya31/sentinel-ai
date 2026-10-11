"""create_ml_predictions_table

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ml_predictions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ip", sa.String(50), nullable=False),
        sa.Column("anomaly_score", sa.Float, nullable=False),
        sa.Column("is_anomaly", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("raw_if_score", sa.Float, nullable=False),
        sa.Column("feature_vector", sa.Text, nullable=False, server_default="{}"),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_ml_predictions_ip", "ml_predictions", ["ip"])
    op.create_index("ix_ml_predictions_evaluated_at", "ml_predictions", ["evaluated_at"])
    op.create_index("ix_ml_predictions_ip_evaluated", "ml_predictions", ["ip", "evaluated_at"])
    op.create_index("ix_ml_predictions_is_anomaly", "ml_predictions", ["is_anomaly"])


def downgrade() -> None:
    op.drop_index("ix_ml_predictions_is_anomaly", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_ip_evaluated", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_evaluated_at", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_ip", table_name="ml_predictions")
    op.drop_table("ml_predictions")
