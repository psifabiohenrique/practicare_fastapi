"""add report_type and system_prompt to treatment_reports

Revision ID: b2c3d4e5f6a7
Revises: f71506e547e2
Create Date: 2026-04-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "f71506e547e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define the enum type
reporttype_enum = sa.Enum(
    "COMPLETO", "PERIODICO", "FOCADO", name="reporttype"
)


def upgrade() -> None:
    # Create the ENUM type in the database
    reporttype_enum.create(op.get_bind(), checkfirst=True)

    # Add report_type column with server default 'PERIODICO'
    # so all existing rows get the default value
    op.add_column(
        "treatment_reports",
        sa.Column(
            "report_type",
            reporttype_enum,
            nullable=False,
            server_default="PERIODICO",
        ),
    )

    # Add system_prompt column (nullable for focused reports)
    op.add_column(
        "treatment_reports",
        sa.Column("system_prompt", sa.Text(), nullable=True),
    )

    # Remove server_default after population so it's not persisted
    op.alter_column("treatment_reports", "report_type", server_default=None)


def downgrade() -> None:
    op.drop_column("treatment_reports", "system_prompt")
    op.drop_column("treatment_reports", "report_type")
    reporttype_enum.drop(op.get_bind(), checkfirst=True)
