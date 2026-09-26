import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.service import AgentActionError, draft_document_digest, draft_email_summary, post_to_slack
from app.models.automation import AutomationRule, AutomationSource, QueuedDraft, QueuedDraftStatus


class AutomationError(Exception):
    """A rule couldn't be created or run. Callers turn this into a clear HTTP error."""


async def create_rule(
    db: AsyncSession,
    organization_id: uuid.UUID,
    name: str,
    source: AutomationSource,
    gmail_connector_id: uuid.UUID | None,
    document_id: uuid.UUID | None,
    slack_connector_id: uuid.UUID,
    channel_id: str,
) -> AutomationRule:
    if source == AutomationSource.GMAIL and gmail_connector_id is None:
        raise AutomationError("gmail_connector_id is required for a Gmail-sourced rule")
    if source == AutomationSource.DOCUMENT and document_id is None:
        raise AutomationError("document_id is required for a document-sourced rule")

    rule = AutomationRule(
        organization_id=organization_id,
        name=name,
        source=source,
        gmail_connector_id=gmail_connector_id,
        document_id=document_id,
        slack_connector_id=slack_connector_id,
        channel_id=channel_id,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def list_rules(db: AsyncSession, organization_id: uuid.UUID) -> list[AutomationRule]:
    result = await db.execute(
        select(AutomationRule).where(AutomationRule.organization_id == organization_id).order_by(AutomationRule.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_rule(db: AsyncSession, organization_id: uuid.UUID, rule_id: uuid.UUID) -> None:
    rule = await db.get(AutomationRule, rule_id)
    if rule is None or rule.organization_id != organization_id:
        raise AutomationError("Automation rule not found")
    await db.delete(rule)
    await db.commit()


async def run_rule(db: AsyncSession, organization_id: uuid.UUID, rule_id: uuid.UUID) -> QueuedDraft:
    """Generates a draft from the rule's source and queues it for human
    approval. This is the only thing "running" a rule does -- it never
    posts to Slack itself. A real scheduler could call this on an
    interval; today it's triggered manually from the UI, but the safety
    property (nothing external happens without a separate approve call)
    is identical either way."""
    rule = await db.get(AutomationRule, rule_id)
    if rule is None or rule.organization_id != organization_id:
        raise AutomationError("Automation rule not found")
    if not rule.active:
        raise AutomationError("This rule is disabled")

    try:
        if rule.source == AutomationSource.GMAIL:
            draft_text, count = await draft_email_summary(db, organization_id, rule.gmail_connector_id, max_results=10)
            source_label = f"{count} recent email(s)"
        else:
            draft_text, filename, truncated = await draft_document_digest(db, organization_id, rule.document_id)
            source_label = f"{filename}{' (truncated)' if truncated else ''}"
    except AgentActionError as exc:
        raise AutomationError(f"Could not run rule: {exc}") from exc

    queued = QueuedDraft(
        organization_id=organization_id,
        rule_id=rule.id,
        rule_name=rule.name,
        draft_text=draft_text,
        source_label=source_label,
        slack_connector_id=rule.slack_connector_id,
        channel_id=rule.channel_id,
    )
    db.add(queued)
    rule.last_run_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(queued)
    return queued


async def list_queue(db: AsyncSession, organization_id: uuid.UUID) -> list[QueuedDraft]:
    result = await db.execute(
        select(QueuedDraft)
        .where(QueuedDraft.organization_id == organization_id, QueuedDraft.status == QueuedDraftStatus.PENDING)
        .order_by(QueuedDraft.created_at.desc())
    )
    return list(result.scalars().all())


async def approve_queued_draft(db: AsyncSession, organization_id: uuid.UUID, draft_id: uuid.UUID, message: str) -> str:
    """The only write in this module. Posts the human-approved (possibly
    edited) text via the same post_to_slack() every other agent action
    uses -- there is still exactly one place in the codebase that writes
    to Slack."""
    queued = await db.get(QueuedDraft, draft_id)
    if queued is None or queued.organization_id != organization_id:
        raise AutomationError("Queued draft not found")
    if queued.status != QueuedDraftStatus.PENDING:
        raise AutomationError("This draft was already handled")

    try:
        ts = await post_to_slack(db, organization_id, queued.slack_connector_id, queued.channel_id, message)
    except AgentActionError as exc:
        raise AutomationError(f"Could not post to Slack: {exc}") from exc

    queued.status = QueuedDraftStatus.APPROVED
    await db.commit()
    return ts


async def dismiss_queued_draft(db: AsyncSession, organization_id: uuid.UUID, draft_id: uuid.UUID) -> None:
    queued = await db.get(QueuedDraft, draft_id)
    if queued is None or queued.organization_id != organization_id:
        raise AutomationError("Queued draft not found")
    if queued.status != QueuedDraftStatus.PENDING:
        raise AutomationError("This draft was already handled")
    queued.status = QueuedDraftStatus.DISMISSED
    await db.commit()
