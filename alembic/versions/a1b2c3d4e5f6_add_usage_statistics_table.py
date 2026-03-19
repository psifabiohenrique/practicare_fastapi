"""Add usage_statistics table

Revision ID: a1b2c3d4e5f6
Revises: 5a42d90b5c8e
Create Date: 2026-03-19 14:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "5a42d90b5c8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create usage_statistics table."""
    op.create_table(
        "usage_statistics",
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column("user_uuid", sa.UUID(), nullable=False),
        sa.Column("job_uuid", sa.UUID(), nullable=True),
        sa.Column(
            "process_type",
            sa.Enum(
                "TRANSCRIPTION",
                "RECORD_GENERATION",
                "REPORT_GENERATION",
                name="processtype",
            ),
            nullable=False,
        ),
        sa.Column(
            "input_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "output_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("audio_duration_seconds", sa.Float(), nullable=True),
        sa.Column(
            "audio_duration_after_vad_seconds", sa.Float(), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_uuid"],
            ["users.uuid"],
        ),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(
        op.f("ix_usage_statistics_uuid"),
        "usage_statistics",
        ["uuid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_usage_statistics_user_uuid"),
        "usage_statistics",
        ["user_uuid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_usage_statistics_created_at"),
        "usage_statistics",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop usage_statistics table."""
    op.drop_index(
        op.f("ix_usage_statistics_created_at"),
        table_name="usage_statistics",
    )
    op.drop_index(
        op.f("ix_usage_statistics_user_uuid"),
        table_name="usage_statistics",
    )
    op.drop_index(
        op.f("ix_usage_statistics_uuid"),
        table_name="usage_statistics",
    )
    op.drop_table("usage_statistics")
    op.execute("DROP TYPE IF EXISTS processtype")
