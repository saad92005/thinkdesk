import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.documents.schemas import DocumentOut
from app.documents.service import (
    InvalidFileError,
    UnsupportedFileTypeError,
    create_document,
    get_document,
    list_documents,
    process_document,
)
from app.models.organization import OrganizationMember
from app.models.user import User
from app.organizations.dependencies import get_organization_membership

router = APIRouter(prefix="/organizations/{organization_id}/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document_route(
    organization_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    membership: OrganizationMember = Depends(get_organization_membership),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    content = await file.read()
    try:
        document = await create_document(
            db, organization_id, current_user, file.filename or "untitled.pdf", file.content_type or "", content
        )
    except UnsupportedFileTypeError:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF files are supported")
    except InvalidFileError as exc:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, str(exc))

    background_tasks.add_task(process_document, document.id)
    return document


@router.get("", response_model=list[DocumentOut])
async def list_documents_route(
    organization_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    return await list_documents(db, organization_id)  # type: ignore[return-value]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document_route(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    document = await get_document(db, organization_id, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document  # type: ignore[return-value]
