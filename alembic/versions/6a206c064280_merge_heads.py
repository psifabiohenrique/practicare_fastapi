"""merge_heads

Revision ID: 6a206c064280
Revises: 6990923b39c9, c1d2e3f4a5b6
Create Date: 2026-04-22 18:52:26.634113

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a206c064280'
down_revision: Union[str, Sequence[str], None] = ('6990923b39c9', 'c1d2e3f4a5b6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
