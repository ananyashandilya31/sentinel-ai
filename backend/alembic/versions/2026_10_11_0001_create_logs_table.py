"""create logs table

Revision ID: 0001_create_logs
Revises: None
Create Date: 2026-10-11 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_create_logs"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "logs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user", sa.String(length=100), nullable=False),
        sa.Column("ip", sa.String(length=50), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("bytes_transferred", sa.BigInteger(), nullable=True),
        sa.Column("country", sa.String(length=10), nullable=False, server_default="US"),
        sa.Column("session_id", sa.String(length=100), nullable=False),
    )

    # Primary search and filter indices
    op.create_index("ix_logs_timestamp", "logs", ["timestamp"])
    op.create_index("ix_logs_user", "logs", ["user"])
    op.create_index("ix_logs_ip", "logs", ["ip"])
    op.create_index("ix_logs_event_type", "logs", ["event_type"])

    # Composite query optimization indices
    op.create_index("ix_logs_timestamp_event_type", "logs", ["timestamp", "event_type"])
    op.create_index("ix_logs_user_timestamp", "logs", ["user", "timestamp"])
    op.create_index("ix_logs_ip_timestamp", "logs", ["ip", "timestamp"])


def downgrade() -> None:
    op.drop_index("ix_logs_ip_timestamp", table_name="logs")
    op.drop_index("ix_logs_user_timestamp", table_name="logs")
    op.drop_index("ix_logs_timestamp_event_type", table_name="logs")
    op.drop_index("ix_logs_event_type", table_name="logs")
    op.drop_index("ix_logs_ip", table_name="logs")
    op.drop_index("ix_logs_user", table_name="logs")
    op.drop_index("ix_logs_timestamp", table_name="logs")
    op.drop_table("logs")
