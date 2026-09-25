"""rename account_email to account_label, add slack provider

Revision ID: 373c17eff06b
Revises: bd1218406a77
Create Date: 2026-09-25 15:59:40.453272

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '373c17eff06b'
down_revision: Union[str, None] = 'bd1218406a77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A real rename (not drop+add) -- preserves any already-connected
    # accounts instead of destroying the column's data.
    op.alter_column('connector_accounts', 'account_email', new_column_name='account_label')
    op.drop_constraint('uq_connector_account', 'connector_accounts', type_='unique')
    op.create_unique_constraint(
        'uq_connector_account', 'connector_accounts', ['organization_id', 'provider', 'account_label']
    )
    # ALTER TYPE ... ADD VALUE can't run inside the transaction Alembic
    # wraps migrations in by default on Postgres -- autocommit block needed.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE connector_provider ADD VALUE IF NOT EXISTS 'slack'")


def downgrade() -> None:
    # Postgres has no ALTER TYPE ... DROP VALUE -- removing 'slack' from
    # the enum would need a full type rebuild, not attempted here since
    # this is a purely additive change.
    op.drop_constraint('uq_connector_account', 'connector_accounts', type_='unique')
    op.create_unique_constraint(
        'uq_connector_account', 'connector_accounts', ['organization_id', 'provider', 'account_email']
    )
    op.alter_column('connector_accounts', 'account_label', new_column_name='account_email')
