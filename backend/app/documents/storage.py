import uuid
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


def _upload_dir(organization_id: uuid.UUID) -> Path:
    upload_dir = Path(settings.storage_root) / str(organization_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def save_upload(organization_id: uuid.UUID, document_id: uuid.UUID, content: bytes) -> str:
    path = _upload_dir(organization_id) / f"{document_id}.pdf"
    path.write_bytes(content)
    return str(path)
