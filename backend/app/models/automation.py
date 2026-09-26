import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AutomationSource(str, enum.Enum):
    GMAIL = "gmail"
    DOCUMENT = "document"


class QueuedDraftStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DISMISSED = "dismissed"


class AutomationRule(Base):
    """A saved recipe for what to draft and where it would post -- running
    it (manually now, or from a real scheduler later; both call the same
    `run_rule()`) only ever creates a QueuedDraft. It never posts anything
    itself: that still requires a human to approve a specific queued draft,
    same as the rest of app/agents/. This is what "automation" can mean
    without breaking the master brief's human-approval rule."""

    __tablename__ = "automation_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[AutomationSource] = mapped_column(Enum(AutomationSource, name="automation_source"), nullable=False)
    gmail_connector_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("connector_accounts.id", ondelete="CASCADE"), nullable=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    slack_connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connector_accounts.id", ondelete="CASCADE"), nullable=False
    )
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QueuedDraft(Base):
    """One automation run's output, waiting for a human decision. Created
    only by AutomationRule runs -- never posted anywhere until a human
    calls the approve endpoint, which is the same post_to_slack() used by
    the rest of the agent actions."""

    __tablename__ = "queued_drafts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(200), nullable=False)
    draft_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_label: Mapped[str] = mapped_column(String(300), nullable=False)
    slack_connector_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[QueuedDraftStatus] = mapped_column(
        Enum(QueuedDraftStatus, name="queued_draft_status"), default=QueuedDraftStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
