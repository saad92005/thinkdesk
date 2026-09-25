from app.ai.llm import LLMNotConfiguredError
from app.retrieval import query_rewrite


def test_parse_rewrites_deduplicates_and_excludes_echo_of_original():
    raw = (
        "What is the refund policy?\n"
        "What are the terms for reimbursement?\n"
        "What is the refund policy?\n"
        "Refund and return terms"
    )

    rewrites = query_rewrite._parse_rewrites(raw, "What is the refund policy?")

    assert rewrites == ["What are the terms for reimbursement?", "Refund and return terms"]


def test_parse_rewrites_caps_at_max_rewrites():
    raw = "\n".join(f"variant {i}" for i in range(5))

    rewrites = query_rewrite._parse_rewrites(raw, "original")

    assert len(rewrites) == query_rewrite.MAX_REWRITES


def test_parse_rewrites_ignores_blank_lines():
    raw = "\n\nAlternate phrasing\n\n   \n"

    rewrites = query_rewrite._parse_rewrites(raw, "original")

    assert rewrites == ["Alternate phrasing"]


def test_rewrite_query_falls_back_to_original_when_llm_not_configured(monkeypatch):
    def _raise():
        raise LLMNotConfiguredError("no key")

    monkeypatch.setattr(query_rewrite, "get_llm_provider", _raise)

    assert query_rewrite.rewrite_query("what is X?") == ["what is X?"]
