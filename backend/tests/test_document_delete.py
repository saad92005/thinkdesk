from tests.pdf_fixture import make_pdf_bytes


async def test_delete_document_removes_it_and_its_chunks_from_search(client):
    await client.post("/auth/signup", json={"email": "deleter@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    pdf_bytes = make_pdf_bytes(["Refund Policy: full refunds within 30 days of purchase."])
    upload = await client.post(
        f"/organizations/{org_id}/documents",
        files={"file": ("policy.pdf", pdf_bytes, "application/pdf")},
    )
    document_id = upload.json()["id"]

    delete_response = await client.delete(f"/organizations/{org_id}/documents/{document_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/organizations/{org_id}/documents/{document_id}")
    assert get_response.status_code == 404

    search = await client.post(f"/organizations/{org_id}/search", json={"query": "refund policy", "top_k": 5})
    assert search.json()["results"] == []


async def test_delete_nonexistent_document_returns_404(client):
    await client.post("/auth/signup", json={"email": "deleter2@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.delete(f"/organizations/{org_id}/documents/{fake_id}")
    assert response.status_code == 404


async def test_non_member_cannot_delete_another_orgs_document(client, second_client):
    await client.post("/auth/signup", json={"email": "owner_del@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    pdf_bytes = make_pdf_bytes(["Some content."])
    upload = await client.post(
        f"/organizations/{org_id}/documents",
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
    )
    document_id = upload.json()["id"]

    await second_client.post("/auth/signup", json={"email": "intruder_del@example.com", "password": "correcthorse123"})
    response = await second_client.delete(f"/organizations/{org_id}/documents/{document_id}")
    assert response.status_code == 403
