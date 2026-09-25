import json
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMGenerationError, LLMNotConfiguredError, get_llm_provider
from app.chat.prompts import GROUNDED_SYSTEM_PROMPT, build_user_prompt
from app.evaluation.schemas import EvalCase, EvalCaseResult, EvalReport
from app.retrieval.service import search

_JUDGE_SYSTEM_PROMPT = (
    "You are grading a retrieval-augmented AI assistant's answer. You are given "
    "the retrieved context excerpts, the question, and the generated answer. "
    "Score two things on a 0.0-1.0 scale:\n"
    "- faithfulness: does every claim in the answer come from the context "
    "excerpts, with nothing invented or added from outside knowledge?\n"
    "- relevance: does the answer actually address the question asked?\n"
    'Respond with ONLY a JSON object, nothing else: {"faithfulness": <0-1>, '
    '"relevance": <0-1>, "notes": "<one short sentence>"}'
)


def _parse_judge_response(raw: str) -> tuple[float | None, float | None, str | None]:
    """The judge is asked for bare JSON but LLMs sometimes wrap it in prose
    or code fences -- pull out the first {...} block rather than trusting
    the whole response to be valid JSON. Any parse failure returns all-None
    (an honestly missing score), never a guessed number."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None, None, None
    try:
        data = json.loads(match.group(0))
        faithfulness = max(0.0, min(1.0, float(data["faithfulness"])))
        relevance = max(0.0, min(1.0, float(data["relevance"])))
        notes = str(data["notes"]) if data.get("notes") else None
        return faithfulness, relevance, notes
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return None, None, None


def _judge_answer(question: str, context_text: str, answer: str) -> tuple[float | None, float | None, str | None]:
    try:
        provider = get_llm_provider()
        raw = provider.generate(
            _JUDGE_SYSTEM_PROMPT,
            f"Context excerpts:\n\n{context_text}\n\nQuestion: {question}\n\nGenerated answer: {answer}",
        )
    except (LLMNotConfiguredError, LLMGenerationError):
        return None, None, None
    return _parse_judge_response(raw)


async def _evaluate_case(db: AsyncSession, organization_id: uuid.UUID, case: EvalCase) -> EvalCaseResult:
    retrieval = await search(db, organization_id, case.question, top_k=5)
    context_text = "\n\n".join(r.text for r in retrieval)

    generation_failed = False
    if not retrieval:
        answer = "No relevant context was found in this workspace's knowledge base."
    else:
        try:
            provider = get_llm_provider()
            answer = provider.generate(GROUNDED_SYSTEM_PROMPT, build_user_prompt(case.question, retrieval))
        except LLMNotConfiguredError as exc:
            answer, generation_failed = f"[no LLM configured: {exc}]", True
        except LLMGenerationError as exc:
            answer, generation_failed = f"[generation failed: {exc}]", True

    retrieval_hit: bool | None = None
    if case.expected_keywords:
        haystack = context_text.lower()
        retrieval_hit = any(keyword.lower() in haystack for keyword in case.expected_keywords)

    faithfulness = relevance = judge_notes = None
    if retrieval and not generation_failed:
        faithfulness, relevance, judge_notes = _judge_answer(case.question, context_text, answer)

    return EvalCaseResult(
        question=case.question,
        answer=answer,
        retrieved_chunk_count=len(retrieval),
        retrieval_hit=retrieval_hit,
        faithfulness=faithfulness,
        relevance=relevance,
        judge_notes=judge_notes,
    )


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


async def run_evaluation(db: AsyncSession, organization_id: uuid.UUID, cases: list[EvalCase]) -> EvalReport:
    """Run each case through the exact same retrieval + generation path a
    real chat message takes (`app.retrieval.service.search` +
    `app.chat.prompts`), then score it two ways: a deterministic
    keyword-in-context check for retrieval, and an LLM-as-judge score for
    the generated answer's faithfulness/relevance. Neither score is
    fabricated when it can't be computed (no keywords given, no LLM
    configured, judge output unparseable) -- it's reported as missing
    (None), not defaulted to a fake pass or fail.
    """
    results = [await _evaluate_case(db, organization_id, case) for case in cases]

    hits = [r.retrieval_hit for r in results if r.retrieval_hit is not None]
    return EvalReport(
        results=results,
        retrieval_hit_rate=(sum(hits) / len(hits)) if hits else None,
        average_faithfulness=_average([r.faithfulness for r in results if r.faithfulness is not None]),
        average_relevance=_average([r.relevance for r in results if r.relevance is not None]),
    )
