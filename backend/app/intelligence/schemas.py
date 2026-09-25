import uuid

from pydantic import BaseModel, Field


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


class ExtractedField(BaseModel):
    label: str
    value: str


class ExtractionResult(BaseModel):
    document: str
    fields: list[ExtractedField]
    truncated: bool


class ReportRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(min_length=1, max_length=5)
    focus: str | None = Field(default=None, max_length=500)


class ReportResult(BaseModel):
    title: str
    documents: list[str]
    overview: str
    key_findings: list[str]
    risks_or_gaps: list[str]
    recommendations: list[str]
    truncated: bool
