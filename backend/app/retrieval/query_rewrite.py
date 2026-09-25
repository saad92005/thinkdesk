from app.ai.llm import LLMGenerationError, LLMNotConfiguredError, get_llm_provider

# Widens recall, not an open-ended brainstorm -- 2 alternates plus the
# original is enough to catch vocabulary mismatch without tripling the
# number of hybrid searches (and LLM calls) done per query.
MAX_REWRITES = 2

_SYSTEM_PROMPT = (
    "You rewrite search queries to improve document retrieval recall. Given "
    "a user's question, write up to 2 alternative phrasings that preserve "
    "the original meaning but use different wording -- synonyms, expanded "
    "abbreviations, or a more literal/keyword-heavy phrasing. Output exactly "
    "one rewrite per line, nothing else: no numbering, no quotes, no "
    "commentary."
)


def _parse_rewrites(raw: str, original: str) -> list[str]:
    """Turn the LLM's raw multi-line output into a deduplicated list of
    rewrites, dropping anything that just echoes the original query (an LLM
    asked to "rewrite" will sometimes hand the input straight back)."""
    seen = {original.strip().lower()}
    rewrites: list[str] = []
    for line in raw.splitlines():
        candidate = line.strip()
        key = candidate.lower()
        if candidate and key not in seen:
            seen.add(key)
            rewrites.append(candidate)
    return rewrites[:MAX_REWRITES]


def rewrite_query(query: str) -> list[str]:
    """Return the original query plus up to MAX_REWRITES LLM-generated
    alternate phrasings, to widen retrieval recall for questions that don't
    share vocabulary with the source documents (e.g. "refund policy" vs. a
    document that only says "reimbursement terms").

    Always returns the original query first. Falls back to just the
    original on any failure -- rewriting is a recall enhancement, never a
    hard dependency for search to work, so a missing/failing LLM degrades
    search to exactly today's behavior rather than breaking it.
    """
    try:
        provider = get_llm_provider()
        raw = provider.generate(_SYSTEM_PROMPT, query)
    except (LLMNotConfiguredError, LLMGenerationError):
        return [query]

    return [query] + _parse_rewrites(raw, query)
