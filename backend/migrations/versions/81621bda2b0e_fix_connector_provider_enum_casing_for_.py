"""fix connector_provider enum casing for slack and notion

Revision ID: 81621bda2b0e
Revises: 3be7b0b20b11
Create Date: 2026-09-25 18:14:43.483582

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '81621bda2b0e'
down_revision: Union[str, None] = '3be7b0b20b11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The earlier two migrations added 'slack' and 'notion' (lowercase),
    # but SQLAlchemy's Enum column type serializes a Python str-Enum by its
    # member NAME by default (e.g. ConnectorProvider.SLACK -> "SLACK"), not
    # its .value -- matching the very first migration's 'GOOGLE' label.
    # This mismatch was invisible in tests because the test database is
    # built fresh from the current models (Base.metadata.create_all), only
    # surfacing once a real Slack/Notion connection was attempted against
    # this incrementally-migrated database.
    op.execute("ALTER TYPE connector_provider RENAME VALUE 'slack' TO 'SLACK'")
    op.execute("ALTER TYPE connector_provider RENAME VALUE 'notion' TO 'NOTION'")


def downgrade() -> None:
    op.execute("ALTER TYPE connector_provider RENAME VALUE 'SLACK' TO 'slack'")
    op.execute("ALTER TYPE connector_provider RENAME VALUE 'NOTION' TO 'notion'")
