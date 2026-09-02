"""enable pgvector extension

Revision ID: 4f1b8c679186
Revises: a8b4e8b23112
Create Date: 2026-09-02 14:09:34.601676

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f1b8c679186'
down_revision: Union[str, None] = 'a8b4e8b23112'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
