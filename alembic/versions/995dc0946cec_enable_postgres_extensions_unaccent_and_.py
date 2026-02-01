"""enable postgres extensions unaccent and pg_trgm

Revision ID: 995dc0946cec
Revises: 
Create Date: 2026-02-01 12:17:59.981837

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '995dc0946cec'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
