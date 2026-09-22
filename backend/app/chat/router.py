import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.chat.schemas import ChatRequest, ChatResponse, ConversationOut, MessageOut
from app.chat.service import get_conversation_messages, list_conversations, send_message
from app.database import get_db
from app.models.organization import OrganizationMember
from app.models.user import User
from app.organizations.dependencies import get_organization_membership

router = APIRouter(prefix="/organizations/{organization_id}", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_route(
    organization_id: uuid.UUID,
    payload: ChatRequest,
    membership: OrganizationMember = Depends(get_organization_membership),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    conversation, message = await send_message(
        db, organization_id, current_user, payload.conversation_id, payload.message
    )
    return ChatResponse(conversation_id=conversation.id, message=message)  # type: ignore[arg-type]


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations_route(
    organization_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationOut]:
    return await list_conversations(db, organization_id, current_user)  # type: ignore[return-value]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def get_conversation_messages_route(
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    messages = await get_conversation_messages(db, organization_id, conversation_id, current_user)
    if messages is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return messages  # type: ignore[return-value]
