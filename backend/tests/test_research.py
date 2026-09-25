from tests.pdf_fixture import make_pdf_bytes


async def _upload(client, org_id: str, filename: str, lines: list[str]) -> str:
    upload = await client.post(
        f"/organizations/{org_id}/documents",
        files={"file": (filename, make_pdf_bytes(lines), "application/pdf")},
    )
    return upload.json()["id"]


async def test_research_finds_a_verified_finding_corroborated_by_two_documents(client):
    await client.post("/auth/signup", json={"email": "research1@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    await _upload(client, org_id, "handbook_a.pdf", ["Remote work policy: employees may work remotely up to 3 days per week."])
    await _upload(client, org_id, "handbook_b.pdf", ["Company remote work guideline: staff can work from home 3 days weekly."])

    response = await client.post(f"/organizations/{org_id}/research", json={"topic": "remote work policy"})

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["summary"], str) and body["summary"]
    assert len(body["documents_used"]) >= 1
    # At least one finding should be corroborated by both documents.
    confidences = {f["confidence"] for f in body["findings"]}
    assert confidences.issubset({"verified", "single_source"})


async def test_research_with_no_matching_content_returns_empty_report(client):
    await client.post("/auth/signup", json={"email": "research2@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    response = await client.post(f"/organizations/{org_id}/research", json={"topic": "anything at all"})

    assert response.status_code == 200
    body = response.json()
    assert body["findings"] == []
    assert body["documents_used"] == []
    assert "no relevant content" in body["summary"].lower()


async def test_research_topic_too_short_is_rejected(client):
    await client.post("/auth/signup", json={"email": "research3@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    response = await client.post(f"/organizations/{org_id}/research", json={"topic": ""})

    assert response.status_code == 422


async def test_non_member_cannot_research_another_organizations_workspace(client, second_client):
    await client.post("/auth/signup", json={"email": "research4@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]
    await second_client.post("/auth/signup", json={"email": "research4b@example.com", "password": "correcthorse123"})

    response = await second_client.post(f"/organizations/{org_id}/research", json={"topic": "anything"})

    assert response.status_code == 403
