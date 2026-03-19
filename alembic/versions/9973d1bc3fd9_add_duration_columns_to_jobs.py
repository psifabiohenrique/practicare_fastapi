"""Add duration columns to jobs

Revision ID: 9973d1bc3fd9
Revises: a1b2c3d4e5f6
Create Date: 2026-03-19 16:59:58.443437

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9973d1bc3fd9'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "automated_record_jobs",
        sa.Column("audio_duration_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "automated_record_jobs",
        sa.Column(
            "audio_duration_after_vad_seconds", sa.Float(), nullable=True
        ),
    )
    op.add_column(
        "automated_report_jobs",
        sa.Column("audio_duration_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "automated_report_jobs",
        sa.Column(
            "audio_duration_after_vad_seconds", sa.Float(), nullable=True
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("automated_report_jobs", "audio_duration_after_vad_seconds")
    op.drop_column("automated_report_jobs", "audio_duration_seconds")
    op.drop_column("automated_record_jobs", "audio_duration_after_vad_seconds")
    op.drop_column("automated_record_jobs", "audio_duration_seconds")
