from tests.pdf_fixture import make_pdf_bytes


async def _create_org_with_policy_doc(client, email: str) -> str:
    await client.post("/auth/signup", json={"email": email, "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    pdf_bytes = make_pdf_bytes(
        [
            "ThinkDesk Test Policy",
            "Refund Policy: full refunds within 30 days of purchase.",
        ]
    )
    await client.post(
        f"/organizations/{org_id}/documents",
        files={"file": ("policy.pdf", pdf_bytes, "application/pdf")},
    )
    return org_id


async def test_evaluation_run_scores_a_hit_and_a_miss_case(client):
    org_id = await _create_org_with_policy_doc(client, "evaluser@example.com")

    response = await client.post(
        f"/organizations/{org_id}/evaluation/run",
        json={
            "cases": [
                {"question": "What is the refund policy?", "expected_keywords": ["refund"]},
                {"question": "What is the refund policy?", "expected_keywords": ["unrelated nonsense term"]},
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    results = body["results"]
    assert len(results) == 2
    assert results[0]["retrieval_hit"] is True
    assert results[1]["retrieval_hit"] is False
    assert body["retrieval_hit_rate"] == 0.5
    # A real Groq key is configured in this environment -- the judge should
    # produce real scores, not silently skip.
    assert results[0]["faithfulness"] is not None
    assert 0.0 <= results[0]["faithfulness"] <= 1.0


async def test_evaluation_case_without_expected_keywords_skips_retrieval_check(client):
    org_id = await _create_org_with_policy_doc(client, "evaluser2@example.com")

    response = await client.post(
        f"/organizations/{org_id}/evaluation/run",
        json={"cases": [{"question": "What is the refund policy?"}]},
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["retrieval_hit"] is None


async def test_evaluation_with_no_documents_reports_no_relevant_context(client):
    await client.post("/auth/signup", json={"email": "evalempty@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    response = await client.post(
        f"/organizations/{org_id}/evaluation/run",
        json={"cases": [{"question": "Anything at all?", "expected_keywords": ["anything"]}]},
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["retrieved_chunk_count"] == 0
    assert result["faithfulness"] is None
    assert "no relevant context" in result["answer"].lower()


async def test_viewer_cannot_run_evaluation(client, second_client):
    org_id = await _create_org_with_policy_doc(client, "evalowner@example.com")
    await second_client.post("/auth/signup", json={"email": "evalviewer@example.com", "password": "correcthorse123"})
    await client.post(
        f"/organizations/{org_id}/members", json={"email": "evalviewer@example.com", "role": "viewer"}
    )

    response = await second_client.post(
        f"/organizations/{org_id}/evaluation/run",
        json={"cases": [{"question": "What is the refund policy?"}]},
    )

    assert response.status_code == 403
