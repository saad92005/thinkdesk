import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConnectorProvider(str, enum.Enum):
    GOOGLE = "google"
    SLACK = "slack"


class ConnectorAccount(Base):
    """One connected third-party account (e.g. a Gmail inbox, a Slack
    workspace) for a workspace. Tokens are stored encrypted
    (app/connectors/crypto.py) -- never in plaintext, even though they're
    only as safe as the database they sit in either way; encryption at
    rest is table stakes, not a substitute for real infrastructure
    security."""

    __tablename__ = "connector_accounts"
    __table_args__ = (UniqueConstraint("organization_id", "provider", "account_label", name="uq_connector_account"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    connected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[ConnectorProvider] = mapped_column(
        Enum(ConnectorProvider, name="connector_provider"), nullable=False
    )
    # A human-readable identifier for the connected account -- an email
    # address for Google, a workspace name for Slack. Not every provider
    # has an "email," so this is deliberately generic rather than named
    # after Google's specific concept.
    account_label: Mapped[str] = mapped_column(String(320), nullable=False)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
