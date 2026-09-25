from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """One test question in an evaluation run. `expected_keywords` is
    optional: when given, it's used as a cheap, deterministic check that
    retrieval actually surfaced the right material (no LLM judgment
    needed, no room for the judge to hallucinate a pass)."""

    question: str = Field(min_length=1)
    expected_keywords: list[str] = Field(default_factory=list)


class EvalRunRequest(BaseModel):
    cases: list[EvalCase] = Field(min_length=1, max_length=50)


class EvalCaseResult(BaseModel):
    question: str
    answer: str
    retrieved_chunk_count: int
    retrieval_hit: bool | None
    faithfulness: float | None
    relevance: float | None
    judge_notes: str | None = None


class EvalReport(BaseModel):
    results: list[EvalCaseResult]
    retrieval_hit_rate: float | None
    average_faithfulness: float | None
    average_relevance: float | None
