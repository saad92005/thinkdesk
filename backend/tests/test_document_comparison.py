import pytest
from tests.pdf_fixture import make_pdf_bytes


async def _upload(client, org_id: str, filename: str, lines: list[str]) -> str:
    upload = await client.post(
        f"/organizations/{org_id}/documents",
        files={"file": (filename, make_pdf_bytes(lines), "application/pdf")},
    )
    return upload.json()["id"]


@pytest.mark.live_llm
async def test_compare_two_documents_returns_grounded_structured_result(client):
    await client.post("/auth/signup", json={"email": "compare1@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    doc_a = await _upload(client, org_id, "policy_2023.pdf", ["Refund Policy: full refunds within 30 days of purchase."])
    doc_b = await _upload(client, org_id, "policy_2024.pdf", ["Refund Policy: full refunds within 14 days of purchase."])

    response = await client.post(
        f"/organizations/{org_id}/documents/compare",
        json={"document_id_a": doc_a, "document_id_b": doc_b},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_a"] == "policy_2023.pdf"
    assert body["document_b"] == "policy_2024.pdf"
    assert isinstance(body["summary"], str) and body["summary"]
    assert isinstance(body["differences"], list)
    assert body["truncated"] is False


async def test_compare_same_document_twice_is_rejected(client):
    await client.post("/auth/signup", json={"email": "compare2@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]
    doc_a = await _upload(client, org_id, "policy.pdf", ["Some content."])

    response = await client.post(
        f"/organizations/{org_id}/documents/compare",
        json={"document_id_a": doc_a, "document_id_b": doc_a},
    )

    assert response.status_code == 400


async def test_compare_nonexistent_document_returns_404(client):
    await client.post("/auth/signup", json={"email": "compare3@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]
    doc_a = await _upload(client, org_id, "policy.pdf", ["Some content."])

    response = await client.post(
        f"/organizations/{org_id}/documents/compare",
        json={"document_id_a": doc_a, "document_id_b": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 404


@pytest.mark.live_llm
async def test_extract_key_information_from_a_document(client):
    await client.post("/auth/signup", json={"email": "extract1@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]
    doc_a = await _upload(
        client,
        org_id,
        "contract.pdf",
        ["Agreement between Acme Corp and Globex Inc.", "Total contract value: $50,000.", "Effective date: January 1, 2025."],
    )

    response = await client.post(f"/organizations/{org_id}/documents/{doc_a}/extract")

    assert response.status_code == 200
    body = response.json()
    assert body["document"] == "contract.pdf"
    assert isinstance(body["fields"], list)
    assert body["truncated"] is False


async def test_extract_from_nonexistent_document_returns_404(client):
    await client.post("/auth/signup", json={"email": "extract2@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    response = await client.post(
        f"/organizations/{org_id}/documents/00000000-0000-0000-0000-000000000000/extract"
    )

    assert response.status_code == 404


@pytest.mark.live_llm
async def test_generate_report_across_multiple_documents(client):
    await client.post("/auth/signup", json={"email": "report1@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]
    doc_a = await _upload(client, org_id, "q1.pdf", ["Q1 revenue was $1.2 million, up 10% year over year."])
    doc_b = await _upload(client, org_id, "q2.pdf", ["Q2 revenue was $1.5 million, up 25% year over year."])

    response = await client.post(
        f"/organizations/{org_id}/documents/report",
        json={"document_ids": [doc_a, doc_b], "focus": "revenue growth"},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body["documents"]) == {"q1.pdf", "q2.pdf"}
    assert isinstance(body["title"], str) and body["title"]
    assert isinstance(body["key_findings"], list)
    assert body["truncated"] is False


async def test_report_with_no_documents_is_rejected(client):
    await client.post("/auth/signup", json={"email": "report2@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    response = await client.post(f"/organizations/{org_id}/documents/report", json={"document_ids": []})

    assert response.status_code == 422


async def test_report_with_missing_document_returns_404(client):
    await client.post("/auth/signup", json={"email": "report3@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]
    doc_a = await _upload(client, org_id, "q1.pdf", ["Some content."])

    response = await client.post(
        f"/organizations/{org_id}/documents/report",
        json={"document_ids": [doc_a, "00000000-0000-0000-0000-000000000000"]},
    )

    assert response.status_code == 404


async def test_cannot_compare_a_document_from_another_organization(client, second_client):
    await client.post("/auth/signup", json={"email": "compare4@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]
    doc_a = await _upload(client, org_id, "policy.pdf", ["Some content."])

    await second_client.post("/auth/signup", json={"email": "compare4b@example.com", "password": "correcthorse123"})
    other_org_id = (await second_client.get("/organizations")).json()[0]["id"]
    doc_b = await _upload(second_client, other_org_id, "other.pdf", ["Other content."])

    response = await client.post(
        f"/organizations/{org_id}/documents/compare",
        json={"document_id_a": doc_a, "document_id_b": doc_b},
    )

    assert response.status_code == 404
