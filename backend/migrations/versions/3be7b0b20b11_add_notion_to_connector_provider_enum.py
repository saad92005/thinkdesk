"""add notion to connector_provider enum

Revision ID: 3be7b0b20b11
Revises: 53fc3c551fb3
Create Date: 2026-09-25 18:06:45.105834

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3be7b0b20b11'
down_revision: Union[str, None] = '53fc3c551fb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE can't run inside the transaction Alembic
    # wraps migrations in by default on Postgres -- autocommit block needed.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE connector_provider ADD VALUE IF NOT EXISTS 'notion'")


def downgrade() -> None:
    # Postgres has no ALTER TYPE ... DROP VALUE -- not attempted, this is
    # a purely additive change.
    pass
