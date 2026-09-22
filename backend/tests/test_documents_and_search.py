from tests.pdf_fixture import make_pdf_bytes


async def test_upload_process_search_and_chat_round_trip(client):
    await client.post("/auth/signup", json={"email": "reader@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    pdf_bytes = make_pdf_bytes(
        [
            "ThinkDesk Test Policy",
            "Refund Policy: full refunds within 30 days of purchase.",
        ]
    )
    upload = await client.post(
        f"/organizations/{org_id}/documents",
        files={"file": ("policy.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload.status_code == 201
    document = upload.json()

    # BackgroundTasks run to completion inside the same ASGI call under
    # httpx's ASGITransport, so processing has already finished here.
    detail = await client.get(f"/organizations/{org_id}/documents/{document['id']}")
    assert detail.json()["status"] == "ready"
    assert detail.json()["page_count"] == 1

    search = await client.post(f"/organizations/{org_id}/search", json={"query": "refund policy", "top_k": 3})
    assert search.status_code == 200
    results = search.json()["results"]
    assert len(results) >= 1
    assert "refund" in results[0]["text"].lower()
    assert results[0]["filename"] == "policy.pdf"

    chat = await client.post(f"/organizations/{org_id}/chat", json={"message": "What is the refund policy?"})
    assert chat.status_code == 200
    body = chat.json()
    assert body["message"]["citations"], "chat answer must cite the retrieved chunk, not answer ungrounded"
    assert body["message"]["citations"][0]["filename"] == "policy.pdf"


async def test_non_pdf_upload_is_rejected(client):
    await client.post("/auth/signup", json={"email": "reject@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    response = await client.post(
        f"/organizations/{org_id}/documents",
        files={"file": ("notes.txt", b"just text", "text/plain")},
    )
    assert response.status_code == 415


async def test_search_with_no_documents_returns_empty(client):
    await client.post("/auth/signup", json={"email": "empty@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    response = await client.post(f"/organizations/{org_id}/search", json={"query": "anything", "top_k": 5})
    assert response.status_code == 200
    assert response.json()["results"] == []


async def test_chat_with_no_knowledge_does_not_fabricate_an_answer(client):
    await client.post("/auth/signup", json={"email": "noknowledge@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    response = await client.post(f"/organizations/{org_id}/chat", json={"message": "What is our refund policy?"})
    assert response.status_code == 200
    body = response.json()["message"]
    assert body["citations"] is None
    assert "couldn't find" in body["content"].lower()
