import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMGenerationError, LLMNotConfiguredError, get_llm_provider
from app.connectors import google_oauth, service as connector_service, slack_oauth
from app.connectors.crypto import ConnectorEncryptionNotConfiguredError
from app.models.connector import ConnectorProvider

_SUMMARY_SYSTEM_PROMPT = (
    "You write a brief, professional status update summarizing a list of recent "
    "emails, suitable to post directly in a team Slack channel. Use ONLY the "
    "emails given -- never invent a sender, subject, or detail that isn't there. "
    "Plain text, no markdown headers, under 150 words."
)


class AgentActionError(Exception):
    """A connector call or LLM call failed while preparing or executing an
    agent action. Callers turn this into a clear HTTP error."""


async def draft_email_summary(
    db: AsyncSession, organization_id: uuid.UUID, gmail_connector_id: uuid.UUID, max_results: int
) -> tuple[str, int]:
    """Read-only: fetches recent emails and asks the LLM to summarize them.
    Nothing is sent or posted anywhere -- this is the "propose" half of the
    propose/approve/execute loop. The caller (an agent UI) is expected to
    show `draft_text` to a human before anything reaches post_to_slack."""
    account = await connector_service.get_connection(db, organization_id, gmail_connector_id)
    if account is None or account.provider != ConnectorProvider.GOOGLE:
        raise AgentActionError("Gmail connector not found in this workspace")

    try:
        access_token = await connector_service.get_valid_access_token(db, account)
        messages = await google_oauth.list_recent_messages(access_token, max_results=max_results)
    except (google_oauth.GoogleOAuthError, ConnectorEncryptionNotConfiguredError) as exc:
        raise AgentActionError(f"Could not read Gmail: {exc}") from exc

    if not messages:
        return "No recent emails to summarize.", 0

    email_list = "\n\n".join(
        f"From: {m['from']}\nSubject: {m['subject']}\nSnippet: {m['snippet']}" for m in messages
    )
    try:
        provider = get_llm_provider()
        draft = provider.generate(_SUMMARY_SYSTEM_PROMPT, email_list)
    except (LLMNotConfiguredError, LLMGenerationError) as exc:
        raise AgentActionError(f"Could not generate summary: {exc}") from exc

    return draft.strip(), len(messages)


async def post_to_slack(
    db: AsyncSession, organization_id: uuid.UUID, slack_connector_id: uuid.UUID, channel_id: str, message: str
) -> str:
    """The "execute" half. Only ever called from the router after a human
    has explicitly approved `message` via a separate, deliberate request --
    this function has no concept of a draft, it just sends what it's told."""
    account = await connector_service.get_connection(db, organization_id, slack_connector_id)
    if account is None or account.provider != ConnectorProvider.SLACK:
        raise AgentActionError("Slack connector not found in this workspace")

    try:
        access_token = await connector_service.get_valid_access_token(db, account)
        result = await slack_oauth.post_message(access_token, channel_id, message)
    except slack_oauth.SlackOAuthError as exc:
        hint = " (reconnect Slack -- this connector was authorized before chat:write was added)" if "missing_scope" in str(exc) else ""
        raise AgentActionError(f"Could not post to Slack: {exc}{hint}") from exc
    except ConnectorEncryptionNotConfiguredError as exc:
        raise AgentActionError(f"Could not post to Slack: {exc}") from exc

    return result["ts"]
