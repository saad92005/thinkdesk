import uuid

from pydantic import BaseModel


class ComparisonRequest(BaseModel):
    document_id_a: uuid.UUID
    document_id_b: uuid.UUID


class ComparisonResult(BaseModel):
    document_a: str
    document_b: str
    summary: str
    similarities: list[str]
    differences: list[str]
    contradictions: list[str]
    truncated: bool
