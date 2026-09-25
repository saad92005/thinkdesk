from typing import Literal

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)


class ResearchCitation(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int | None
    snippet: str


class ResearchFinding(BaseModel):
    claim: str
    confidence: Literal["verified", "single_source"]
    citations: list[ResearchCitation]


class ResearchReport(BaseModel):
    topic: str
    summary: str
    findings: list[ResearchFinding]
    gaps: list[str]
    documents_used: list[str]
