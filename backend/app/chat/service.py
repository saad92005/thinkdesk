import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMGenerationError, LLMNotConfiguredError, get_llm_provider
from app.chat.prompts import GROUNDED_SYSTEM_PROMPT, build_user_prompt
from app.models.message import Conversation, Message, MessageRole
from app.models.user import User
from app.retrieval.service import search


async def _get_or_create_conversation(
    db: AsyncSession, organization_id: uuid.UUID, user: User, conversation_id: uuid.UUID | None, title_seed: str
) -> Conversation:
    if conversation_id is not None:
        conversation = await db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.organization_id == organization_id
            )
        )
        if conversation is not None:
            return conversation

    conversation = Conversation(
        organization_id=organization_id, user_id=user.id, title=title_seed[:80] or "New conversation"
    )
    db.add(conversation)
    await db.flush()
    return conversation


async def send_message(
    db: AsyncSession,
    organization_id: uuid.UUID,
    user: User,
    conversation_id: uuid.UUID | None,
    message_text: str,
) -> tuple[Conversation, Message]:
    conversation = await _get_or_create_conversation(db, organization_id, user, conversation_id, message_text)

    db.add(Message(conversation_id=conversation.id, role=MessageRole.USER, content=message_text))
    await db.commit()

    results = await search(db, organization_id, message_text, top_k=5)

    if not results:
        answer = (
            "I couldn't find anything in this workspace's knowledge base to answer "
            "that. Try uploading a relevant document first."
        )
        citations = None
    else:
        try:
            provider = get_llm_provider()
            answer = provider.generate(GROUNDED_SYSTEM_PROMPT, build_user_prompt(message_text, results))
        except LLMNotConfiguredError as exc:
            answer = f"I found relevant context, but no LLM is configured to generate an answer yet ({exc})"
        except LLMGenerationError as exc:
            answer = f"I found relevant context, but the AI provider couldn't generate an answer right now ({exc})"

        # Citations always come from the real retrieval results, never
        # parsed out of what the LLM claims to have used -- grounding the
        # citation list independently of the generated text.
        citations = [
            {
                "chunk_id": str(r.chunk_id),
                "document_id": str(r.document_id),
                "filename": r.filename,
                "page_number": r.page_number,
                "snippet": r.text[:280],
            }
            for r in results
        ]

    assistant_message = Message(
        conversation_id=conversation.id, role=MessageRole.ASSISTANT, content=answer, citations=citations
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)
    return conversation, assistant_message


async def list_conversations(db: AsyncSession, organization_id: uuid.UUID, user: User) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.organization_id == organization_id, Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation_messages(
    db: AsyncSession, organization_id: uuid.UUID, conversation_id: uuid.UUID, user: User
) -> list[Message] | None:
    conversation = await db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == organization_id,
            Conversation.user_id == user.id,
        )
    )
    if conversation is None:
        return None
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    )
    return list(result.scalars().all())
